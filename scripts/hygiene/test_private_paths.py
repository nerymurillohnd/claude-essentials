"""No tracked file names the maintainer's machine: this repository is published as it is.

Command output pasted as evidence carries absolute paths, and one pasted log put a home
directory and a private plan path on `main` (2026-09-22, the migration log). The check reads
every file git would ship and refuses the home directory of whoever runs it, which is the
maintainer locally; in CI the home is the runner's and the check guards nothing extra, so the
second pattern, a path into the private `~/.claude/plans/`, holds everywhere.
"""

from __future__ import annotations

from pathlib import Path
import re
from typing import Final

from scripts.common.plugins import working_files

PRIVATE_PLAN: Final = re.compile(r"~/\.claude/plans/")
"""A path into the maintainer's private plans, which no reader of this repository can open."""

SELF: Final = "scripts/hygiene/test_private_paths.py"
"""This file, which has to spell the pattern it refuses."""


def _offenders(repo: Path, needle: str) -> list[str]:
    """List `path:line` for each shipped text line that contains the home or a private plan.

    Args:
        repo: The repository root.
        needle: The home directory, with a trailing slash.

    Returns:
        One entry per offending line.
    """
    found: list[str] = []
    for rel in working_files(repo):
        if rel == SELF:
            continue
        try:
            text = (repo / rel).read_text(encoding="utf-8")
        except UnicodeDecodeError, OSError:
            continue
        found.extend(
            f"{rel}:{number}"
            for number, line in enumerate(text.splitlines(), 1)
            if needle in line or PRIVATE_PLAN.search(line) is not None
        )
    return found


def test_no_shipped_file_names_the_home_directory_or_a_private_plan(repo: Path) -> None:
    """Replace a pasted absolute path with `<repo>/…` or `~/…` before it is committed.

    Args:
        repo: The repository root.
    """
    offenders = _offenders(repo, f"{Path.home()}/")
    assert not offenders, offenders


def test_the_check_finds_a_pasted_home_path(tmp_path: Path) -> None:
    """The needle matches the shape of a pasted log line, so a pass means something."""
    line = f"Validating plugin manifest: {Path.home()}/projects/x/plugin.json"
    assert f"{Path.home()}/" in line
    assert PRIVATE_PLAN.search("see ~/.claude/plans/a.md") is not None
    assert tmp_path.exists()
