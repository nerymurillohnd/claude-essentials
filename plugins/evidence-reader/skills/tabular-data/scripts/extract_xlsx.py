#!/usr/bin/env python3
"""Audit a .xlsx/.xlsm workbook with Sheet!A1 locators (stdlib only, read-only).

Subcommands:
  summary FILE                     every sheet (including hidden ones), formulas, formulas
                                   with no cached value, error cells, merged ranges, hidden
                                   rows/columns, external links, macros, formula outliers.
  cells FILE --sheet S [--range A1:D20]
                                   one line per non-empty cell: value, cached/missing,
                                   formula, number format. Streams large sheets.
  recompute FILE --sheet S         evaluate formulas that have NO cached value, using a
                                   small safe evaluator (numbers, references, ranges,
                                   + - * / ^, SUM AVERAGE MIN MAX COUNT COUNTA ROUND ABS
                                   DATE). Results are labelled "recomputed", never cached.

A cached value is what the spreadsheet application stored the last time it
calculated. Files written by libraries often have none; this script never invents
one. Workbooks with external links are never recomputed over those links.

Safety: read in memory only; XML parts declaring a DTD or entities are refused;
parts larger than MAX_PART_BYTES are refused.

Exit codes: 0 ok, 2 not a .xlsx or corrupt, 3 encrypted or legacy binary .xls, 4 unsafe input,
5 python3 older than 3.14.
"""

from __future__ import annotations

import argparse
from collections import Counter
import datetime as dt
from decimal import ROUND_HALF_UP, Decimal
import io
import math
from pathlib import Path
import posixpath
import re
import sys
from typing import TYPE_CHECKING, Literal, NoReturn, TypedDict
import xml.etree.ElementTree as ET
import zipfile
import zlib

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator


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


S = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
R_ID = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
REL = "{http://schemas.openxmlformats.org/package/2006/relationships}"
OLE_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
MAX_PART_BYTES = 500 * 1024 * 1024
ERRORS = {
    "#NULL!",
    "#DIV/0!",
    "#VALUE!",
    "#REF!",
    "#NAME?",
    "#NUM!",
    "#N/A",
    "#GETTING_DATA",
    "#SPILL!",
    "#CALC!",
}
BUILTIN_DATE_FORMATS = set(range(14, 23)) | {45, 46, 47} | set(range(27, 37)) | set(range(50, 59))
BUILTIN_PERCENT_FORMATS = {9, 10}
REF_RE = re.compile(r"(?<![A-Za-z0-9_.])(\$?)([A-Z]{1,3})(\$?)([0-9]+)(?![A-Za-z0-9_(])")
LIST_CAP = 25
MIN_OUTLIER_SAMPLE = 3
MIN_OUTLIER_MAJORITY = 2
MAX_RECOMPUTE_CELLS = 1_000_000
# Days from the 1900 date system's epoch (1899-12-30) to the 1904 system's (1904-01-01).
DATE1904_OFFSET_DAYS = 1462
# DATE adds this to a year below it, as Excel does.
EXCEL_YEAR_BASE = 1900


class _Sheet(TypedDict):
    name: str
    state: str
    part: str


class _Cell(TypedDict):
    ref: str
    col: int
    row: int
    type: str
    value: str | int | float | bool | None
    formula: str | None
    cached: bool
    style: int
    hidden_row: bool


class _SheetLayout(TypedDict):
    dimension: str
    merged: list[str]
    hidden_cols: list[str]


def _fail(code: int, message: str) -> NoReturn:
    print(f"ERROR: {message}", file=sys.stderr)
    sys.exit(code)


# iterparse is annotated to yield `tuple[str, Any]`; with only "start" and "end" events every
# item is an element, and this alias is the one place that Any becomes `ET.Element`.
_Events = tuple[Literal["start", "end"], ...]
_iterparse: Callable[[io.BytesIO, _Events], Iterator[tuple[str, ET.Element]]] = ET.iterparse


# ---------------------------------------------------------------- package access


def _open_package(path: str) -> zipfile.ZipFile:
    try:
        with Path(path).open("rb") as handle:
            head = handle.read(8)
    except OSError as exc:
        _fail(2, f"cannot open {path}: {exc.strerror}")
    if head == OLE_MAGIC:
        _fail(3, f"{path} is an encrypted (password-protected) workbook or a legacy binary .xls")
    try:
        package = zipfile.ZipFile(path)
    except zipfile.BadZipFile:
        _fail(2, f"{path} is not a valid .xlsx (not a zip package)")
    if "xl/workbook.xml" not in package.namelist():
        _fail(2, f"{path} has no xl/workbook.xml; it is not an Excel workbook")
    return package


