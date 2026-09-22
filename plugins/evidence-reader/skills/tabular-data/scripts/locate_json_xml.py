#!/usr/bin/env python3
"""Flatten JSON or XML into one citable line per value (stdlib only, read-only).

JSON: every scalar becomes  <JSON Pointer> = <value>   (RFC 6901, e.g. /order/lines/0/qty)
XML:  every element text and attribute becomes
      line <L> <path> = <value>   with an XPath-like path, e.g. /catalog/product[2]/@sku

Options:
  --grep REGEX   only print lines whose path or value matches
  --limit N      stop after N printed lines (the COVERED line still reports the total)

XML safety: documents that declare a DTD or entities are refused (no external
entity or entity-expansion processing is ever performed).

Exit codes: 0 ok, 2 unreadable or malformed, 4 refused unsafe XML, 5 python3 older than 3.14.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import TYPE_CHECKING, NoReturn, cast
from xml.parsers import expat

if TYPE_CHECKING:
    from collections.abc import Callable


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


# Parse() takes isfinal positionally only (Python 3.9 rejects the keyword form).
_FINAL_CHUNK = True


# json.loads is annotated `-> Any`; this alias is the one place that Any becomes object.
_loads: Callable[[str], object] = json.loads


def _fail(code: int, message: str) -> NoReturn:
    print(f"ERROR: {message}", file=sys.stderr)
    sys.exit(code)


def _pointer_escape(key: str) -> str:
    return key.replace("~", "~0").replace("/", "~1")


def _walk_json(node: object, path: str, out: list[tuple[str, str]]) -> None:
    if isinstance(node, dict):
        obj = cast("dict[str, object]", node)
        if not obj:
            out.append((path or "/", "{}"))
        for key, value in obj.items():
            _walk_json(value, f"{path}/{_pointer_escape(key)}", out)
    elif isinstance(node, list):
        items = cast("list[object]", node)
        if not items:
            out.append((path or "/", "[]"))
        for index, value in enumerate(items):
            _walk_json(value, f"{path}/{index}", out)
    else:
        out.append((path or "/", json.dumps(node, ensure_ascii=False)))


def _flatten_json(path: str) -> list[tuple[str, str]]:
    try:
        with Path(path).open(encoding="utf-8-sig") as handle:
            data = _loads(handle.read())
    except json.JSONDecodeError as exc:
        _fail(2, f"{path} is not valid JSON: {exc.msg} at line {exc.lineno} column {exc.colno}")
    out: list[tuple[str, str]] = []
    _walk_json(data, "", out)
    return out


class _XmlFlattener:
    """Accumulates one (locator, value) pair per element text and per attribute."""

    def __init__(self) -> None:
        self.out: list[tuple[str, str]] = []
        self.stack: list[tuple[str, dict[str, int], list[str], int]] = []
        self.counts_root: dict[str, int] = {}
        self.parser: expat.XMLParserType = expat.ParserCreate()
        self.parser.StartElementHandler = self.start
        self.parser.EndElementHandler = self.end
        self.parser.CharacterDataHandler = self.chars

    def start(self, name: str, attrs: dict[str, str]) -> None:
        siblings = self.stack[-1][1] if self.stack else self.counts_root
        siblings[name] = siblings.get(name, 0) + 1
        parent_path = self.stack[-1][0] if self.stack else ""
        me = f"{parent_path}/{name}[{siblings[name]}]"
        line = self.parser.CurrentLineNumber
        for key, value in attrs.items():
            self.out.append((f"line {line} {me}/@{key}", value))
        self.stack.append((me, {}, [], line))

    def end(self, _name: str) -> None:
        me, _, texts, line = self.stack.pop()
        text = "".join(texts).strip()
        if text:
            self.out.append((f"line {line} {me}", text))

    def chars(self, data: str) -> None:
        if self.stack:
            self.stack[-1][2].append(data)


def _declares_dtd(data: bytes) -> bool:
    """True when the part declares a DTD or entity, in UTF-8 or in UTF-16 (which expat reads)."""
    if b"<!DOCTYPE" in data or b"<!ENTITY" in data:
        return True
    if data[:2] in (b"\xff\xfe", b"\xfe\xff", b"<\x00", b"\x00<"):
        text = data.decode("utf-16-be" if data[:1] in (b"\xfe", b"\x00") else "utf-16-le", "ignore")
        return "<!DOCTYPE" in text or "<!ENTITY" in text
    return False


def _flatten_xml(path: str) -> list[tuple[str, str]]:
    with Path(path).open("rb") as handle:
        data = handle.read()
    if _declares_dtd(data):
        msg = f"{path} declares a DTD or entities; refusing to parse (entity-expansion protection)"
        _fail(4, msg)
    flattener = _XmlFlattener()
    try:
        _ = flattener.parser.Parse(data, _FINAL_CHUNK)
    except expat.ExpatError as exc:
        _fail(2, f"{path} is not well-formed XML: {exc}")
    return flattener.out


def _flatten_jsonl(path: str) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    with Path(path).open(encoding="utf-8-sig") as handle:
        for number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                record = _loads(line)
            except json.JSONDecodeError as exc:
                _fail(2, f"line {number} is not valid JSON: {exc.msg}")
            _walk_json(record, f"line{number}", rows)
    return rows


def _flatten(path: str) -> tuple[list[tuple[str, str]], str]:
    lower = path.lower()
    if lower.endswith((".json", ".geojson")):
        return _flatten_json(path), "json"
    if lower.endswith((".jsonl", ".ndjson")):
        return _flatten_jsonl(path), "jsonl"
    return _flatten_xml(path), "xml"


def main() -> None:
    """Parse the command line, flatten the file and print one locator per value."""
    doc = __doc__ or ""
    parser = argparse.ArgumentParser(description=doc.split("\n", 1)[0])
    _ = parser.add_argument("path")
    _ = parser.add_argument("--grep", help="only lines whose path or value matches this regex")
    _ = parser.add_argument("--limit", type=int, default=0)
    values: dict[str, object] = vars(parser.parse_args())
    path = str(values["path"])
    grep = values["grep"]
    limit_value = values["limit"]
    limit = limit_value if isinstance(limit_value, int) else 0
    try:
        rows, kind = _flatten(path)
    except OSError as exc:
        _fail(2, f"cannot read {path}: {exc.strerror}")
    regex = re.compile(str(grep)) if grep else None
    printed = 0
    for locator, value in rows:
        if regex and not (regex.search(locator) or regex.search(value)):
            continue
        if limit and printed >= limit:
            break
        print(f"{locator} = {value}")
        printed += 1
    print(f"COVERED {kind} values={len(rows)} printed={printed}")


if __name__ == "__main__":
    main()
