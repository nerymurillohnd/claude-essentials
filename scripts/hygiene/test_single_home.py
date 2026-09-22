"""X1: every policy table has exactly one home.

The 2026-09 audits found nine contradictions in this repository, all the same shape: a table
copied into a second document, then one copy updated. Nobody sees the other copy, so the two
answers coexist and whichever one the reader happens to open becomes the policy.

The check is a signature: the header row of each canonical table, which is distinctive enough
that a copy carries it verbatim. Three trees are outside the sweep, each for a stated reason:
`docs/superpowers/` keeps the design plans as they were written and is history by definition;
`templates/` holds the parametrised copies a new plugin is generated from; and
`docs/maintenance/resolved-debt.md` records what a table used to say.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

import pytest

from scripts.common.plugins import working_files

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True, slots=True)
class Table:
    """One canonical policy table.

    Attributes:
        what: The policy, named the way the plan names it.
        home: The repository-relative file that owns it.
        signature: A line a copy would carry verbatim.
    """

    what: str
    home: str
    signature: str


EXCLUDED: Final[tuple[str, ...]] = (
    "docs/superpowers/*",  # design plans and specs, kept as written after landing
    "templates/*",  # the parametrised copies a new plugin starts from
    "docs/maintenance/resolved-debt.md",  # records what a table used to say
)
"""Trees where a second copy is history or a template, not a contradiction."""

TABLES: Final[tuple[Table, ...]] = (
    Table(
        "catalog-row rules",
        "README.md",
        "| Plugin | Description | Kind | Claude Code | Claude Cowork | Additional requirements |",
    ),
    Table("the kind table", "README.md", "| Kind | Installing it gives you |"),
    Table("the surface lifecycle", "README.md", "| Component | Claude Code | Claude Cowork |"),
    Table(
        "the bump rules",
        "docs/contributing/versioning.md",
        "| Surface | Paths (relative to `plugins/<name>/`) | Bump? |",
    ),
    Table("the rename rules", "docs/contributing/versioning.md", "| Rename | Effect | Bump |"),
    Table(
        "the label taxonomy", "docs/contributing/labels.md", "| Family | Labels | Applied by | On |"
    ),
)
"""Measured 2026-09-21: each signature appears in exactly one file in the swept tree."""

PENDING: Final[tuple[tuple[str, str], ...]] = (
    ("the push route matrix", "step 11 writes it into `docs/contributing/versioning.md`"),
    ("the registration contract", "step 10 writes it into the nested `CLAUDE.md` files"),
)
"""Tables the plan names that this tree does not carry yet, recorded so they are not forgotten."""


def _table_id(table: Table) -> str:
    """Name a parametrised case after the policy it is about.

    Args:
        table: The case.

    Returns:
        The policy's name.
    """
    return table.what


def _pending_id(pending: tuple[str, str]) -> str:
    """Name a pending case after the table it is waiting for.

    Args:
        pending: The case.

    Returns:
        The policy's name.
    """
    return pending[0]


def _swept(repo: Path) -> list[str]:
    """List the files a duplicated table would have to live in to count.

    Args:
        repo: The repository root.

    Returns:
        Sorted repository-relative Markdown paths, the excluded trees removed.
    """
    excluded = set(working_files(repo, *EXCLUDED))
    return [rel for rel in sorted(working_files(repo, "*.md")) if rel not in excluded]


def _homes(repo: Path, signature: str) -> list[str]:
    """Find every file that carries one signature.

    Args:
        repo: The repository root.
        signature: The header row to look for.

    Returns:
        Sorted repository-relative paths.
    """
    return [rel for rel in _swept(repo) if signature in (repo / rel).read_text(encoding="utf-8")]


@pytest.mark.parametrize("table", TABLES, ids=_table_id)
def test_each_canonical_table_lives_in_exactly_one_file(repo: Path, table: Table) -> None:
    """A second copy is a second answer, and only one of them ever gets updated."""
    assert _homes(repo, table.signature) == [table.home]


@pytest.mark.parametrize("table", TABLES, ids=_table_id)
def test_each_home_is_a_file_that_exists(repo: Path, table: Table) -> None:
    """A home recorded here that nobody ships would make the rule pass by accident."""
    assert (repo / table.home).is_file()


@pytest.mark.parametrize("pending", PENDING, ids=_pending_id)
def test_a_pending_table_is_recorded_rather_than_assumed(pending: tuple[str, str]) -> None:
    """Naming what is not pinned yet is what keeps the list from looking complete."""
    what, when = pending
    assert what
    assert "step" in when
