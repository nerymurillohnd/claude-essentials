#!/usr/bin/env python3
"""Probe and read a PDF page by page with poppler, giving page+line locators.

Subcommands:
  probe FILE              page count, encryption, per-page text size, pages with no
                          text layer (likely scanned: read them with vision), and a
                          20-page chunk plan covering every page.
  text FILE --pages N-M   exact text of pages N..M from the text layer, every line
                          prefixed "p<page> L<line>:" for citation.

Requires poppler (pdfinfo, pdftotext). Without it the script says so and exits 5;
the caller then falls back to the Read tool and reports the gap. Stdlib only,
read-only: the PDF is never modified.

Exit codes: 0 ok, 2 not a readable PDF or bad --pages, 3 password required,
5 poppler missing or python3 older than 3.14.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import NoReturn, TypedDict

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


CHUNK = 20


def _fail(code: int, message: str) -> NoReturn:
    print(f"ERROR: {message}", file=sys.stderr)
    sys.exit(code)


def _need(tool: str) -> str:
    found = shutil.which(tool)
    if not found:
        msg = f"{tool} not found: install poppler (macOS: brew install poppler; "
        msg += "Debian/Ubuntu: apt install poppler-utils). "
        msg += "Fallback: read the PDF with the Read tool and mark pages you could not cover "
        msg += "as not verified."
        _fail(5, msg)
    return found


def _run(args: list[str]) -> str:
    # Decode as UTF-8 whatever the locale: pdftotext and pdfinfo are told to emit UTF-8.
    proc = subprocess.run(
        args, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False
    )
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout).strip()
        if "password" in err.lower():
            _fail(3, f"password required: {err}")
        _fail(2, f"{args[0]} failed: {err or 'no message'}")
    return proc.stdout


def _info(path: str) -> dict[str, str]:
    out = _run([_need("pdfinfo"), "-enc", "UTF-8", path])
    fields: dict[str, str] = {}
    for line in out.splitlines():
        key, _, value = line.partition(":")
        fields[key.strip()] = value.strip()
    return fields


def _page_texts(path: str, first: int, last: int, *, layout: bool) -> list[str]:
    args = [_need("pdftotext"), "-f", str(first), "-l", str(last), "-enc", "UTF-8"]
    if layout:
        args.append("-layout")
    text = _run([*args, path, "-"])
    pages = text.split("\f")
    # pdftotext ends every page with a form feed, so the final element is trailing.
    if pages and pages[-1].strip() == "":
        pages = pages[:-1]
    return pages


def _parse_range(spec: str, total: int) -> tuple[int, int]:
    match = re.fullmatch(r"\s*(\d+)\s*(?:-\s*(\d+)\s*)?", spec)
    if not match:
        _fail(2, f"invalid page range {spec!r}: use N or N-M, e.g. 1-20")
    first = int(match.group(1))
    last = int(match.group(2) or first)
    if not 1 <= first <= last <= total:
        _fail(2, f"page range {spec} is outside 1-{total}")
    if last - first + 1 > CHUNK:
        msg = f"page range {spec} has {last - first + 1} pages; at most {CHUNK} pages per call. "
        msg += "Follow the chunk_plan from `probe`."
        _fail(2, msg)
    return first, last


class _ProbeResult(TypedDict):
    file: str
    pages: int
    encrypted: str
    producer: str
    page_size: str
    chars_per_page: list[int]
    pages_without_text_layer: list[int]
    chunk_plan: list[str]


def _probe(path: str) -> _ProbeResult:
    fields = _info(path)
    total = int(fields.get("Pages", "0") or 0)
    if total == 0:
        _fail(2, f"{path}: pdfinfo reports no pages")
    texts = _page_texts(path, 1, total, layout=False)
    chars = [len(t.strip()) for t in texts] + [0] * max(0, total - len(texts))
    no_text = [i for i, n in enumerate(chars, 1) if n == 0]
    chunks = [(s, min(s + CHUNK - 1, total)) for s in range(1, total + 1, CHUNK)]
    return {
        "file": path,
        "pages": total,
        "encrypted": fields.get("Encrypted", "unknown"),
        "producer": fields.get("Producer", ""),
        "page_size": fields.get("Page size", ""),
        "chars_per_page": chars,
        "pages_without_text_layer": no_text,
        "chunk_plan": [f"{a}-{b}" for a, b in chunks],
    }


def _compress(pages: list[int]) -> str:
    if not pages:
        return "none"
    ranges: list[str] = []
    start = prev = pages[0]
    for p in pages[1:]:
        if p == prev + 1:
            prev = p
            continue
        ranges.append(f"{start}-{prev}" if start != prev else str(start))
        start = prev = p
    ranges.append(f"{start}-{prev}" if start != prev else str(start))
    return ",".join(ranges)


def _print_probe(result: _ProbeResult) -> None:
    print(
        f"FILE {result['file']} pages={result['pages']} encrypted={result['encrypted']}",
        f"producer={result['producer']!r}",
    )
    print(
        f"pages_without_text_layer={_compress(result['pages_without_text_layer'])}",
        "(read these with the Read tool pages= argument: scanned or image-only)",
    )
    print(
        f"chunk_plan={' '.join(result['chunk_plan'])}",
        f"(text subcommand, at most {CHUNK} pages per call)",
    )


def _print_text(path: str, pages_spec: str, *, raw: bool) -> None:
    total = int(_info(path).get("Pages", "0") or 0)
    first, last = _parse_range(pages_spec, total)
    pages = _page_texts(path, first, last, layout=not raw)
    for offset, text in enumerate(pages):
        number = first + offset
        lines = text.splitlines()
        if not any(line.strip() for line in lines):
            print(
                f"p{number}: [no text layer on this page: read it with vision via Read",
                f"pages={number}]",
            )
            continue
        for i, line in enumerate(lines, 1):
            if line.strip():
                print(f"p{number} L{i}: {line.rstrip()}")
    print(f"COVERED pages {first}-{last} of {total}")


def main() -> None:
    """Parse the command line and run the probe or text subcommand."""
    doc = __doc__ or ""
    parser = argparse.ArgumentParser(description=doc.split("\n", 1)[0])
    sub = parser.add_subparsers(dest="command", required=True)
    p_probe = sub.add_parser("probe", help="page count, text-layer map and chunk plan")
    _ = p_probe.add_argument("path")
    _ = p_probe.add_argument("--json", action="store_true")
    p_text = sub.add_parser("text", help="exact text of a page range with p/L locators")
    _ = p_text.add_argument("path")
    _ = p_text.add_argument("--pages", required=True, help="range such as 1-20 or 7")
    _ = p_text.add_argument("--raw", action="store_true", help="reading order instead of -layout")
    values: dict[str, object] = vars(parser.parse_args())
    path = str(values["path"])

    if str(values["command"]) == "probe":
        result = _probe(path)
        if bool(values["json"]):
            json.dump(result, sys.stdout, indent=2)
            print()
            return
        _print_probe(result)
        return

    _print_text(path, str(values["pages"]), raw=bool(values["raw"]))


if __name__ == "__main__":
    main()
