"""The map of `scripts/` matches `scripts/`, and every module in it is covered by a test.

Two different drifts, both silent. The `marketplace-governance` skill is what Claude reads
before adding a maintainer script, so an area it names that no longer exists sends the next
file to a directory nobody gates; an area on disk it never names is a directory Claude does
not know it may use. And a module with no sibling test is behaviour that changes without
anything noticing, which is the rule P5 states for the maintainer's own code.

The marker check is about the two-tier suite: `make test-fast` runs everything not marked
`slow`, so a test that spawns a process without the marker makes the fast gate slow, and a
test with two markers is excluded from both halves and therefore never runs.
"""

from __future__ import annotations

from pathlib import Path
import re
from typing import Final

from scripts.common.plugins import working_files

SKILL: Final = ".claude/skills/marketplace-governance/SKILL.md"
"""The map Claude reads before adding or moving a maintainer script."""

AREA_REFERENCE: Final = re.compile(r"scripts/(?P<area>[a-z_]+)/")
"""How the map names an area, whether in prose or in the tree block."""

PACKAGE_MARKER: Final = "__init__.py"
"""What makes a directory under `scripts/` an area rather than a stray folder."""

EXEMPT_MODULES: Final[frozenset[str]] = frozenset({"__init__.py", "conftest.py"})
"""Files that carry no behaviour of their own, so they need no sibling test."""

MARKERS: Final[tuple[str, ...]] = ("slow", "coverage_matrix")
"""The two markers `pyproject.toml` declares; the gate runs one half at a time."""

MARKER_LINE: Final = re.compile(r"^@pytest\.mark\.(?P<marker>slow|coverage_matrix)\b", re.MULTILINE)
"""A marker applied to a test or a module."""


def _areas_on_disk(repo: Path) -> list[str]:
    """List the areas `scripts/` actually holds.

    Args:
        repo: The repository root.

    Returns:
        Sorted directory names.
    """
    return sorted(
        path.name
        for path in (repo / "scripts").iterdir()
        if path.is_dir() and (path / PACKAGE_MARKER).is_file()
    )


def _areas_in_map(repo: Path) -> list[str]:
    """List the areas the map names.

    Args:
        repo: The repository root.

    Returns:
        Sorted area names, deduplicated.
    """
    text = (repo / SKILL).read_text(encoding="utf-8")
    return sorted({match["area"] for match in AREA_REFERENCE.finditer(text)})


def _tree_entries(repo: Path) -> list[str]:
    """Read the directory names out of the map's tree block.

    Args:
        repo: The repository root.

    Returns:
        Sorted directory names.
    """
    text = (repo / SKILL).read_text(encoding="utf-8")
    found = {
        line.split()[1].rstrip("/")
        for line in text.splitlines()
        if line.startswith(("├── ", "└── ")) and line.split()[1].endswith("/")
    }
    return sorted(found)


def _modules(repo: Path) -> list[str]:
    """List every maintainer module that carries behaviour.

    Args:
        repo: The repository root.

    Returns:
        Sorted repository-relative paths.
    """
    return [
        rel
        for rel in working_files(repo, "scripts/*.py")
        if not rel.rsplit("/", 1)[-1].startswith("test_")
        and rel.rsplit("/", 1)[-1] not in EXEMPT_MODULES
    ]


def _tests(repo: Path) -> list[str]:
    """List every test module.

    Args:
        repo: The repository root.

    Returns:
        Sorted repository-relative paths.
    """
    return [rel for rel in working_files(repo, "scripts/*.py") if "/test_" in rel]


def test_the_map_names_every_area_on_disk(repo: Path) -> None:
    """An area the map never mentions is a directory Claude does not know it may use."""
    assert [area for area in _areas_on_disk(repo) if area not in _areas_in_map(repo)] == []


def test_the_map_names_no_area_that_is_gone(repo: Path) -> None:
    """A stale area sends the next maintainer script to a directory nobody gates."""
    assert [area for area in _areas_in_map(repo) if area not in _areas_on_disk(repo)] == []


def test_the_tree_block_matches_the_areas(repo: Path) -> None:
    """The tree is the part a reader scans; it drifts first and says nothing."""
    assert _tree_entries(repo) == _areas_on_disk(repo)


def test_governance_map_every_module_has_a_sibling_test(repo: Path) -> None:
    """A module with no test beside it is behaviour that changes unnoticed (P5)."""
    missing = [
        rel
        for rel in _modules(repo)
        if not (repo / rel).with_name(f"test_{Path(rel).name}").is_file()
    ]
    assert missing == [], f"no sibling test for: {missing}"


def test_governance_map_every_test_carries_at_most_one_marker(repo: Path) -> None:
    """Two markers exclude a test from both halves of the gate, so it never runs."""
    offenders: list[str] = []
    for rel in _tests(repo):
        for block in (repo / rel).read_text(encoding="utf-8").split("\ndef "):
            found = {match["marker"] for match in MARKER_LINE.finditer(block)}
            if len(found) > 1:
                offenders.append(f"{rel}: {sorted(found)}")
    assert offenders == [], f"tests carrying more than one marker: {offenders}"


def test_every_marker_used_is_declared(repo: Path) -> None:
    """`--strict-markers` already refuses an undeclared marker; this names the set."""
    used: set[str] = set()
    for rel in _tests(repo):
        used.update(
            match["marker"] for match in MARKER_LINE.finditer((repo / rel).read_text("utf-8"))
        )
    assert used <= set(MARKERS), sorted(used)