def _part_bytes(package: zipfile.ZipFile, name: str) -> bytes:
    info = package.getinfo(name)
    if info.file_size > MAX_PART_BYTES:
        _fail(4, f"{name} expands to {info.file_size:,} bytes; refusing (possible zip bomb)")
    try:
        data = package.read(name)
    except (zipfile.BadZipFile, zlib.error, EOFError, OSError) as exc:
        _fail(2, f"{name} is corrupt or incomplete ({exc}); not verified, ask for a fresh copy")
    if _declares_dtd(data):
        _fail(4, f"{name} declares a DTD or entity; OOXML never needs one, refusing to parse")
    return data


def _declares_dtd(data: bytes) -> bool:
    """True when the part declares a DTD or entity, in UTF-8 or in UTF-16 (which expat reads)."""
    if b"<!DOCTYPE" in data or b"<!ENTITY" in data:
        return True
    if data[:2] in (b"\xff\xfe", b"\xfe\xff", b"<\x00", b"\x00<"):
        text = data.decode("utf-16-be" if data[:1] in (b"\xfe", b"\x00") else "utf-16-le", "ignore")
        return "<!DOCTYPE" in text or "<!ENTITY" in text
    return False


def _read_part(package: zipfile.ZipFile, name: str) -> ET.Element:
    try:
        return ET.fromstring(_part_bytes(package, name))
    except ET.ParseError as exc:
        _fail(2, f"{name} is not well-formed XML: {exc}")


def _rels_of(package: zipfile.ZipFile, part: str) -> dict[str, tuple[str, str]]:
    folder, name = posixpath.split(part)
    rels_name = posixpath.join(folder, "_rels", name + ".rels")
    found: dict[str, tuple[str, str]] = {}
    if rels_name not in package.namelist():
        return found
    for rel in _read_part(package, rels_name).iter(f"{REL}Relationship"):
        target = rel.get("Target", "")
        if rel.get("TargetMode") == "External":
            resolved = target
        elif target.startswith("/"):
            resolved = target.lstrip("/")
        else:
            resolved = posixpath.normpath(posixpath.join(folder, target))
        found[rel.get("Id", "")] = (rel.get("Type", "").rsplit("/", 1)[-1], resolved)
    return found


# ---------------------------------------------------------------- workbook model


class _Workbook:
    def __init__(self, path: str) -> None:
        self.path: str = path
        self.package: zipfile.ZipFile = _open_package(path)
        root = _read_part(self.package, "xl/workbook.xml")
        pr = root.find(f"{S}workbookPr")
        self.date1904: bool = pr is not None and pr.get("date1904") in ("1", "true")
        rels = _rels_of(self.package, "xl/workbook.xml")
        self.sheets: list[_Sheet] = []
        for sheet in root.iter(f"{S}sheet"):
            _, target = rels.get(sheet.get(R_ID, ""), ("", ""))
            self.sheets.append(
                {
                    "name": sheet.get("name", "?"),
                    "state": sheet.get("state", "visible"),
                    "part": target,
                }
            )
        self.defined_names: list[tuple[str, str]] = [
            (d.get("name", "?"), (d.text or "").strip()) for d in root.iter(f"{S}definedName")
        ]
        names = self.package.namelist()
        self.external_links: list[str] = sorted(
            n for n in names if re.fullmatch(r"xl/externalLinks/externalLink\d+\.xml", n)
        )
        self.has_macros: bool = "xl/vbaProject.bin" in names
        self.shared: list[str] = self._shared_strings()
        self.styles: list[tuple[int, str]] = self._styles()

    def _shared_strings(self) -> list[str]:
        if "xl/sharedStrings.xml" not in self.package.namelist():
            return []
        root = _read_part(self.package, "xl/sharedStrings.xml")
        return ["".join(t.text or "" for t in si.iter(f"{S}t")) for si in root.findall(f"{S}si")]

    def _styles(self) -> list[tuple[int, str]]:
        if "xl/styles.xml" not in self.package.namelist():
            return []
        root = _read_part(self.package, "xl/styles.xml")
        custom = {
            int(n.get("numFmtId", "0")): n.get("formatCode", "") for n in root.iter(f"{S}numFmt")
        }
        xfs = root.find(f"{S}cellXfs")
        out: list[tuple[int, str]] = []
        for xf in xfs.findall(f"{S}xf") if xfs is not None else []:
            fid = int(xf.get("numFmtId", "0"))
            out.append((fid, custom.get(fid, "")))
        return out

    def sheet(self, name: str) -> _Sheet:
        for s in self.sheets:
            if s["name"] == name:
                return s
        _fail(2, f"no sheet named {name!r}; sheets are {[s['name'] for s in self.sheets]}")

    def number_kind(self, style_index: int) -> str:
        if style_index >= len(self.styles):
            return "general"
        fid, code = self.styles[style_index]
        if fid in BUILTIN_PERCENT_FORMATS or "%" in code:
            return "percent"
        if fid in BUILTIN_DATE_FORMATS:
            return "date"
        stripped = re.sub(r'"[^"]*"|\[[^\]]*\]|\\.', "", code).lower()
        if stripped and re.search(r"[dmyhs]", stripped) and "general" not in stripped:
            return "date"
        return "general"

    def serial_to_date(self, serial: float) -> str:
        # A serial date is a day count with no timezone: the arithmetic runs in UTC so no
        # local offset can shift it, and the result drops the zone again because the
        # workbook never had one.
        utc = dt.timezone.utc
        base = (
            dt.datetime(1904, 1, 1, tzinfo=utc)
            if self.date1904
            else dt.datetime(1899, 12, 30, tzinfo=utc)
        )
        moment = (base + dt.timedelta(days=serial)).replace(tzinfo=None)
        if moment.time() == dt.time(0):
            return moment.date().isoformat()
        return moment.isoformat(timespec="seconds")


