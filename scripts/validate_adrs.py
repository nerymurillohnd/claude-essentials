#!/usr/bin/env python3
"""Validate the architecture decision records in docs/adr/decisions/.

Run: scripts/validate_adrs.py [--root PATH]

Rules (docs/adr/README.md):
  * file name `ADR_YYYY-MM-DD_<slug>.md` with a real date and a kebab-case slug;
  * frontmatter `date` equals the filename date; `status` is proposed, accepted,
    rejected, deprecated or superseded; `decision-makers` is a non-empty list;
    `consulted` and `informed`, when present, are non-empty lists;
  * one `#` title and the required sections; no template placeholders left;
  * a superseded record links to another record in decisions/;
  * every relative link resolves to an existing file.
"""

from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path
import re
import sys

import repo

FILENAME_RE = re.compile(r"^ADR_(\d{4}-\d{2}-\d{2})_([a-z0-9]+(?:-[a-z0-9]+)*)\.md$")
STATUSES = frozenset({"proposed", "accepted", "rejected", "deprecated", "superseded"})
ADR_REFERENCE_FIELDS = ("supersedes", "superseded-by")
REQUIRED_SECTIONS = (
    "## Purpose",
    "## Scope",
    "## Context and problem statement",
    "## Decision drivers",
    "## Considered options",
    "## Decision outcome",
    "### Consequences",
    "### Confirmation",
)
# Template placeholders read like `{Short title naming the decision}`; `${CLAUDE_PLUGIN_ROOT}`
# and other all-caps variables are not placeholders.
PLACEHOLDER_RE = re.compile(r"(?<!\$)\{[A-Z][a-z][^{}\n]*\}")
LINK_RE = re.compile(r"\]\(([^)#\s]+)(?:#[^)]*)?\)")


def parse_frontmatter(text: str) -> tuple[dict[str, str | list[str]], str] | None:
    """Return (fields, body) for simple YAML frontmatter, or None when it is missing."""
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---\n", 4)
    if end == -1:
        return None
    fields: dict[str, str | list[str]] = {}
    current: str | None = None
    for line in text[4:end].splitlines():
        if not line.strip():
            continue
        item = re.match(r"^\s+-\s+(.*)$", line)
        if item and current is not None:
            values = fields.get(current)
            values = values if isinstance(values, list) else []
            values.append(item.group(1).strip().strip("'\""))
            fields[current] = values
            continue
        pair = re.match(r"^([A-Za-z-]+):\s*(.*)$", line)
        if pair:
            current = str(pair.group(1))
            value = str(pair.group(2)).strip().strip("'\"")
            fields[current] = value or []
    return fields, text[end + 5 :]


def _reference_problems(fields: dict[str, str | list[str]], decisions: Path) -> list[str]:
    """Check `supersedes` and `superseded-by`: "none" or the file name of an existing record."""
    problems: list[str] = []
    for name in ADR_REFERENCE_FIELDS:
        value = fields.get(name)
        if value is None or value == "none":
            continue
        if not (
            isinstance(value, str) and FILENAME_RE.match(value) and (decisions / value).is_file()
        ):
            problems.append(
                f'{name} "{value}" must be "none" or the file name of an existing record'
            )
    successor = fields.get("superseded-by")
    if fields.get("status") == "superseded" and successor in (None, "none"):
        problems.append("a superseded record must name its successor in superseded-by")
    return problems


def _frontmatter_problems(
    fields: dict[str, str | list[str]], file_date: str, decisions: Path
) -> list[str]:
    problems: list[str] = _reference_problems(fields, decisions)
    if fields.get("date") != file_date:
        problems.append(
            f'frontmatter date "{fields.get("date")}" must equal the file name date {file_date}'
        )
    status = fields.get("status")
    if not isinstance(status, str) or status not in STATUSES:
        problems.append(f'status "{status}" must be one of: {", ".join(sorted(STATUSES))}')
    makers = fields.get("decision-makers")
    if not isinstance(makers, list) or not makers:
        problems.append("decision-makers must list at least one accountable person or role")
    problems.extend(
        f"remove the empty {optional} field"
        for optional in ("consulted", "informed")
        if optional in fields and not fields[optional]
    )
    return problems


def _structure_problems(text: str, body: str) -> list[str]:
    problems: list[str] = []
    titles = [line for line in body.splitlines() if line.startswith("# ")]
    if len(titles) != 1:
        problems.append("the record needs exactly one # title")
    problems.extend(
        f'missing "{section}" section'
        for section in REQUIRED_SECTIONS
        if not re.search(rf"^{re.escape(section)}\s*$", body, re.MULTILINE)
    )
    problems.extend(
        f"template placeholder left: {placeholder}"
        for placeholder in sorted({m.group(0) for m in PLACEHOLDER_RE.finditer(text)})
    )
    return problems


def _link_problems(
    path: Path, decisions: Path, body: str, status: str | list[str] | None
) -> list[str]:
    links = [m.group(1) for m in LINK_RE.finditer(body)]
    problems = [
        f"broken link: {target}"
        for target in links
        if "://" not in target
        and not target.startswith("mailto:")
        and not (path.parent / target).resolve().exists()
    ]
    if status == "superseded" and not any(
        FILENAME_RE.match(Path(t).name) and (decisions / Path(t).name) != path for t in links
    ):
        problems.append("a superseded record must link to the record that supersedes it")
    return problems


def validate_record(path: Path, decisions: Path) -> list[str]:
    """Return every problem of one ADR record."""
    match = FILENAME_RE.match(path.name)
    if match is None:
        return ["file name must be ADR_YYYY-MM-DD_<kebab-case-slug>.md"]
    file_date = match.group(1)
    problems: list[str] = []
    try:
        _ = dt.date.fromisoformat(file_date)
    except ValueError:
        problems.append(f'"{file_date}" in the file name is not a real date')
    text = path.read_text(encoding="utf-8")
    parsed = parse_frontmatter(text)
    if parsed is None:
        return [*problems, "missing YAML frontmatter between --- lines"]
    fields, body = parsed
    problems.extend(_frontmatter_problems(fields, file_date, decisions))
    problems.extend(_structure_problems(text, body))
    problems.extend(_link_problems(path, decisions, body, fields.get("status")))
    return problems


def validate(root: Path) -> list[str]:
    """Return every problem in docs/adr/decisions/ under `root`."""
    decisions = root / "docs" / "adr" / "decisions"
    if not decisions.is_dir():
        return ["docs/adr/decisions/ is missing"]
    problems: list[str] = []
    records = sorted(decisions.iterdir())
    if not any(p.suffix == ".md" for p in records):
        problems.append("docs/adr/decisions/ has no records")
    for path in records:
        where = path.relative_to(root)
        if path.is_dir() or path.suffix != ".md":
            problems.append(f"{where}: only ADR Markdown files belong in decisions/")
            continue
        problems.extend(f"{where}: {problem}" for problem in validate_record(path, decisions))
    return problems


def main() -> int:
    """Validate every record and report the problems."""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    _ = parser.add_argument("--root", type=Path, default=repo.ROOT, help="repository root")
    args = parser.parse_args()
    root: Path = args.root  # pyright: ignore[reportAny]  # argparse Namespace attributes are Any
    problems = validate(root.resolve())
    for problem in problems:
        repo.emit(f"✘ {problem}")
    if problems:
        repo.emit(f"\nvalidate_adrs: {len(problems)} problem(s); see docs/adr/README.md")
        return 1
    count = len(list((root / "docs" / "adr" / "decisions").glob("ADR_*.md")))
    repo.emit(f"validate_adrs: {count} record(s) valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
