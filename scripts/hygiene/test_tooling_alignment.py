"""X4: nothing in the swept tree still points at the toolchain this repository replaced.

A document that tells a contributor to run `npm run check` is worse than no document: the
command fails, and the reader has no way to know whether the instruction is stale or their
machine is. The same goes for a recipe that calls a deleted `.mjs`, or an editor setting that
names a formatter the repository no longer uses.

The sweep grows one step at a time. It cannot be repository-wide today, because the
workflows, the hooks, the instruction files and the documentation are rewritten at steps 7,
8, 10 and 11 respectively; sweeping them now would fail on text that is scheduled to change.
`SWEPT_PATHS` is what is already migrated, `PENDING_PATHS` is what joins it and when, and the
second constant is what keeps the first from looking complete.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

import pytest

from scripts.common.plugins import working_files

if TYPE_CHECKING:
    from pathlib import Path

TERMS: Final[tuple[str, ...]] = ("npm ", "npx ", ".mjs", "Biome", "Knip", "tsc ")
"""The retired toolchain, spelled the way a stale instruction would spell it."""

SWEPT_PATHS: Final[tuple[str, ...]] = (
    "scripts/*.py",
    "pyproject.toml",
    "Makefile",
    ".vscode/*",
    "uv.lock",
)
"""What is migrated today and therefore has no excuse to name the old toolchain."""

EXEMPT_PATHS: Final[tuple[str, ...]] = ("scripts/*/test_*.py",)
"""Test modules, which name the tooling they exist to reject.

Measured 2026-09-21: five occurrences, each one the check itself — a guard's deny text
asserted *not* to name `.mjs` or `npm run`, a fixture seeding `npx` so the runtime-boundary
validator rejects it, a parametrised example of the `npm run validate` a checklist still
carries until step 10, and a docstring recording why the post-edit hook's Biome branch is not
covered. A sweep that flagged those would make the checks undocumentable.
"""

PENDING_PATHS: Final[tuple[tuple[str, str], ...]] = (
    (".github/**", "step 7 rewrites the workflows"),
    (".claude/hooks/** and .claude/settings.json", "step 8 switches the hooks"),
    ("CLAUDE.md and .claude/**", "step 10 rewrites the instruction files"),
    ("docs/**, README.md, CONTRIBUTING.md, SECURITY.md, templates/**", "step 11 rewrites the docs"),
)
"""What joins the sweep, and at which step, so the list is never mistaken for finished."""


def _pending_id(pending: tuple[str, str]) -> str:
    """Name a parametrised case after the tree it is about.

    Args:
        pending: The case.

    Returns:
        The tree's paths.
    """
    return pending[0]


MIN_SWEPT: Final = 10
"""Below this the globs matched almost nothing and every assertion would pass for free."""


def _swept(repo: Path) -> list[str]:
    """List the files this check reads.

    Args:
        repo: The repository root.

    Returns:
        Sorted repository-relative paths.
    """
    exempt = set(working_files(repo, *EXEMPT_PATHS))
    return [rel for rel in sorted(working_files(repo, *SWEPT_PATHS)) if rel not in exempt]


def _hits(repo: Path, term: str) -> list[str]:
    """Find every line in the swept tree that carries one term.

    Args:
        repo: The repository root.
        term: The retired tool's name.

    Returns:
        One `path:line` per occurrence.
    """
    found: list[str] = []
    for rel in _swept(repo):
        try:
            text = (repo / rel).read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        found.extend(
            f"{rel}:{number}" for number, line in enumerate(text.splitlines(), 1) if term in line
        )
    return found


def test_the_sweep_reads_something(repo: Path) -> None:
    """A glob that matched nothing would make every assertion below pass for free."""
    assert len(_swept(repo)) > MIN_SWEPT


@pytest.mark.parametrize("term", TERMS)
def test_no_swept_file_names_the_retired_toolchain(repo: Path, term: str) -> None:
    """An instruction that names a deleted tool fails, and the reader cannot tell why."""
    assert _hits(repo, term) == []


@pytest.mark.parametrize("pending", PENDING_PATHS, ids=_pending_id)
def test_every_unswept_tree_is_recorded_with_its_step(pending: tuple[str, str]) -> None:
    """A sweep that looks complete is how the last stale document survives the migration."""
    paths, when = pending
    assert paths
    assert "step" in when


def test_the_swept_and_pending_lists_do_not_overlap() -> None:
    """A tree in both lists would be swept and excused at the same time."""
    pending = " ".join(paths for paths, _ in PENDING_PATHS)
    for pattern in SWEPT_PATHS:
        assert pattern.split("/")[0] not in pending.split(), pattern