def _col_to_num(col: str) -> int:
    n = 0
    for ch in col:
        n = n * 26 + (ord(ch) - 64)
    return n


def _num_to_col(n: int) -> str:
    out = ""
    while n:
        n, rem = divmod(n - 1, 26)
        out = chr(65 + rem) + out
    return out


def _split_ref(ref: str) -> tuple[int, int]:
    m = re.fullmatch(r"\$?([A-Z]{1,3})\$?([0-9]+)", ref)
    if not m:
        raise ValueError(ref)
    return _col_to_num(m.group(1)), int(m.group(2))


def _shift_formula(formula: str, d_row: int, d_col: int) -> str:
    """Translate a shared formula from its master cell to a child cell."""
    parts = re.split(r'("[^"]*")', formula)

    def move(m: re.Match[str]) -> str:
        col_abs, col, row_abs, row = m.groups()
        c = _col_to_num(col) + (0 if col_abs else d_col)
        r = int(row) + (0 if row_abs else d_row)
        return f"{col_abs}{_num_to_col(c)}{row_abs}{r}"

    return "".join(p if p.startswith('"') else REF_RE.sub(move, p) for p in parts)


def _relative_pattern(formula: str, col: int, row: int) -> str:
    """Normalize a formula to R1C1-style relative form to compare formulas down a column."""
    parts = re.split(r'("[^"]*")', formula)

    def rel(m: re.Match[str]) -> str:
        col_abs, c, row_abs, r = m.groups()
        cc = f"C{_col_to_num(c)}" if col_abs else f"C[{_col_to_num(c) - col}]"
        rr = f"R{r}" if row_abs else f"R[{int(r) - row}]"
        return rr + cc

    return "".join(p if p.startswith('"') else REF_RE.sub(rel, p) for p in parts)


def _resolve_formula(
    f_el: ET.Element | None, shared_masters: dict[str, tuple[str, int, int]], col: int, row: int
) -> str | None:
    if f_el is None:
        return None
    text = (f_el.text or "").strip()
    if f_el.get("t") != "shared":
        return text or None
    si = f_el.get("si", "")
    if text:
        shared_masters[si] = (text, col, row)
        return text
    if si in shared_masters:
        master, mc, mr = shared_masters[si]
        return _shift_formula(master, row - mr, col - mc)
    return None


def _resolve_value(
    book: _Workbook, el: ET.Element, ctype: str, raw: str | None
) -> tuple[str | int | float | bool | None, bool]:
    if ctype == "inlineStr":
        return "".join(t.text or "" for t in el.iter(f"{S}t")), True
    if raw is None or (raw == "" and ctype != "str"):
        return None, False
    value: str | int | float | bool
    if ctype == "s":
        idx = int(raw)
        value = book.shared[idx] if idx < len(book.shared) else f"<missing shared string {idx}>"
    elif ctype == "b":
        value = raw in ("1", "true")
    elif ctype in ("e", "str", "d"):
        value = raw
    else:
        try:
            parsed = float(raw)
            value = int(parsed) if parsed.is_integer() and "e" not in raw.lower() else parsed
        except ValueError:
            value = raw
    return value, True


