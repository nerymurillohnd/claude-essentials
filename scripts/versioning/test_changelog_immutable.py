"""C2 against this repository: every released section still reads as it did at its tag.

This is the check DEBT-0009 asked for. It runs on the real working tree rather than on a
fixture, because the defect it catches is a maintainer quietly improving the notes of a
version that users already installed.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Final

import pytest

from scripts.common.plugins import git_output, plugin_ids, repo_root
from scripts.versioning.changelog import check_links, check_released_bodies, read_changelog
from scripts.versioning.version_plan import predecessors, read_renames

if TYPE_CHECKING:
    from scripts.common.errors import Finding

C1_DEBT: Final = frozenset(
    {
        "block-no-verify",
        "ruff-quality",
        "shell-quality",
        "verify-completion",
    }
)
"""Plugins whose footer links a later release with `tree/` instead of `compare/`.

Measured 2026-09-21: four, not the three the migration plan predicted. `block-no-verify`
links `0.1.1` correctly with `compare/` and then links `0.1.2` with `tree/`, so the defect is
"the newest release is linked as a snapshot", not "only ever one compare link". The validator
that fails on C1 lands with `validate_plugins`; until the four CHANGELOGs are repaired, this
set records the debt so no fifth plugin can join it.
"""


def _root() -> Path:
    """Return this repository's root, wherever pytest was started from.

    Returns:
        The working tree that contains this test file.
    """
    return repo_root(Path(__file__).resolve().parent)


def _known_tags(root: Path) -> frozenset[str]:
    """List every tag in the repository.

    Args:
        root: The repository root.

    Returns:
        The tag names.
    """
    return frozenset(line.strip() for line in git_output(root, ["tag", "--list"]).splitlines())


@pytest.mark.slow
def test_every_released_section_equals_its_text_at_its_tag() -> None:
    """A tagged version's notes are frozen; corrections go under `## [Unreleased]`."""
    root = _root()
    tags = _known_tags(root)
    renames = read_renames(root)
    findings: list[Finding] = []
    compared: list[str] = []
    for name in plugin_ids(root):
        names = [name, *predecessors(name, renames)]
        relative = f"plugins/{name}/CHANGELOG.md"
        changelog = read_changelog(root / relative)
        compared.extend(
            f"{name} {section.label}"
            for section in changelog.released()
            if any(f"{candidate}--v{section.label}" in tags for candidate in names)
        )
        findings.extend(
            check_released_bodies(
                root,
                changelog,
                path=relative,
                names=names,
                known_tags=tags,
            )
        )
    assert findings == [], [finding.message for finding in findings]
    released_tags = [tag for tag in tags if "--v" in tag]
    assert len(compared) == len(released_tags), f"compared {compared} against {released_tags}"


@pytest.mark.slow
def test_no_plugin_outside_the_recorded_debt_mixes_link_styles() -> None:
    """C1 is not yet a gate, so this keeps the known defect from spreading."""
    root = _root()
    tags = _known_tags(root)
    renames = read_renames(root)
    offenders: set[str] = set()
    for name in plugin_ids(root):
        relative = f"plugins/{name}/CHANGELOG.md"
        findings = check_links(
            read_changelog(root / relative),
            path=relative,
            names=[name, *predecessors(name, renames)],
            known_tags=tags,
        )
        if findings:
            offenders.add(name)
    assert offenders <= set(C1_DEBT), f"new C1 offenders: {sorted(offenders - set(C1_DEBT))}"
