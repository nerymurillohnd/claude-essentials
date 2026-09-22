"""Tests for the push guard: the two pushes that must never happen.

**A push that recreates a merged branch.** GitHub deletes the branch when its PR merges; a
later `git push` puts it back with commits `main` never receives, and nothing says so.

**A direct push to `main` that changes a plugin's runtime.** The maintainer bypasses the
required checks to push docs straight to `main` (ADR-0003). A behaviour change must not take
that route, because then `version-check` and the tag workflow never run.

The two commands the guard runs are seams: the tests replace them, Claude's command line
cannot. They are replaced rather than really run because a fixture repository has no
`Makefile` and no plugins; what the real command prints is pinned where it is produced, by
the versioning area's golden test for `Computed label: bump: none`.
"""

from __future__ import annotations

import shlex
from typing import TYPE_CHECKING, Final

import pytest

from scripts.common.errors import ExitCode
from scripts.harness.conftest import (
    BASH_BINARIES,
    ambient_env,
    bash_payload,
    commit_all,
    git_in,
    run_hook,
)
from scripts.versioning.check_versions import LABEL_PREFIX

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

HOOK: Final = "guard-push.sh"
"""The hook under test."""

EXEMPT_OUTPUT: Final[tuple[str, ...]] = ("alpha 0.1.0 exempt", f"{LABEL_PREFIX}bump: none")
"""What `make -s versions` prints when only exempt files changed."""

RUNTIME_OUTPUT: Final[tuple[str, ...]] = ("alpha 0.1.0 runtime", f"{LABEL_PREFIX}bump: patch")
"""What it prints when a plugin's runtime changed, which `main` may not receive directly."""


def _env(lines: Sequence[str]) -> dict[str, str]:
    """Replace the two commands the guard runs.

    Args:
        lines: What the version check should print, one entry per line.

    Returns:
        This process's environment with both seams set.
    """
    quoted = " ".join(shlex.quote(line) for line in lines)
    return {
        **ambient_env(),
        "GUARD_PUSH_VERSIONS_CMD": f"printf '%s\\n' {quoted}",
        "GUARD_PUSH_CHECK_CMD": "true",
    }


@pytest.fixture
def clone(tmp_path: Path) -> Path:
    """Build a bare origin and a clone of it whose `main` tracks the remote.

    Args:
        tmp_path: pytest's per-test temporary directory.

    Returns:
        The clone's root.
    """
    origin = tmp_path / "origin.git"
    source = tmp_path / "source"
    _ = git_in(tmp_path, "init", "--quiet", "--initial-branch=main", str(source))
    _ = (source / "README.md").write_text("# fixture\n", encoding="utf-8")
    _ = commit_all(source, "initial")
    _ = git_in(tmp_path, "clone", "--quiet", "--bare", str(source), str(origin))
    work = tmp_path / "work"
    _ = git_in(tmp_path, "clone", "--quiet", str(origin), str(work))
    return work


@pytest.mark.slow
@pytest.mark.parametrize("binary", BASH_BINARIES)
def test_an_exempt_only_push_to_main_is_allowed(clone: Path, hooks: Path, binary: str) -> None:
    """The direct route exists for changes users never receive: docs, tooling, root files."""
    completed = run_hook(
        hooks / HOOK,
        bash_payload("git push origin main", clone),
        binary=binary,
        cwd=clone,
        env=_env(EXEMPT_OUTPUT),
    )
    assert completed.stdout == ""
    assert completed.returncode == int(ExitCode.OK)


@pytest.mark.slow
@pytest.mark.parametrize("binary", BASH_BINARIES)
def test_a_runtime_push_to_main_is_denied(clone: Path, hooks: Path, binary: str) -> None:
    """A behaviour change on the direct route skips `version-check` and the tag workflow."""
    completed = run_hook(
        hooks / HOOK,
        bash_payload("git push origin main", clone),
        binary=binary,
        cwd=clone,
        env=_env(RUNTIME_OUTPUT),
    )
    assert "pull request" in completed.stdout
    assert "bump: patch" in completed.stdout


@pytest.mark.slow
@pytest.mark.parametrize("binary", BASH_BINARIES)
def test_a_dirty_tree_is_refused_before_anything_runs(
    clone: Path, hooks: Path, binary: str
) -> None:
    """With uncommitted changes the local checks would not test what is being pushed."""
    _ = (clone / "scratch.txt").write_text("uncommitted\n", encoding="utf-8")
    completed = run_hook(
        hooks / HOOK,
        bash_payload("git push origin main", clone),
        binary=binary,
        cwd=clone,
        env=_env(EXEMPT_OUTPUT),
    )
    assert "uncommitted changes" in completed.stdout


@pytest.mark.slow
@pytest.mark.parametrize("binary", BASH_BINARIES)
def test_a_push_to_a_new_feature_branch_is_allowed(clone: Path, hooks: Path, binary: str) -> None:
    """Feature branches are the ordinary route; the guard is only about the two exceptions."""
    _ = git_in(clone, "switch", "--quiet", "--create", "feature/x")
    completed = run_hook(
        hooks / HOOK,
        bash_payload("git push origin feature/x", clone),
        binary=binary,
        cwd=clone,
        env=_env(RUNTIME_OUTPUT),
    )
    assert completed.stdout == ""
    assert completed.returncode == int(ExitCode.OK)


@pytest.mark.slow
@pytest.mark.parametrize("binary", BASH_BINARIES)
def test_a_merged_and_deleted_branch_is_denied(clone: Path, hooks: Path, binary: str) -> None:
    """The branch was published, the remote no longer has it: almost always a merged PR."""
    _ = git_in(clone, "switch", "--quiet", "--create", "feature/merged")
    _ = git_in(clone, "push", "--quiet", "--set-upstream", "origin", "feature/merged")
    _ = git_in(clone, "push", "--quiet", "origin", "--delete", "feature/merged")
    completed = run_hook(
        hooks / HOOK,
        bash_payload("git push origin feature/merged", clone),
        binary=binary,
        cwd=clone,
        env=_env(EXEMPT_OUTPUT),
    )
    assert "no longer exists on the remote" in completed.stdout


@pytest.mark.slow
@pytest.mark.parametrize("binary", BASH_BINARIES)
def test_a_command_that_is_not_a_push_is_ignored(clone: Path, hooks: Path, binary: str) -> None:
    """Every Bash call reaches this hook; only a push may pay for a remote lookup."""
    completed = run_hook(
        hooks / HOOK,
        bash_payload("git status", clone),
        binary=binary,
        cwd=clone,
        env=_env(RUNTIME_OUTPUT),
    )
    assert completed.stdout == ""


@pytest.mark.slow
@pytest.mark.parametrize("binary", BASH_BINARIES)
def test_a_tag_push_is_not_a_branch_push(clone: Path, hooks: Path, binary: str) -> None:
    """Tags come from the workflow, and the branch rules have nothing to say about them."""
    completed = run_hook(
        hooks / HOOK,
        bash_payload("git push origin refs/tags/alpha--v0.1.0", clone),
        binary=binary,
        cwd=clone,
        env=_env(RUNTIME_OUTPUT),
    )
    assert completed.stdout == ""