def _iter_cells(book: _Workbook, sheet: _Sheet) -> Iterator[_Cell]:
    """Stream cells in document order, one `_Cell` per non-skipped `<c>` element."""
    part = sheet["part"]
    if part not in book.package.namelist():
        _fail(2, f"sheet {sheet['name']!r} points to missing part {part}")
    data = _part_bytes(book.package, part)
    shared_masters: dict[str, tuple[str, int, int]] = {}
    row_hidden = False

    for event, el in _iterparse(io.BytesIO(data), ("start", "end")):
        if event == "start" and el.tag == f"{S}row":
            row_hidden = el.get("hidden") in ("1", "true")
            continue
        if event == "end" and el.tag == f"{S}row":
            el.clear()  # its cells were yielded; keep memory flat on large sheets
            continue
        if event != "end" or el.tag != f"{S}c":
            continue
        ref = el.get("r", "")
        try:
            col, row = _split_ref(ref)
        except ValueError:
            el.clear()
            continue
        ctype = el.get("t", "n")
        style = int(el.get("s", "0"))
        formula = _resolve_formula(el.find(f"{S}f"), shared_masters, col, row)
        v_el = el.find(f"{S}v")
        raw = v_el.text if v_el is not None else None
        value, has_cache = _resolve_value(book, el, ctype, raw)
        yield {
            "ref": ref,
            "col": col,
            "row": row,
            "type": ctype,
            "value": value,
            "formula": formula,
            "cached": has_cache,
            "style": style,
            "hidden_row": row_hidden,
        }
        el.clear()


def _col_span(col: ET.Element) -> str:
    lo, hi = int(col.get("min", "0")), int(col.get("max", "0"))
    return _num_to_col(lo) if lo == hi else f"{_num_to_col(lo)}:{_num_to_col(hi)}"


def _sheet_layout(book: _Workbook, sheet: _Sheet) -> _SheetLayout:
    """Dimension, merged ranges and hidden columns, read in one streaming pass."""
    data = _part_bytes(book.package, sheet["part"])
    layout: _SheetLayout = {"dimension": "", "merged": [], "hidden_cols": []}
    try:
        for _, el in _iterparse(io.BytesIO(data), ("end",)):
            if el.tag == f"{S}dimension":
                layout["dimension"] = el.get("ref", "")
            elif el.tag == f"{S}mergeCell":
                layout["merged"].append(el.get("ref", ""))
            elif el.tag == f"{S}col" and el.get("hidden") in ("1", "true"):
                layout["hidden_cols"].append(_col_span(el))
            elif el.tag == f"{S}row":
                el.clear()
    except ET.ParseError as exc:
        _fail(2, f"{sheet['part']} is not well-formed XML: {exc}")
    return layout


def _display(book: _Workbook, cell: _Cell) -> str:
    value = cell["value"]
    if value is None:
        return "<no cached value>" if cell["formula"] else "<empty>"
    kind = book.number_kind(cell["style"])
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if kind == "date":
            return f"{book.serial_to_date(float(value))} (serial {value})"
        if kind == "percent":
            return f"{value * 100:g}% (stored {value})"
    return repr(value) if isinstance(value, str) else str(value)


def _explain_formula(formula: str) -> str:
    note = (
        " [_xlfn. = function newer than Excel 2007, prefix hidden in Excel]"
        if "_xlfn." in formula
        else ""
    )
    return f"={formula}{note}"


# ---------------------------------------------------------------- summary


def _formula_outliers(by_col: dict[int, list[tuple[str, str]]]) -> list[str]:
    """Cells whose formula pattern differs from its column's majority pattern."""
    outliers: list[str] = []
    for entries in by_col.values():
        if len(entries) < MIN_OUTLIER_SAMPLE:
            continue
        common, count = Counter(p for _, p in entries).most_common(1)[0]
        if count >= MIN_OUTLIER_MAJORITY:
            outliers += [ref for ref, p in entries if p != common]
    return outliers


