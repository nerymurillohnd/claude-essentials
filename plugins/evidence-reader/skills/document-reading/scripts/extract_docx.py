#!/usr/bin/env python3
"""Extract a .docx with a citable locator on every line (stdlib only, read-only).

Locators:
  P<n>          body paragraph n (1-based, document order, tables excluded)
  T<t>.R<r>.C<c> table t, row r, cell c (1-based)
  <part> P<n>   paragraph n inside a header, footer, footnotes or endnotes part
Each body paragraph also shows the heading path it sits under, so a citation can
read "Payment > P4" instead of a page number (Word has no stored page numbers).

Tracked changes are shown inline in the default "markup" view as [+inserted+]
and [-deleted-]; --view accepted shows the text as if all changes were accepted,
--view original as if all were rejected.

Safety: the file is read in memory only, never extracted or modified. XML parts
that declare a DTD or entities are refused (OOXML never needs one), and parts
that expand beyond MAX_PART_BYTES are refused (zip-bomb guard).

Exit codes: 0 ok, 2 not a .docx (not a zip / missing word/document.xml) or corrupt,
3 encrypted or legacy binary Word file, 4 refused as unsafe input, 5 python3 older than 3.14.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
import json
from pathlib import Path
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


W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
OLE_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
MAX_PART_BYTES = 200 * 1024 * 1024


class _LineRecord(TypedDict):
    locator: str
    section: str
    style: str
    text: str


class _ChangeRecord(TypedDict):
    locator: str
    kind: str
    author: str
    date: str
    text: str


class _CommentRecord(TypedDict):
    id: str
    anchor: str
    author: str
    date: str
    text: str


class _Counts(TypedDict):
    body_paragraphs: int
    tables: int
    insertions: int
    deletions: int
    comments: int
    extra_parts: list[str]


class _ExtractResult(TypedDict):
    file: str
    view: str
    counts: _Counts
    lines: list[_LineRecord]
    tracked_changes: list[_ChangeRecord]
    comments: list[_CommentRecord]


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
        _fail(3, f"{path} is encrypted or a legacy binary Word file; cannot read as .docx")
    try:
        package = zipfile.ZipFile(path)
    except zipfile.BadZipFile:
        _fail(2, f"{path} is not a valid .docx (not a zip package)")
    if "word/document.xml" not in package.namelist():
        _fail(2, f"{path} has no word/document.xml; it is not a Word document")
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


def _style_names(package: zipfile.ZipFile) -> dict[str, str]:
    names: dict[str, str] = {}
    if "word/styles.xml" not in package.namelist():
        return names
    root = _read_part(package, "word/styles.xml")
    for style in root.iter(f"{W}style"):
        style_id = style.get(f"{W}styleId", "")
        name = style.find(f"{W}name")
        names[style_id] = name.get(f"{W}val", style_id) if name is not None else style_id
    return names


def _heading_level(style_name: str) -> int | None:
    match = re.fullmatch(r"(?i)(heading|título|titulo)\s*(\d)", style_name.strip())
    if match:
        return int(match.group(2))
    if style_name.strip().lower() == "title":
        return 0
    return None


class _Paragraph:
    def __init__(self) -> None:
        self.markup: list[str] = []
        self.accepted: list[str] = []
        self.original: list[str] = []
        self.insertions: list[tuple[str, str, str]] = []
        self.deletions: list[tuple[str, str, str]] = []
        self.comment_ids: list[str] = []


_TEXT_TAGS = (f"{W}t", f"{W}delText")
# A move is recorded where the text went (moveTo, an insertion) and where it came from
# (moveFrom, a deletion), so moved text appears once in each view, not twice.
_INSERT_TAGS = (f"{W}ins", f"{W}moveTo")
_DELETE_TAGS = (f"{W}del", f"{W}moveFrom")


def _record_change(node: ET.Element, bucket: list[tuple[str, str, str]]) -> None:
    author, date = node.get(f"{W}author", "?"), node.get(f"{W}date", "?")
    text = "".join(t.text or "" for t in node.iter() if t.tag in _TEXT_TAGS)
    bucket.append((author, date, text))


def _change_state(tag: str, state: str) -> str:
    """The run state inside a change mark: text both inserted and deleted is in no view."""
    entering = "ins" if tag in _INSERT_TAGS else "del"
    if state in ("ins", "del") and state != entering:
        return "insdel"
    return entering


def _append_run_text(text: str, state: str, out: _Paragraph) -> None:
    if state == "insdel":
        out.markup.append(f"[+-{text}-+]")
    elif state == "ins":
        out.markup.append(f"[+{text}+]")
        out.accepted.append(text)
    elif state == "del":
        out.markup.append(f"[-{text}-]")
        out.original.append(text)
    else:
        out.markup.append(text)
        out.accepted.append(text)
        out.original.append(text)


def _append_to_all(out: _Paragraph, char: str) -> None:
    for bucket in (out.markup, out.accepted, out.original):
        bucket.append(char)


_RUN_BREAKS = {f"{W}tab": "\t", f"{W}br": "\n", f"{W}cr": "\n"}


def _walk_run(node: ET.Element, state: str, out: _Paragraph) -> None:
    tag = node.tag
    if tag == f"{W}pPr":
        # Paragraph properties hold no text; an empty w:ins or w:del in them marks a
        # tracked paragraph mark, not a change to the wording.
        return
    if tag in _INSERT_TAGS or tag in _DELETE_TAGS:
        state = _change_state(tag, state)
        _record_change(node, out.insertions if tag in _INSERT_TAGS else out.deletions)
    elif tag == f"{W}commentRangeStart":
        out.comment_ids.append(node.get(f"{W}id", "?"))
    elif tag in _TEXT_TAGS:
        _append_run_text(node.text or "", state, out)
        return
    elif tag in _RUN_BREAKS:
        _append_to_all(out, _RUN_BREAKS[tag])
    for child in node:
        _walk_run(child, state, out)


def _read_paragraph(p: ET.Element) -> _Paragraph:
    out = _Paragraph()
    _walk_run(p, "normal", out)
    return out


def _paragraph_text(par: _Paragraph, view: str) -> str:
    bucket = {"markup": par.markup, "accepted": par.accepted, "original": par.original}[view]
    return "".join(bucket).strip()


def _comments(package: zipfile.ZipFile) -> dict[str, dict[str, str]]:
    found: dict[str, dict[str, str]] = {}
    if "word/comments.xml" not in package.namelist():
        return found
    root = _read_part(package, "word/comments.xml")
    for c in root.iter(f"{W}comment"):
        text = " ".join(
            "".join(t.text or "" for t in p.iter(f"{W}t")) for p in c.iter(f"{W}p")
        ).strip()
        found[c.get(f"{W}id", "?")] = {
            "author": c.get(f"{W}author", "?"),
            "date": c.get(f"{W}date", "?"),
            "text": text,
        }
    return found


@dataclass
class _ExtractState:
    view: str
    names: dict[str, str]
    lines: list[_LineRecord] = field(default_factory=list)
    heading_path: list[tuple[int, str]] = field(default_factory=list)
    changes: list[_ChangeRecord] = field(default_factory=list)
    anchors: dict[str, str] = field(default_factory=dict)
    counters: dict[str, int] = field(default_factory=lambda: {"p": 0, "t": 0})


def _paragraph_style(p: ET.Element, names: dict[str, str]) -> str:
    style_el = p.find(f"{W}pPr/{W}pStyle")
    if style_el is None:
        return ""
    val = style_el.get(f"{W}val", "")
    return names.get(val, val)


def _next_body_locator(state: _ExtractState, style: str, text: str) -> str:
    state.counters["p"] += 1
    locator = f"P{state.counters['p']}"
    level = _heading_level(style) if style else None
    if level is not None and text:
        while state.heading_path and state.heading_path[-1][0] >= level:
            _ = state.heading_path.pop()
        state.heading_path.append((level, text))
    return locator


def _record_tracked_changes(state: _ExtractState, par: _Paragraph, locator: str) -> None:
    for author, date, change in par.insertions:
        state.changes.append(
            {
                "locator": locator,
                "kind": "insertion",
                "author": author,
                "date": date,
                "text": change,
            }
        )
    for author, date, change in par.deletions:
        state.changes.append(
            {
                "locator": locator,
                "kind": "deletion",
                "author": author,
                "date": date,
                "text": change,
            }
        )


def _handle_paragraph(state: _ExtractState, p: ET.Element, locator: str | None = None) -> None:
    par = _read_paragraph(p)
    text = _paragraph_text(par, state.view)
    style = _paragraph_style(p, state.names)
    if locator is None:
        locator = _next_body_locator(state, style, text)
    _record_tracked_changes(state, par, locator)
    for cid in par.comment_ids:
        state.anchors[cid] = locator
    if text:
        state.lines.append(
            {
                "locator": locator,
                "section": " > ".join(h for _, h in state.heading_path),
                "style": style,
                "text": text,
            }
        )


def _handle_table(state: _ExtractState, tbl: ET.Element) -> None:
    state.counters["t"] += 1
    t = state.counters["t"]
    for r, row in enumerate(tbl.findall(f"{W}tr"), 1):
        for c, cell in enumerate(row.findall(f"{W}tc"), 1):
            texts: list[str] = []
            for p in cell.iter(f"{W}p"):
                par = _read_paragraph(p)
                _record_tracked_changes(state, par, f"T{t}.R{r}.C{c}")
                for cid in par.comment_ids:
                    state.anchors[cid] = f"T{t}.R{r}.C{c}"
                texts.append(_paragraph_text(par, state.view))
            state.lines.append(
                {
                    "locator": f"T{t}.R{r}.C{c}",
                    "section": " > ".join(h for _, h in state.heading_path),
                    "style": "table-cell",
                    "text": " / ".join(x for x in texts if x),
                }
            )


def _walk_block(state: _ExtractState, node: ET.Element) -> None:
    for child in node:
        if child.tag == f"{W}p":
            _handle_paragraph(state, child)
        elif child.tag == f"{W}tbl":
            _handle_table(state, child)
        elif child.tag == f"{W}sdt":
            content = child.find(f"{W}sdtContent")
            if content is not None:
                _walk_block(state, content)


def _extra_parts_lines(package: zipfile.ZipFile, state: _ExtractState) -> list[str]:
    extra_parts = sorted(
        n
        for n in package.namelist()
        if re.fullmatch(r"word/(header\d*|footer\d*|footnotes|endnotes)\.xml", n)
    )
    for part in extra_parts:
        root = _read_part(package, part)
        short = part.split("/")[-1]
        for i, p in enumerate(root.iter(f"{W}p"), 1):
            _handle_paragraph(state, p, locator=f"{short} P{i}")
    return extra_parts


def _extract(path: str, view: str) -> _ExtractResult:
    package = _open_package(path)
    names = _style_names(package)
    body = _read_part(package, "word/document.xml").find(f"{W}body")
    if body is None:
        _fail(2, f"{path} has an empty document body")

    state = _ExtractState(view=view, names=names)
    _walk_block(state, body)
    extra_parts = _extra_parts_lines(package, state)

    found_comments = _comments(package)
    comment_rows: list[_CommentRecord] = [
        {
            "id": cid,
            "anchor": state.anchors.get(cid, "unanchored"),
            "author": data["author"],
            "date": data["date"],
            "text": data["text"],
        }
        for cid, data in found_comments.items()
    ]
    return {
        "file": path,
        "view": view,
        "counts": {
            "body_paragraphs": state.counters["p"],
            "tables": state.counters["t"],
            "insertions": sum(1 for c in state.changes if c["kind"] == "insertion"),
            "deletions": sum(1 for c in state.changes if c["kind"] == "deletion"),
            "comments": len(comment_rows),
            "extra_parts": extra_parts,
        },
        "lines": state.lines,
        "tracked_changes": state.changes,
        "comments": comment_rows,
    }


def _print_text(result: _ExtractResult) -> None:
    c = result["counts"]
    print(
        f"FILE {result['file']} view={result['view']} body_paragraphs={c['body_paragraphs']}",
        f"tables={c['tables']} insertions={c['insertions']} deletions={c['deletions']}",
        f"comments={c['comments']}",
    )
    for line in result["lines"]:
        where = f" ({line['section']})" if line["section"] else ""
        style = f" [{line['style']}]" if line["style"] and line["style"] != "table-cell" else ""
        print(f"{line['locator']}{where}{style}: {line['text']}")
    if result["tracked_changes"]:
        print("== TRACKED CHANGES")
        for ch in result["tracked_changes"]:
            print(
                f"{ch['locator']}: {ch['kind']} by {ch['author']} on {ch['date']}: {ch['text']!r}"
            )
    if result["comments"]:
        print("== COMMENTS")
        for cm in result["comments"]:
            print(
                f"comment {cm['id']} on {cm['anchor']} by {cm['author']} on {cm['date']}:",
                f"{cm['text']!r}",
            )


def main() -> None:
    """Parse the command line and print the extraction as text or JSON."""
    doc = __doc__ or ""
    parser = argparse.ArgumentParser(description=doc.split("\n", 1)[0])
    _ = parser.add_argument("path", help="path to the .docx file")
    _ = parser.add_argument("--view", choices=["markup", "accepted", "original"], default="markup")
    _ = parser.add_argument("--json", action="store_true", help="print JSON instead of text")
    values: dict[str, object] = vars(parser.parse_args())
    try:
        result = _extract(str(values["path"]), str(values["view"]))
    except RecursionError:
        _fail(2, f"{values['path']} nests its markup too deeply to read safely; not verified")
    if bool(values["json"]):
        json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
        print()
    else:
        _print_text(result)


if __name__ == "__main__":
    main()
