"""Q2: the repository's policy is at least the maintainer's own, never less (P11).

Q1 pins this repository's configuration against a written floor. Q2 pins it against the
machine's: the maintainer's `~/.config/ruff/ruff.toml` and `~/.config/shellcheckrc` apply to
every other project, and a project file replaces them entirely rather than extending them. So
the moment `pyproject.toml` exists, this repository can silently be the *least* strict place
the maintainer works, which is the opposite of what a public marketplace needs.

The comparison needs those files, so it is skipped — with an explicit reason — when they are
not there, which is every CI runner. `scripts.common.environment` decides that, because
`GITHUB_ACTIONS` alone is set in this maintainer's shell profile and would skip the check on
the one machine it exists for.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

import pytest

from scripts.common.environment import in_github_actions
from scripts.hygiene.conftest import (
    PYPROJECT,
    SHELLCHECKRC,
    nested,
    shellcheck_directives,
    string_list,
    toml_document,
)

GLOBAL_RUFF: Final = Path.home() / ".config" / "ruff" / "ruff.toml"
"""The policy every other project of this maintainer's gets."""

GLOBAL_SHELLCHECKRC: Final = Path.home() / ".config" / "shellcheckrc"
"""The same, for shell."""

THRESHOLDS: Final[tuple[tuple[str, ...], ...]] = (
    ("lint", "mccabe", "max-complexity"),
    ("line-length",),
)
"""Numeric settings where the repository may only be stricter, never looser."""

FORMAT_KEYS: Final[tuple[str, ...]] = (
    "quote-style",
    "indent-style",
    "skip-magic-trailing-comma",
    "line-ending",
    "docstring-code-format",
    "docstring-code-line-length",
)
"""The formatter settings; a difference here is a reformat of every file on the next save."""


def _skip_without(path: Path) -> None:
    """Skip with a reason when the machine-level policy is not present.

    Args:
        path: The file the comparison needs.
    """
    if in_github_actions():
        pytest.skip(f"{path} is a maintainer-machine file; CI has no user-level policy")
    if not path.is_file():
        pytest.skip(f"{path} is absent, so there is no machine-level policy to compare against")


def _global_lint(key: str) -> list[str]:
    """Read a list out of the global Ruff policy's `[lint]` table.

    Args:
        key: `select` or `ignore`.

    Returns:
        The strings it holds.
    """
    return string_list(nested(toml_document(GLOBAL_RUFF), "lint", key))


def _repo_lint(repo: Path, key: str) -> list[str]:
    """Read the same list out of this repository's policy.

    Args:
        repo: The repository root.
        key: `select` or `ignore`.

    Returns:
        The strings it holds.
    """
    return string_list(nested(toml_document(repo / PYPROJECT), "tool", "ruff", "lint", key))


def test_every_family_the_machine_selects_is_selected_here(repo: Path) -> None:
    """A family missing here is a class of finding that fires everywhere except this repository."""
    _skip_without(GLOBAL_RUFF)
    missing = [
        family for family in _global_lint("select") if family not in _repo_lint(repo, "select")
    ]
    assert missing == [], f"selected globally but not here: {missing}"


def test_this_repository_ignores_nothing_extra(repo: Path) -> None:
    """An ignore that exists only here is a rule this project alone turned off."""
    _skip_without(GLOBAL_RUFF)
    extra = [rule for rule in _repo_lint(repo, "ignore") if rule not in _global_lint("ignore")]
    assert extra == [], f"ignored here but not globally: {extra}"


@pytest.mark.parametrize("keys", THRESHOLDS)
def test_no_threshold_is_looser_than_the_machine_s(repo: Path, keys: tuple[str, ...]) -> None:
    """A raised ceiling in one project is exactly how a floor stops being a floor."""
    _skip_without(GLOBAL_RUFF)
    machine = nested(toml_document(GLOBAL_RUFF), *keys)
    here = nested(toml_document(repo / PYPROJECT), "tool", "ruff", *keys)
    assert isinstance(machine, int)
    assert isinstance(here, int)
    assert here <= machine, f"{'.'.join(keys)}: {here} > {machine}"


@pytest.mark.parametrize("key", FORMAT_KEYS)
def test_the_formatter_settings_are_identical(repo: Path, key: str) -> None:
    """A different formatter setting rewrites every file the first time either tool runs."""
    _skip_without(GLOBAL_RUFF)
    assert nested(toml_document(repo / PYPROJECT), "tool", "ruff", "format", key) == nested(
        toml_document(GLOBAL_RUFF), "format", key
    )


def test_every_shellcheck_check_the_machine_enables_is_enabled_here(repo: Path) -> None:
    """The optional checks are off by default, so dropping one is invisible."""
    _skip_without(GLOBAL_SHELLCHECKRC)
    machine = {
        line
        for line in shellcheck_directives(GLOBAL_SHELLCHECKRC.read_text(encoding="utf-8"))
        if line.startswith("enable=")
    }
    here = set(shellcheck_directives((repo / SHELLCHECKRC).read_text(encoding="utf-8")))
    assert sorted(machine - here) == []