def _sheet_audit(book: _Workbook, sheet: _Sheet) -> None:
    layout = _sheet_layout(book, sheet)
    cells = formulas = 0
    missing: list[str] = []
    errors: list[str] = []
    hidden_rows: set[int] = set()
    by_col: dict[int, list[tuple[str, str]]] = {}
    for cell in _iter_cells(book, sheet):
        cells += 1
        if cell["hidden_row"]:
            hidden_rows.add(cell["row"])
        if cell["type"] == "e" or (isinstance(cell["value"], str) and cell["value"] in ERRORS):
            errors.append(f"{cell['ref']}={cell['value']}")
        if not cell["formula"]:
            continue
        formulas += 1
        if not cell["cached"]:
            missing.append(cell["ref"])
        by_col.setdefault(cell["col"], []).append(
            (cell["ref"], _relative_pattern(cell["formula"], cell["col"], cell["row"]))
        )
    outliers = _formula_outliers(by_col)
    print(
        f"== SHEET {sheet['name']!r} state={sheet['state']} dimension={layout['dimension']}",
        f"cells={cells} formulas={formulas}",
    )
    print(f"   formulas_without_cached_value={len(missing)} {_cap(missing)}")
    print(f"   error_cells={len(errors)} {_cap(errors)}")
    print(
        f"   formula_outliers_by_column={len(outliers)} {_cap(outliers)}",
        "(formula differs from its column's pattern)",
    )
    print(
        f"   merged={_cap(layout['merged'])}",
        f"hidden_rows={_cap([str(r) for r in sorted(hidden_rows)])}",
        f"hidden_cols={_cap(layout['hidden_cols'])}",
    )


def _cmd_summary(book: _Workbook) -> None:
    macros = (
        "YES (xl/vbaProject.bin present: not executed, not inspected)" if book.has_macros else "no"
    )
    print(
        f"FILE {book.path} sheets={len(book.sheets)} date1904={book.date1904}",
        f"macros={macros} external_links={len(book.external_links)}",
    )
    for name, text in book.defined_names:
        print(f"defined_name {name} = {text}")
    for link in book.external_links:
        print(
            f"external_link {link} (formulas pointing to [n] use another workbook;",
            "cached values are the only data)",
        )
    for sheet in book.sheets:
        _sheet_audit(book, sheet)


def _cap(items: list[str]) -> str:
    if not items:
        return "[]"
    shown = ", ".join(items[:LIST_CAP])
    more = f" … and {len(items) - LIST_CAP} more" if len(items) > LIST_CAP else ""
    return f"[{shown}{more}]"


# ---------------------------------------------------------------- cells


def _parse_range(spec: str | None) -> tuple[int, int, int, int] | None:
    if not spec:
        return None
    a, _, b = spec.upper().partition(":")
    c1, r1 = _split_ref(a)
    c2, r2 = _split_ref(b or a)
    return min(c1, c2), min(r1, r2), max(c1, c2), max(r1, r2)


def _cmd_cells(book: _Workbook, sheet_name: str, spec: str | None) -> None:
    sheet = book.sheet(sheet_name)
    box = _parse_range(spec)
    shown = 0
    for cell in _iter_cells(book, sheet):
        if box and not (box[0] <= cell["col"] <= box[2] and box[1] <= cell["row"] <= box[3]):
            continue
        if cell["value"] is None and not cell["formula"]:
            continue
        shown += 1
        parts = [f"{sheet_name}!{cell['ref']}: {_display(book, cell)}"]
        if cell["formula"]:
            parts.append(f"formula {_explain_formula(cell['formula'])}")
            parts.append("cached" if cell["cached"] else "NOT CALCULATED (no cached value)")
        if cell["hidden_row"]:
            parts.append("hidden row")
        print(" | ".join(parts))
    print(
        f"COVERED {shown} non-empty cells in",
        f"{sheet_name!r}{' range ' + spec if spec else ' (whole sheet)'}",
    )


# ---------------------------------------------------------------- recompute


class _UnsupportedError(Exception):
    pass


TOKEN_RE = re.compile(
    r"""
    \s*(?:
        (?P<num>\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)
        |(?P<str>"[^"]*")
        |(?P<ref>(?:'[^']+'|[A-Za-z0-9_]+)?!?\$?[A-Z]{1,3}\$?\d+(?::\$?[A-Z]{1,3}\$?\d+)?)
        |(?P<func>[A-Z][A-Z0-9.]*)\(
        |(?P<op>[-+*/^(),:])
    )
    """,
    re.VERBOSE,
)
FUNCS = {"SUM", "AVERAGE", "MIN", "MAX", "COUNT", "COUNTA", "ROUND", "ABS", "DATE"}


