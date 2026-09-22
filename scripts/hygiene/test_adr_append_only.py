"""X3: an accepted decision record is appended to, never rewritten.

An ADR is the record of why something is the way it is. Editing an accepted one in place
makes the repository's history agree with its present, which is the one thing a decision
record exists not to do: the reasoning that was rejected, and the constraint that has since
been lifted, are what a reader comes back for. Corrections go in an
`### Amendment — YYYY-MM-DD` section at the end.

The check is the diff against `origin/main`: on a branch, no line may be removed from a file
under `docs/decisions/`. A `---` separator is the one exception, because a new amendment
inserts one and the diff reads that as a move.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

import pytest

from scripts.common.plugins import git_output_or_none

if TYPE_CHECKING:
    from pathlib import Path

DECISIONS: Final = "docs/decisions"
"""The tree this rule covers."""

BASE: Final = "origin/main"
"""What a branch is measured against; the check is skipped without it."""

SEPARATOR: Final = "---"
"""The one removable line: inserting an amendment moves the horizontal rule."""


def _removed_lines(repo: Path) -> list[str] | None:
    """Collect the lines this branch removes from the decision records.

    Args:
        repo: The repository root.

    Returns:
        The removed lines, or None when the base ref is not available.
    """
    diff = git_output_or_none(repo, ["diff", BASE, "--", DECISIONS])
    if diff is None:
        return None
    return [
        line[1:]
        for line in diff.splitlines()
        if line.startswith("-") and not line.startswith("---")
    ]


def test_no_line_is_removed_from_an_accepted_decision(repo: Path) -> None:
    """A rewritten ADR makes the history agree with the present, which erases the decision."""
    removed = _removed_lines(repo)
    if removed is None:
        pytest.skip(f"{BASE} is not available in this checkout, so there is nothing to compare")
    offending = [line for line in removed if line.strip() != SEPARATOR]
    assert offending == [], f"removed from {DECISIONS}: {offending}"


def test_the_decision_records_are_there_to_protect(repo: Path) -> None:
    """A rule over an empty directory passes for free and says nothing."""
    assert list((repo / DECISIONS).glob("adr-*.md"))
