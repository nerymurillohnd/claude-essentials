#!/usr/bin/env python3
"""Check that commit messages or a pull request title follow Conventional Commits 1.0.0.

Usage:
  python3 scripts/check_commit_msg.py --file .git/COMMIT_EDITMSG   # git commit-msg hook
  python3 scripts/check_commit_msg.py --message "feat(my-plugin): add x"
  python3 scripts/check_commit_msg.py --range BASE..HEAD           # every commit in a range

The scope, when present, is a plugin name or a repository area (docs/releasing.md).
A breaking change is marked with `!` before the colon or a `BREAKING CHANGE:` footer.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import re
import sys

import repo

TYPES: tuple[str, ...] = (
    "feat",
    "fix",
    "docs",
    "style",
    "refactor",
    "perf",
    "test",
    "build",
    "ci",
    "chore",
    "revert",
)
MAX_HEADER_LENGTH = 100
_TYPE_ALTERNATION = "|".join(TYPES)
_HEADER_PATTERN = (
    rf"^(?P<type>{_TYPE_ALTERNATION})"
    r"(?:\((?P<scope>[a-z0-9][a-z0-9-]*)\))?(?P<bang>!)?: (?P<subject>\S.*)$"
)
HEADER_RE = re.compile(_HEADER_PATTERN)
_BREAKING_FOOTER_RE = re.compile(r"^BREAKING[ -]CHANGE: \S", re.MULTILINE)
# Merge commits created by GitHub when a branch is updated are not authored messages.
_EXEMPT_RE = re.compile(r"^Merge (?:branch|pull request|remote-tracking branch) ")


@dataclass(frozen=True)
class Parsed:
    """The parts of a Conventional Commits header."""

    type: str
    scope: str | None
    breaking: bool
    subject: str


def parse(message: str) -> tuple[Parsed | None, list[str]]:
    """Parse a commit message; return (parsed, problems)."""
    lines = [line for line in message.splitlines() if not line.startswith("#")]
    header = lines[0].strip() if lines else ""
    problems: list[str] = []
    if not header:
        return None, ["empty commit message"]
    if _EXEMPT_RE.match(header):
        return None, []
    match = HEADER_RE.match(header)
    if match is None:
        shape = "<type>(<scope>)!: <subject>"
        problems.append(f'header "{header}" must be "{shape}" with type one of: {", ".join(TYPES)}')
        return None, problems
    if len(header) > MAX_HEADER_LENGTH:
        problems.append(f"header is {len(header)} characters; the limit is {MAX_HEADER_LENGTH}")
    if len(lines) > 1 and lines[1].strip():
        problems.append("the line after the header must be blank")
    body = "\n".join(lines[1:])
    parsed = Parsed(
        type=match.group("type"),
        scope=match.group("scope"),
        breaking=bool(match.group("bang")) or bool(_BREAKING_FOOTER_RE.search(body)),
        subject=match.group("subject"),
    )
    if parsed.subject.endswith("."):
        problems.append("subject must not end with a period")
    return parsed, problems


def _messages_in_range(revision_range: str) -> list[tuple[str, str]]:
    output = repo.run(["git", "log", "--format=%H%x1f%B%x1e", revision_range]).stdout
    messages: list[tuple[str, str]] = []
    for record in output.split("\x1e"):
        if "\x1f" not in record:
            continue
        sha, body = record.split("\x1f", 1)
        messages.append((sha.strip()[:12], body.strip()))
    return messages


def main() -> int:
    """Check a message file, a single message or every commit in a range."""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    group = parser.add_mutually_exclusive_group(required=True)
    _ = group.add_argument("--file", type=Path, help="commit message file (commit-msg hook)")
    _ = group.add_argument("--message", help="a single message or pull request title")
    _ = group.add_argument("--range", dest="revision_range", help="git revision range BASE..HEAD")
    args = parser.parse_args()
    file_arg: Path | None = args.file  # pyright: ignore[reportAny]  # argparse Namespace attributes are Any
    message_arg: str | None = args.message  # pyright: ignore[reportAny]  # argparse Namespace attributes are Any
    range_arg: str | None = args.revision_range  # pyright: ignore[reportAny]  # argparse Namespace attributes are Any

    targets: list[tuple[str, str]]
    if file_arg is not None:
        targets = [(str(file_arg), file_arg.read_text(encoding="utf-8"))]
    elif message_arg is not None:
        targets = [("message", message_arg)]
    else:
        targets = _messages_in_range(range_arg or "")

    failures = 0
    for label, message in targets:
        _, problems = parse(message)
        for problem in problems:
            failures += 1
            repo.emit(f"✘ {label}: {problem}")
    if failures:
        repo.emit("\nSee docs/releasing.md#commit-messages for the convention.")
        return 1
    repo.emit(f"check_commit_msg: {len(targets)} message(s) follow Conventional Commits")
    return 0


if __name__ == "__main__":
    sys.exit(main())