def _tokenize(formula: str) -> list[tuple[str, str]]:
    tokens: list[tuple[str, str]] = []
    pos = 0
    while pos < len(formula):
        m = TOKEN_RE.match(formula, pos)
        if not m or m.end() == pos:
            if formula[pos:].strip() == "":
                break
            msg = f"cannot parse near {formula[pos : pos + 12]!r}"
            raise _UnsupportedError(msg)
        kind = m.lastgroup
        if kind is None:
            msg = f"unnamed token near {formula[pos : pos + 12]!r}"
            raise _UnsupportedError(msg)
        tokens.append((kind, m.group(kind)))
        pos = m.end()
    return tokens


class _Evaluator:
    def __init__(self, book: _Workbook, sheet_name: str, cells: dict[str, _Cell]) -> None:
        self.book: _Workbook = book
        self.sheet_name: str = sheet_name
        self.cells: dict[str, _Cell] = cells
        self.memo: dict[str, object] = {}
        self.stack: set[str] = set()
        self.tokens: list[tuple[str, str]] = []
        self.i: int = 0

    def value_of(self, ref: str) -> object:
        ref = ref.replace("$", "")
        if ref in self.memo:
            return self.memo[ref]
        cell = self.cells.get(ref)
        if cell is None:
            return None
        if cell["cached"] or not cell["formula"]:
            return cell["value"]
        if ref in self.stack:
            msg = f"circular reference through {ref}"
            raise _UnsupportedError(msg)
        self.stack.add(ref)
        try:
            result = self.evaluate(cell["formula"])
        finally:
            self.stack.discard(ref)
        self.memo[ref] = result
        return result

    def range_values(self, ref: str) -> list[object]:
        if "!" in ref:
            sheet, _, ref = ref.rpartition("!")
            if sheet.strip("'") != self.sheet_name:
                msg = f"reference to another sheet ({sheet}) is not recomputed"
                raise _UnsupportedError(msg)
        if ":" not in ref:
            return [self.value_of(ref)]
        a, b = ref.replace("$", "").split(":")
        c1, r1 = _split_ref(a)
        c2, r2 = _split_ref(b)
        if (c2 - c1 + 1) * (r2 - r1 + 1) > MAX_RECOMPUTE_CELLS:
            msg = f"range {ref} too large to recompute"
            raise _UnsupportedError(msg)
        return [
            self.value_of(f"{_num_to_col(c)}{r}")
            for r in range(r1, r2 + 1)
            for c in range(c1, c2 + 1)
        ]

    def evaluate(self, formula: str) -> object:
        if "[" in formula:
            msg = "external workbook reference"
            raise _UnsupportedError(msg)
        # value_of() re-enters here for an uncached cell the formula refers to, so the
        # caller's token list and cursor are put back when this formula is done.
        outer = (self.tokens, self.i)
        self.tokens, self.i = _tokenize(formula), 0
        try:
            result = self.expr()
            if self.i != len(self.tokens):
                msg = "trailing tokens"
                raise _UnsupportedError(msg)
        finally:
            self.tokens, self.i = outer
        return result

    def peek(self) -> tuple[str, str] | None:
        return self.tokens[self.i] if self.i < len(self.tokens) else None

    def take(self) -> tuple[str, str]:
        tok = self.tokens[self.i]
        self.i += 1
        return tok

    def expr(self) -> object:
        left = self.term()
        while self.peek() in (("op", "+"), ("op", "-")):
            op = self.take()[1]
            right = self.term()
            left = _num(left) + _num(right) if op == "+" else _num(left) - _num(right)
        return left

    def term(self) -> object:
        left = self.power()
        while self.peek() in (("op", "*"), ("op", "/")):
            op = self.take()[1]
            right = self.power()
            if op == "*":
                left = _num(left) * _num(right)
            else:
                if _num(right) == 0:
                    return "#DIV/0!"
                left = _num(left) / _num(right)
        return left

    def power(self) -> object:
        base = self.unary()
        if self.peek() == ("op", "^"):
            _ = self.take()
            left, right = _num(base), _num(self.unary())
            if left == 0 and right < 0:
                return "#DIV/0!"
            try:
                return math.pow(left, right)
            except (ValueError, OverflowError):
                return "#NUM!"
        return base

    def unary(self) -> object:
        if self.peek() == ("op", "-"):
            _ = self.take()
            return -_num(self.unary())
        if self.peek() == ("op", "+"):
            _ = self.take()
            return _num(self.unary())
        return self.atom()

    def _parse_one_arg(self) -> list[object]:
        tok = self.peek()
        if tok is not None and tok[0] == "ref":
            save = self.i
            _, ref_text = self.take()
            if self.peek() in (("op", ","), ("op", ")")):
                return self.range_values(ref_text)
            self.i = save
        return [self.expr()]

    def _parse_call_args(self) -> list[list[object]]:
        args: list[list[object]] = []
        if self.peek() == ("op", ")"):
            return args
        while True:
            args.append(self._parse_one_arg())
            if self.peek() == ("op", ","):
                _ = self.take()
                continue
            break
        return args

    def atom(self) -> object:
        kind, text = self.take()
        if kind == "num":
            return float(text)
        if kind == "str":
            return text[1:-1]
        if kind == "ref":
            values = self.range_values(text)
            if len(values) != 1:
                msg = f"range {text} used outside a function"
                raise _UnsupportedError(msg)
            return values[0]
        if kind == "op" and text == "(":
            value = self.expr()
            self.expect(")")
            return value
        if kind == "func":
            return self._call(text)
        msg = f"unexpected token {text!r}"
        raise _UnsupportedError(msg)

    def _call(self, text: str) -> object:
        name = text.upper().replace("_XLFN.", "")
        if name not in FUNCS:
            msg = f"function {name} is not supported by the safe evaluator"
            raise _UnsupportedError(msg)
        args = self._parse_call_args()
        self.expect(")")
        result = _apply_func(name, args)
        if name == "DATE" and isinstance(result, float) and self.book.date1904:
            result -= DATE1904_OFFSET_DAYS
        return result

    def expect(self, op: str) -> None:
        if self.peek() != ("op", op):
            msg = f"expected {op!r}"
            raise _UnsupportedError(msg)
        _ = self.take()


