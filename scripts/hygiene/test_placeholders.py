"""P4, repository-wide: no template placeholder survives outside `templates/`.

A plugin's own files are already covered by the validator. This is the other half: the root
README, the instruction files, the skills, the agents and the issue forms are all written by
copying a template, and a `{{Display Name}}` left in one of them ships to readers as the
literal text — or, in a skill, as an instruction Claude tries to follow.

Two things are deliberately not matches. A placeholder inside a backtick code span is prose
*about* placeholders, which the contributing guide and the auditor both need to write. And
`${{ … }}` is a GitHub Actions expression, which every workflow is made of.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Final

from scripts.common.plugins import working_files

if TYPE_CHECKING:
    from pathlib import Path

PLACEHOLDER: Final = re.compile(r"(?<!\$)\{\{|(?i:REPLACE-WITH-[A-Z0-9-]+)")
"""The same pattern the plugin validator uses for P4, so both halves agree."""

CODE_SPAN: Final = re.compile(r"`[^`]*`")
"""A backtick span, whose contents are prose about a placeholder rather than one."""

SWEPT: Final[tuple[str, ...]] = (
    "README.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "CODE_OF_CONDUCT.md",
    "CLAUDE.md",
    "*/CLAUDE.md",
    ".claude/*",
    ".github/*",
)
"""Everything a reader or Claude loads that was written by filling in a template."""

EXCLUDED: Final[tuple[str, ...]] = (
    "templates/*",  # the placeholders live here by definition
    ".claude/state/*",  # run state, not authored text
)
"""Where a placeholder is the point, or where nothing is authored at all."""


def _swept(repo: Path) -> list[str]:
    """List the files this check reads.

    Args:
        repo: The repository root.

    Returns:
        Sorted repository-relative paths.
    """
    excluded = set(working_files(repo, *EXCLUDED))
    return [rel for rel in sorted(working_files(repo, *SWEPT)) if rel not in excluded]


def _offenders(repo: Path) -> list[str]:
    """Find every line that still carries a placeholder.

    Args:
        repo: The repository root.

    Returns:
        One `path:line` per offending line.
    """
    found: list[str] = []
    for rel in _swept(repo):
        try:
            text = (repo / rel).read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for number, line in enumerate(text.splitlines(), 1):
            if PLACEHOLDER.search(CODE_SPAN.sub("``", line)) is not None:
                found.append(f"{rel}:{number}")
    return found


def test_the_sweep_reads_something(repo: Path) -> None:
    """A glob that matched nothing would make every assertion below pass for free."""
    assert len(_swept(repo)) > 1


def test_no_placeholder_survives_outside_the_templates(repo: Path) -> None:
    """A leftover placeholder reaches a reader as literal text, or Claude as an instruction."""
    assert _offenders(repo) == []


def test_a_github_actions_expression_is_not_a_placeholder() -> None:
    """Every workflow is made of `${{ … }}`; matching it would make the rule unusable."""
    assert PLACEHOLDER.search("run: echo ${{ github.sha }}") is None


def test_a_placeholder_in_prose_is_not_a_leftover() -> None:
    """The contributing guide has to be able to name what a contributor must replace."""
    assert PLACEHOLDER.search(CODE_SPAN.sub("``", "Replace `{{YYYY-MM-DD}}` with today.")) is None


def test_a_real_leftover_is_caught() -> None:
    """The control: the same text outside a code span is the defect this exists for."""
    assert PLACEHOLDER.search(CODE_SPAN.sub("``", "# {{Display Name}}")) is not None
