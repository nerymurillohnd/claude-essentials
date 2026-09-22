"""P7 for hooks: every hook on disk is wired, tested, executable, and every wire resolves.

Three ways a hook silently does nothing, all of them seen in this repository's history: it
sits in `.claude/hooks/` and no settings file or skill frontmatter names it; it is named but
the path does not exist; or it exists and is not executable, so Claude Code cannot run it.
None of the three produces an error anywhere — the hook simply never fires.

The fourth rule is this area's own: a hook without a test is behaviour nobody can change
safely, so the table below is exhaustive in both directions.
"""

from __future__ import annotations

import os
from pathlib import Path
import stat
from typing import TYPE_CHECKING, Final

import pytest

from scripts.common.plugins import git_output_or_none, working_files
from scripts.harness.inventory import hook_bindings

if TYPE_CHECKING:
    from collections.abc import Mapping

HOOKS_DIR: Final = ".claude/hooks"
"""Where this repository's hooks live."""

SHEBANG: Final = "#!/usr/bin/env bash"
"""The one shebang a maintainer hook may carry (§2.1)."""

GIT_MODE: Final = "100755"
"""The mode a tracked hook has to be recorded with, so a fresh clone can run it."""

HOOK_TESTS: Final[Mapping[str, str]] = {
    "bash-stamp.sh": "test_bash_stamp.py",
    "checklist-gate.sh": "test_checklist_gate.py",
    "guard-commit.sh": "test_guard_commit.py",
    "guard-marketplace-catalog.sh": "test_guard_catalog.py",
    "guard-push.sh": "test_push_guard.py",
    "post-edit.sh": "test_post_edit.py",
    "record-audit.sh": "test_record_audit.py",
    "session-start.sh": "test_session_start_smoke.py",
    "lib/checklist.sh": "test_checklist_gate.py",
    "lib/plugin-paths.sh": "test_plugin_paths.py",
    "lib/repo-root.sh": "test_repo_root.py",
}
"""Which test covers which hook. Two hooks may share one test; none may have none."""

SHIM_MARKER: Final = "exec "
"""How one hook hands over to another: a hook reached only through `exec` still counts as wired."""


def _hook_names(repo: Path) -> list[str]:
    """List every hook on disk, `lib/` included.

    Args:
        repo: The repository root.

    Returns:
        Paths relative to the hooks directory, sorted.
    """
    prefix = f"{HOOKS_DIR}/"
    return sorted(
        rel.removeprefix(prefix)
        for rel in working_files(repo, f"{HOOKS_DIR}/*.sh", f"{HOOKS_DIR}/*/*.sh")
    )


def _entry_points(repo: Path) -> list[str]:
    """List the hooks Claude Code invokes directly, which excludes the sourced libraries.

    Args:
        repo: The repository root.

    Returns:
        Hook file names, sorted.
    """
    return [name for name in _hook_names(repo) if "/" not in name]


def _wired(repo: Path) -> set[str]:
    """Collect every hook a settings file or a skill frontmatter reaches.

    A hook named in a wire counts, and so does one the named hook `exec`s: that is how the
    commit guard stays wired while `settings.json` still points at its migration shim.

    Args:
        repo: The repository root.

    Returns:
        Hook file names.
    """
    named = {
        binding.command.rsplit("/", 1)[-1].strip('"').strip("'") for binding in hook_bindings(repo)
    }
    reached = set(named)
    for name in named:
        path = repo / HOOKS_DIR / name
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith(SHIM_MARKER):
                reached.add(line.rsplit("/", 1)[-1].strip('"'))
    return reached


def test_every_hook_is_wired_somewhere(repo: Path) -> None:
    """An unwired hook never fires and never says why."""
    wired = _wired(repo)
    assert [name for name in _entry_points(repo) if name not in wired] == []


def test_every_wire_points_at_a_hook_that_exists(repo: Path) -> None:
    """A wire to a missing path is a hook Claude Code cannot run, reported nowhere."""
    for binding in hook_bindings(repo):
        name = binding.command.rsplit("/", 1)[-1].strip('"').strip("'")
        assert (repo / HOOKS_DIR / name).is_file(), f"{binding.source} names {name}"


def test_the_test_table_covers_exactly_the_hooks_on_disk(repo: Path) -> None:
    """A hook with no test is behaviour nobody can change safely."""
    assert sorted(HOOK_TESTS) == _hook_names(repo)


@pytest.mark.parametrize("test_name", sorted(set(HOOK_TESTS.values())))
def test_every_named_test_exists(test_name: str) -> None:
    """The table is only useful while every file it names is really there."""
    assert (Path(__file__).resolve().parent / test_name).is_file()


def test_every_hook_carries_the_one_allowed_shebang(repo: Path) -> None:
    """A maintainer hook runs under bash, never under an interpreter a user may lack."""
    for name in _hook_names(repo):
        first = (repo / HOOKS_DIR / name).read_text(encoding="utf-8").splitlines()[0]
        assert first == SHEBANG, f"{name} starts with {first!r}"


def test_every_hook_is_executable_on_disk(repo: Path) -> None:
    """Without the bit, Claude Code cannot run the hook and reports nothing."""
    for name in _hook_names(repo):
        assert os.access(repo / HOOKS_DIR / name, os.X_OK), name


def test_every_tracked_hook_is_recorded_as_executable(repo: Path) -> None:
    """The bit has to be in the index too, or a fresh clone gets a hook it cannot run."""
    for name in _hook_names(repo):
        listing = git_output_or_none(repo, ["ls-files", "-s", "--", f"{HOOKS_DIR}/{name}"])
        if not listing or not listing.strip():
            continue
        assert listing.split()[0] == GIT_MODE, listing.strip()


def test_the_hooks_directory_holds_no_stray_executable(repo: Path) -> None:
    """Anything executable in there looks like a hook; it must be one, or it misleads."""
    for path in (repo / HOOKS_DIR).rglob("*"):
        if path.is_file() and bool(path.stat().st_mode & stat.S_IXUSR):
            assert path.suffix == ".sh", path