def _num(value: object) -> float:
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, (int, float)):
        return float(value)
    if value is None or value == "":
        return 0.0
    if isinstance(value, str) and value in ERRORS:
        msg = f"operand is an error value {value}"
        raise _UnsupportedError(msg)
    try:
        return float(str(value))
    except ValueError:
        msg = f"non-numeric operand {value!r}"
        raise _UnsupportedError(msg) from None


def _func_sum(_flat: list[object], numbers: list[float], _args: list[list[object]]) -> object:
    return math.fsum(numbers)


def _func_average(_flat: list[object], numbers: list[float], _args: list[list[object]]) -> object:
    return math.fsum(numbers) / len(numbers) if numbers else "#DIV/0!"


def _func_min(_flat: list[object], numbers: list[float], _args: list[list[object]]) -> object:
    return min(numbers) if numbers else 0.0


def _func_max(_flat: list[object], numbers: list[float], _args: list[list[object]]) -> object:
    return max(numbers) if numbers else 0.0


def _func_count(_flat: list[object], numbers: list[float], _args: list[list[object]]) -> object:
    return float(len(numbers))


def _func_counta(flat: list[object], _numbers: list[float], _args: list[list[object]]) -> object:
    return float(sum(1 for v in flat if v not in (None, "")))


def _func_abs(flat: list[object], _numbers: list[float], _args: list[list[object]]) -> object:
    return abs(_num(flat[0]))


def _func_round(_flat: list[object], _numbers: list[float], args: list[list[object]]) -> object:
    # Excel rounds halves away from zero on the decimal it displays (ROUND(2.5,0) is 3,
    # ROUND(0.125,2) is 0.13); Python's round() rounds halves to even on the binary value.
    value, digits = _num(args[0][0]), int(_num(args[1][0])) if len(args) > 1 else 0
    step = Decimal(1).scaleb(-digits)
    return float(Decimal(repr(value)).quantize(step, rounding=ROUND_HALF_UP))


def _func_date(_flat: list[object], _numbers: list[float], args: list[list[object]]) -> object:
    y, m, d = (int(_num(a[0])) for a in args[:3])
    if 0 <= y < EXCEL_YEAR_BASE:
        y += EXCEL_YEAR_BASE  # Excel reads DATE(99,1,1) as 1999
    y += (m - 1) // 12
    m = (m - 1) % 12 + 1
    return float((dt.date(y, m, 1) + dt.timedelta(days=d - 1) - dt.date(1899, 12, 30)).days)


