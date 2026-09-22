#!/usr/bin/env python3
"""Extract a .pptx with a citable locator on every line (stdlib only, read-only).

Locators:
  S<n>                 slide n in presentation order (from the slide-ID list, not file names)
  S<n>.<shape>         text of one shape on slide n (shape name as stored in the file)
  S<n>.T<t>.R<r>.C<c>  table cell
  S<n>.notes           speaker notes of slide n
  S<n>.chart<k>        text and cached numbers of a chart linked from slide n
  S<n>.diagram<k>      SmartArt text linked from slide n
  S<n>.comment<k>      reviewer comment on slide n

Hidden slides are listed and marked HIDDEN. Slide parts that exist in the package
but are not in the slide-ID list are reported as ORPHAN (not part of the deck).

Safety: read in memory only; XML parts declaring a DTD or entities are refused;
parts larger than MAX_PART_BYTES are refused.

Exit codes: 0 ok, 2 not a .pptx or corrupt, 3 encrypted or legacy binary file, 4 unsafe input,
5 python3 older than 3.14.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
import json
from pathlib import Path
import posixpath
import re
import sys
from typing import NoReturn, TypedDict
import xml.etree.ElementTree as ET
import zipfile
import zlib

MIN_PYTHON = (3, 14)


def _require_python() -> None:
    """Exit with status 5 and a one-line explanation when the interpreter is too old."""
    if tuple(sys.version_info[:2]) >= MIN_PYTHON:
        return
    found = ".".join(str(part) for part in sys.version_info[:3])
    _ = sys.stderr.write(
        "".join(
            (
                f"{Path(__file__).name} needs Python 3.14 or later; ",
                f"this is python3 {found} at {sys.executable}. ",
                "Install Python 3.14 (python.org, brew install python@3.14, ",
                "or uv python install 3.14 --default) so `python3` is 3.14.\n",
            )
        )
    )
    sys.exit(5)


_require_python()


P = "{http://schemas.openxmlformats.org/presentationml/2006/main}"
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
C = "{http://schemas.openxmlformats.org/drawingml/2006/chart}"
R_ID = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
REL = "{http://schemas.openxmlformats.org/package/2006/relationships}"
OLE_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
MAX_PART_BYTES = 200 * 1024 * 1024


def _fail(code: int, message: str) -> NoReturn:
    print(f"ERROR: {message}", file=sys.stderr)
    sys.exit(code)


def _open_package(path: str) -> zipfile.ZipFile:
    try:
        with Path(path).open("rb") as handle:
            head = handle.read(8)
    except OSError as exc:
        _fail(2, f"cannot open {path}: {exc.strerror}")
    if head == OLE_MAGIC:
        _fail(3, f"{path} is an encrypted (password-protected) or legacy binary PowerPoint file")
    try:
        package = zipfile.ZipFile(path)
    except zipfile.BadZipFile:
        _fail(2, f"{path} is not a valid .pptx (not a zip package)")
    if "ppt/presentation.xml" not in package.namelist():
        _fail(2, f"{path} has no ppt/presentation.xml; it is not a PowerPoint presentation")
    return package


def _declares_dtd(data: bytes) -> bool:
    """True when the part declares a DTD or entity, in UTF-8 or in UTF-16 (which expat reads)."""
    if b"<!DOCTYPE" in data or b"<!ENTITY" in data:
        return True
    if data[:2] in (b"\xff\xfe", b"\xfe\xff", b"<\x00", b"\x00<"):
        text = data.decode("utf-16-be" if data[:1] in (b"\xfe", b"\x00") else "utf-16-le", "ignore")
        return "<!DOCTYPE" in text or "<!ENTITY" in text
    return False


def _read_part(package: zipfile.ZipFile, name: str) -> ET.Element:
    info = package.getinfo(name)
    if info.file_size > MAX_PART_BYTES:
        _fail(4, f"{name} expands to {info.file_size:,} bytes; refusing (possible zip bomb)")
    try:
        data = package.read(name)
    except (zipfile.BadZipFile, zlib.error, EOFError, OSError) as exc:
        _fail(2, f"{name} is corrupt or incomplete ({exc}); not verified, ask for a fresh copy")
    if _declares_dtd(data):
        _fail(4, f"{name} declares a DTD or entity; OOXML never needs one, refusing to parse")
    try:
        return ET.fromstring(data)
    except ET.ParseError as exc:
        _fail(2, f"{name} is not well-formed XML: {exc}")


def _rels_of(package: zipfile.ZipFile, part: str) -> dict[str, tuple[str, str]]:
    """Map r:id -> (relationship type suffix, resolved part name or external URL)."""
    folder, name = posixpath.split(part)
    rels_name = posixpath.join(folder, "_rels", name + ".rels")
    found: dict[str, tuple[str, str]] = {}
    if rels_name not in package.namelist():
        return found
    for rel in _read_part(package, rels_name).iter(f"{REL}Relationship"):
        rtype = rel.get("Type", "").rsplit("/", 1)[-1]
        target = rel.get("Target", "")
        if rel.get("TargetMode") == "External":
            found[rel.get("Id", "")] = (rtype, target)
            continue
        resolved = (
            target.lstrip("/")
            if target.startswith("/")
            else posixpath.normpath(posixpath.join(folder, target))
        )
        found[rel.get("Id", "")] = (rtype, resolved)
    return found


def _paragraphs_text(node: ET.Element) -> list[str]:
    out: list[str] = []
    for p in node.iter(f"{A}p"):
        text = "".join(t.text or "" for t in p.iter(f"{A}t")).strip()
        if text:
            out.append(text)
    return out


def _chart_lines(package: zipfile.ZipFile, part: str) -> list[str]:
    root = _read_part(package, part)
    lines: list[str] = []
    title = root.find(f".//{C}title")
    if title is not None:
        text = " ".join(_paragraphs_text(title))
        if text:
            lines.append(f"title: {text}")
    for ser in root.iter(f"{C}ser"):
        name = ""
        tx = ser.find(f"{C}tx")
        if tx is not None:
            name = " ".join((v.text or "") for v in tx.iter(f"{C}v")).strip()
        cats = [v.text or "" for v in ser.findall(f"{C}cat//{C}pt/{C}v")]
        vals = [v.text or "" for v in ser.findall(f"{C}val//{C}pt/{C}v")]
        lines.append(f"series {name or '(unnamed)'}: categories={cats} cached_values={vals}")
    return lines


class _LineRecord(TypedDict):
    locator: str
    text: str


class _Counts(TypedDict):
    slides: int
    hidden: list[int]
    orphans: list[str]


class _ExtractResult(TypedDict):
    file: str
    counts: _Counts
    lines: list[_LineRecord]


@dataclass
class _ExtractState:
    lines: list[_LineRecord] = field(default_factory=list)
    hidden: list[int] = field(default_factory=list)

    def add(self, locator: str, text: str) -> None:
        self.lines.append({"locator": locator, "text": text})


@dataclass
class _SlideCounters:
    tables: int = 0
    charts: int = 0
    diagrams: int = 0
    comments: int = 0


@dataclass
class _SlideContext:
    state: _ExtractState
    n: int
    package: zipfile.ZipFile
    counters: _SlideCounters


def _handle_shape(ctx: _SlideContext, shape: ET.Element) -> None:
    if shape.tag == f"{P}sp":
        name_el = shape.find(f"{P}nvSpPr/{P}cNvPr")
        name = name_el.get("name", "shape") if name_el is not None else "shape"
        body = shape.find(f"{P}txBody")
        if body is not None:
            for text in _paragraphs_text(body):
                ctx.state.add(f"S{ctx.n}.{name}", text)
    elif shape.tag == f"{A}tbl":
        ctx.counters.tables += 1
        for r, row in enumerate(shape.findall(f"{A}tr"), 1):
            for c, cell in enumerate(row.findall(f"{A}tc"), 1):
                locator = f"S{ctx.n}.T{ctx.counters.tables}.R{r}.C{c}"
                ctx.state.add(locator, " / ".join(_paragraphs_text(cell)))


def _handle_notes(ctx: _SlideContext, target: str) -> None:
    notes = _read_part(ctx.package, target)
    for sp in notes.iter(f"{P}sp"):
        ph = sp.find(f"{P}nvSpPr/{P}nvPr/{P}ph")
        if ph is None or ph.get("type") != "body":
            continue
        body = sp.find(f"{P}txBody")
        if body is not None:
            for text in _paragraphs_text(body):
                ctx.state.add(f"S{ctx.n}.notes", text)


def _handle_chart(ctx: _SlideContext, target: str) -> None:
    ctx.counters.charts += 1
    for text in _chart_lines(ctx.package, target):
        ctx.state.add(f"S{ctx.n}.chart{ctx.counters.charts}", text)


def _handle_diagram(ctx: _SlideContext, target: str) -> None:
    ctx.counters.diagrams += 1
    for text in _paragraphs_text(_read_part(ctx.package, target)):
        ctx.state.add(f"S{ctx.n}.diagram{ctx.counters.diagrams}", text)


def _handle_comments(ctx: _SlideContext, target: str) -> None:
    for cm in _read_part(ctx.package, target).iter():
        if not cm.tag.endswith("}cm"):
            continue
        ctx.counters.comments += 1
        text = " ".join(
            t.text or "" for t in cm.iter() if t.tag.endswith("}text") or t.tag == f"{A}t"
        )
        ctx.state.add(f"S{ctx.n}.comment{ctx.counters.comments}", text.strip())


def _handle_slide_rel(ctx: _SlideContext, rtype: str, target: str) -> None:
    if rtype == "notesSlide":
        _handle_notes(ctx, target)
    elif rtype == "chart":
        _handle_chart(ctx, target)
    elif rtype == "diagramData":
        _handle_diagram(ctx, target)
    elif rtype in ("comments", "comment"):
        _handle_comments(ctx, target)


def _process_slide(state: _ExtractState, package: zipfile.ZipFile, n: int, part: str) -> None:
    if part not in package.namelist():
        state.add(f"S{n}", f"MISSING PART {part} (listed in presentation.xml but absent)")
        return
    slide = _read_part(package, part)
    if slide.get("show") in ("0", "false"):
        state.hidden.append(n)
        state.add(f"S{n}", "HIDDEN slide (not shown in slideshow)")
    ctx = _SlideContext(state, n, package, _SlideCounters())
    for shape in slide.iter():
        _handle_shape(ctx, shape)
    slide_rels = _rels_of(package, part)
    for rtype, target in slide_rels.values():
        if target not in package.namelist():
            continue
        _handle_slide_rel(ctx, rtype, target)


def _slide_parts(presentation: ET.Element, pres_rels: dict[str, tuple[str, str]]) -> list[str]:
    slide_parts: list[str] = []
    for sld in presentation.iter(f"{P}sldId"):
        rtype, target = pres_rels.get(sld.get(R_ID, ""), ("", ""))
        if rtype == "slide":
            slide_parts.append(target)
    return slide_parts


def _orphan_slides(package: zipfile.ZipFile, listed: set[str]) -> list[str]:
    return sorted(
        name
        for name in package.namelist()
        if re.fullmatch(r"ppt/slides/slide\d+\.xml", name) and name not in listed
    )


def _extract(path: str) -> _ExtractResult:
    package = _open_package(path)
    presentation = _read_part(package, "ppt/presentation.xml")
    pres_rels = _rels_of(package, "ppt/presentation.xml")
    slide_parts = _slide_parts(presentation, pres_rels)

    state = _ExtractState()
    for n, part in enumerate(slide_parts, 1):
        _process_slide(state, package, n, part)

    orphans = _orphan_slides(package, set(slide_parts))
    for orphan in orphans:
        state.add(
            "ORPHAN",
            f"{orphan} exists in the package but is not in the slide list (not part of the deck)",
        )

    return {
        "file": path,
        "counts": {"slides": len(slide_parts), "hidden": state.hidden, "orphans": orphans},
        "lines": state.lines,
    }


def main() -> None:
    """Parse the command line and print the extraction as text or JSON."""
    doc = __doc__ or ""
    parser = argparse.ArgumentParser(description=doc.split("\n", 1)[0])
    _ = parser.add_argument("path", help="path to the .pptx file")
    _ = parser.add_argument("--json", action="store_true", help="print JSON instead of text")
    values: dict[str, object] = vars(parser.parse_args())
    result = _extract(str(values["path"]))
    if bool(values["json"]):
        json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
        print()
        return
    c = result["counts"]
    print(
        f"FILE {result['file']} slides={c['slides']} hidden={c['hidden'] or 'none'}",
        f"orphans={len(c['orphans'])}",
    )
    for line in result["lines"]:
        print(f"{line['locator']}: {line['text']}")


if __name__ == "__main__":
    main()
