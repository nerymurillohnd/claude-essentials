#!/usr/bin/env python3
"""Profile and read CSV/TSV files of any size in one streaming pass (stdlib only).

Subcommands:
  profile FILE                 exact row count, delimiter, encoding, header, ragged rows,
                               and per-column non-empty/numeric counts, min, max, sum.
  rows FILE --from N --to M    print data rows N..M with their file line numbers.
  find FILE --pattern REGEX [--column NAME]
                               every row whose cell matches, with its line number.

Locators: "line L" is the physical line in the file (header = line 1);
"row R" is the data row number (first row after the header = row 1).
Sums are exact decimal sums of the text as written (constant memory); nothing is
rounded or sampled. Only plain decimal numbers count as numeric: codes such as
2024_001 or 00123 (underscores, leading zeros) are identifiers and are never summed.

Encoding: UTF-8 (with or without BOM), UTF-16 by BOM, else Windows-1252 when every
byte is valid there. Anything else stops with exit 2; pass --encoding NAME only
when the source of the file tells you its encoding.

Exit codes: 0 ok, 2 unreadable or not delimited text, 5 python3 older than 3.14.
"""

from __future__ import annotations

import argparse
import contextlib
import csv
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import TYPE_CHECKING, NoReturn, TypedDict

if TYPE_CHECKING:
    from _csv import Reader as CSVReader
    from collections.abc import Generator
import math
import re
import sys

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


LIST_CAP = 25
SNIFF_BYTES = 64 * 1024


def _fail(code: int, message: str) -> NoReturn:
    print(f"ERROR: {message}", file=sys.stderr)
    sys.exit(code)


def _required_int(value: object) -> int:
    """Return an argparse `type=int, required=True` option, which is always an int."""
    if not isinstance(value, int):
        _fail(2, f"expected an integer, got {value!r}")
    return value