_FUNC_HANDLERS: dict[str, Callable[[list[object], list[float], list[list[object]]], object]] = {
    "SUM": _func_sum,
    "AVERAGE": _func_average,
    "MIN": _func_min,
    "MAX": _func_max,
    "COUNT": _func_count,
    "COUNTA": _func_counta,
    "ABS": _func_abs,
    "ROUND": _func_round,
    "DATE": _func_date,
}


def _apply_func(name: str, args: list[list[object]]) -> object:
    flat = [v for group in args for v in group]
    numbers = [float(v) for v in flat if isinstance(v, (int, float)) and not isinstance(v, bool)]
    for v in flat:
        if isinstance(v, str) and v in ERRORS:
            return v
    handler = _FUNC_HANDLERS.get(name)
    if handler is None:
        raise _UnsupportedError(name)
    return handler(flat, numbers, args)


def _recompute_one(
    book: _Workbook, ev: _Evaluator, sheet_name: str, cell: _Cell
) -> tuple[str, int]:
    """Evaluate one formula cell; return its report line and 1 when recomputed, else 0."""
    where = f"{sheet_name}!{cell['ref']}"
    try:
        result = ev.value_of(cell["ref"])
    except _UnsupportedError as exc:
        return f"{where}: NOT RECOMPUTED ({exc}) formula ={cell['formula']}", 0
    except (ValueError, IndexError, ArithmeticError, RecursionError) as exc:
        # A formula the safe evaluator cannot take (missing arguments, a year Python's date
        # cannot hold, nesting too deep) is reported for this cell; the rest still run.
        reason = f"cannot evaluate: {type(exc).__name__}"
        return f"{where}: NOT RECOMPUTED ({reason}) formula ={cell['formula']}", 0
    if isinstance(result, float) and not math.isfinite(result):
        result = "#NUM!"
    if result is None:
        shown = "<empty>"
    elif isinstance(result, (str, int, float, bool)):
        shown_cell: _Cell = {**cell, "value": result, "formula": None}
        shown = _display(book, shown_cell)
    else:
        shown = str(result)
    return (
        f"{where}: RECOMPUTED {shown} from ={cell['formula']} (not a value stored by Excel)",
        1,
    )


def _cmd_recompute(book: _Workbook, sheet_name: str) -> None:
    if book.external_links:
        print("NOTE workbook has external links: formulas that use them are not recomputed")
    sheet = book.sheet(sheet_name)
    cells = {c["ref"]: c for c in _iter_cells(book, sheet)}
    ev = _Evaluator(book, sheet_name, cells)
    todo = [c for c in cells.values() if c["formula"] and not c["cached"]]
    done = 0
    for cell in sorted(todo, key=lambda c: (c["row"], c["col"])):
        line, ok = _recompute_one(book, ev, sheet_name, cell)
        print(line)
        done += ok
    print(
        f"COVERED {len(todo)} formulas without cached value in {sheet_name!r}:",
        f"{done} recomputed, {len(todo) - done} not",
    )


def main() -> None:
    """Parse the command line and run the summary, cells or recompute subcommand."""
    doc = __doc__ or ""
    parser = argparse.ArgumentParser(description=doc.split("\n", 1)[0])
    sub = parser.add_subparsers(dest="command", required=True)
    p_sum = sub.add_parser("summary", help="workbook and per-sheet audit summary")
    _ = p_sum.add_argument("path")
    p_cells = sub.add_parser("cells", help="cells of one sheet with locators")
    _ = p_cells.add_argument("path")
    _ = p_cells.add_argument("--sheet", required=True)
    _ = p_cells.add_argument("--range", help="A1-style range such as A1:D20")
    p_rec = sub.add_parser("recompute", help="evaluate formulas that have no cached value")
    _ = p_rec.add_argument("path")
    _ = p_rec.add_argument("--sheet", required=True)
    values: dict[str, object] = vars(parser.parse_args())
    book = _Workbook(str(values["path"]))
    command = str(values["command"])
    try:
        if command == "summary":
            _cmd_summary(book)
        elif command == "cells":
            range_spec = values["range"]
            sheet = str(values["sheet"])
            _cmd_cells(book, sheet, str(range_spec) if range_spec is not None else None)
        else:
            _cmd_recompute(book, str(values["sheet"]))
    except ET.ParseError as exc:
        _fail(2, f"{values['path']} has a sheet that is not well-formed XML: {exc}")
    except ValueError as exc:
        _fail(2, f"{values['path']} has a malformed value or --range ({exc}); not verified")


if __name__ == "__main__":
    main()