def _detect_encoding(path: str) -> str:
    with Path(path).open("rb") as handle:
        head = handle.read(4)
    if head.startswith(b"\xef\xbb\xbf"):
        return "utf-8-sig"
    if head[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return "utf-16"
    for encoding in ("utf-8", "cp1252"):
        try:
            with Path(path).open(encoding=encoding) as handle:
                for _ in handle:
                    pass
        except UnicodeDecodeError:
            continue
        return encoding
    msg = f"{path} is neither UTF-8 nor Windows-1252 text; its encoding is unknown. "
    msg += "Report it as not verified, or rerun with --encoding NAME if the file's source "
    msg += "states the encoding."
    _fail(2, msg)


@contextlib.contextmanager
def _open_reader(
    path: str, delimiter: str | None, encoding: str | None = None
) -> Generator[tuple[CSVReader, str, str]]:
    """Yield (csv reader, encoding, delimiter); the file is closed on exit."""
    encoding = encoding or _detect_encoding(path)
    with Path(path).open(encoding=encoding, newline="") as handle:
        sample = handle.read(SNIFF_BYTES)
        _ = handle.seek(0)
        if not sample.strip():
            _fail(2, f"{path} is empty")
        if delimiter is None:
            try:
                delimiter = csv.Sniffer().sniff(sample, delimiters=",;\t|").delimiter
            except csv.Error:
                delimiter = "\t" if path.lower().endswith(".tsv") else ","
        # strict: a quote that never closes is an error (exit 2), not a field that swallows
        # the rest of the file and makes the row count wrong.
        yield csv.reader(handle, delimiter=delimiter, strict=True), encoding, delimiter


NUMBER = re.compile(r"[+-]?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?|[+-]?\.[0-9]+")


def _is_number(text: str) -> float | None:
    text = text.strip()
    # float() also accepts "2024_001", "nan", "inf" and " 1 "; lot and invoice codes
    # must stay text, so only plain decimal notation counts.
    if not NUMBER.fullmatch(text):
        return None
    try:
        value = float(text)
    except ValueError:
        return None
    return value if math.isfinite(value) else None


class _ColumnStats(TypedDict):
    non_empty: int
    numeric: int
    min: float | None
    max: float | None
    sum: Decimal


def _new_stats(width: int) -> list[_ColumnStats]:
    return [
        {"non_empty": 0, "numeric": 0, "min": None, "max": None, "sum": Decimal(0)}
        for _ in range(width)
    ]


def _update_column(st: _ColumnStats, cell: str) -> None:
    if cell.strip():
        st["non_empty"] += 1
    value = _is_number(cell)
    if value is None:
        return
    st["numeric"] += 1
    try:
        st["sum"] += Decimal(cell.strip())
    except InvalidOperation:
        st["sum"] += Decimal(repr(value))
    st["min"] = value if st["min"] is None else min(st["min"], value)
    st["max"] = value if st["max"] is None else max(st["max"], value)


@dataclass
class _ProfileResult:
    rows: int
    last_line: int
    header: list[str]
    stats: list[_ColumnStats]
    ragged: list[str]


def _profile_rows(
    reader: CSVReader, header: list[str], stats: list[_ColumnStats]
) -> _ProfileResult:
    width = len(header)
    rows = 0
    ragged: list[str] = []
    for row in reader:
        rows += 1
        if len(row) != width:
            ragged.append(f"line {reader.line_num} has {len(row)} fields")
        for i, cell in enumerate(row[:width]):
            _update_column(stats[i], cell)
    return _ProfileResult(rows, reader.line_num, header, stats, ragged)


def _print_profile(
    path: str, encoding: str, used_delimiter: str, width: int, result: _ProfileResult
) -> None:
    note = (
        " (not UTF-8: decoded as Windows-1252, check accented characters)"
        if encoding == "cp1252"
        else ""
    )
    print(
        f"FILE {path} encoding={encoding}{note} delimiter={used_delimiter!r} columns={width}",
        f"data_rows={result.rows}",
        f"(header on line 1, last data row ends on line {result.last_line})",
    )
    ragged = result.ragged
    shown = ragged[:LIST_CAP]
    print(f"ragged_rows={len(ragged)} {shown}{' …' if len(ragged) > LIST_CAP else ''}")
    for name, st in zip(result.header, result.stats):
        line = f"column {name!r}: non_empty={st['non_empty']} numeric={st['numeric']}"
        if st["numeric"]:
            line += f" min={st['min']:g} max={st['max']:g} sum={st['sum']}"
        print(line)
    print(f"COVERED all {result.rows} data rows")


def _cmd_profile(path: str, delimiter: str | None, forced_encoding: str | None) -> None:
    with _open_reader(path, delimiter, forced_encoding) as (reader, encoding, used_delimiter):
        try:
            header = next(reader)
        except StopIteration:
            _fail(2, f"{path} has no rows")
        stats = _new_stats(len(header))
        result = _profile_rows(reader, header, stats)
    _print_profile(path, encoding, used_delimiter, len(header), result)


def _cmd_rows(
    path: str, delimiter: str | None, encoding: str | None, first: int, last: int
) -> None:
    if first < 1 or last < first:
        _fail(2, "row range must satisfy 1 <= from <= to")
    with _open_reader(path, delimiter, encoding) as (reader, _, _):
        header: list[str] = next(reader, None) or []
        print(f"header (line 1): {header}")
        printed = 0
        for index, row in enumerate(reader, 1):
            if index > last:
                break
            if index >= first:
                print(f"row {index} (line {reader.line_num}): {row}")
                printed += 1
    print(
        f"COVERED rows {first}-{first + printed - 1}"
        if printed
        else "COVERED no rows (range past end of file)"
    )


def _cmd_find(
    path: str, delimiter: str | None, encoding: str | None, pattern: str, column: str | None
) -> None:
    try:
        regex = re.compile(pattern)
    except re.error as exc:
        _fail(2, f"--pattern is not a valid regular expression: {exc}")
    hits = 0
    row_number = 0
    with _open_reader(path, delimiter, encoding) as (reader, _, _):
        header: list[str] = next(reader, None) or []
        index = None
        if column is not None:
            if column not in header:
                _fail(2, f"no column {column!r}; columns are {header}")
            if header.count(column) > 1:
                _fail(2, f"column {column!r} appears {header.count(column)} times; it is ambiguous")
            index = header.index(column)
        for row_number, row in enumerate(reader, 1):
            # A ragged row without the named column has nothing in it to match; searching
            # its other cells would cite them as that column.
            cells = row if index is None else row[index : index + 1]
            if any(regex.search(c) for c in cells):
                hits += 1
                print(f"row {row_number} (line {reader.line_num}): {row}")
        print(f"COVERED all {row_number} data rows; matches={hits}")


def main() -> None:
    """Parse the command line and run the profile, rows or find subcommand."""
    doc = __doc__ or ""
    parser = argparse.ArgumentParser(description=doc.split("\n", 1)[0])
    _ = parser.add_argument(
        "--delimiter", help="force a delimiter instead of sniffing (use $'\\t' for tab)"
    )
    _ = parser.add_argument(
        "--encoding", help="force a text encoding (only when the file's source states it)"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("profile")
    _ = p.add_argument("path")
    r = sub.add_parser("rows")
    _ = r.add_argument("path")
    _ = r.add_argument("--from", dest="first", type=int, required=True)
    _ = r.add_argument("--to", dest="last", type=int, required=True)
    f = sub.add_parser("find")
    _ = f.add_argument("path")
    _ = f.add_argument("--pattern", required=True)
    _ = f.add_argument("--column")
    values: dict[str, object] = vars(parser.parse_args())
    path = str(values["path"])
    delimiter = values["delimiter"]
    encoding = values["encoding"]
    command = str(values["command"])
    try:
        if command == "profile":
            _cmd_profile(
                path,
                str(delimiter) if delimiter is not None else None,
                str(encoding) if encoding is not None else None,
            )
        elif command == "rows":
            _cmd_rows(
                path,
                str(delimiter) if delimiter is not None else None,
                str(encoding) if encoding is not None else None,
                _required_int(values["first"]),
                _required_int(values["last"]),
            )
        else:
            column = values["column"]
            _cmd_find(
                path,
                str(delimiter) if delimiter is not None else None,
                str(encoding) if encoding is not None else None,
                str(values["pattern"]),
                str(column) if column is not None else None,
            )
    except OSError as exc:
        _fail(2, f"cannot read {path}: {exc.strerror}")
    except csv.Error as exc:
        _fail(2, f"malformed delimited text: {exc}")
    except LookupError:
        _fail(2, f"unknown encoding name {encoding!r}")
    except UnicodeDecodeError as exc:
        _fail(2, f"{path} does not decode as {exc.encoding}: {exc.reason} at byte {exc.start}")


if __name__ == "__main__":
    main()
