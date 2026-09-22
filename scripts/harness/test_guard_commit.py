"""Tests for the commit guard: it allows a clean commit and fails closed on everything else.

The guard is what makes `make lint-staged` unavoidable, so the cases that matter are the
three ways it must refuse — a failing check, an unreadable tree, a missing environment — and
the one way it must stay silent. The migration shim is exercised through the same cases,
because `.claude/settings.json` still names the shim's path until step 8.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Final

import pytest

from scripts.common.errors import ExitCode
from scripts.harness.conftest import BASH_BINARIES, bash_payload, decision, reason, run_hook

if TYPE_CHECKING:
    from pathlib import Path

GUARD: Final = "guard-commit.sh"
"""The hook under test."""

SCRIPTS: Final[tuple[str, ...]] = (GUARD,)
"""The entry point `.claude/settings.json` wires; the step-8 shim was removed at step 9."""

COMMIT: Final = "git commit -m 'a change'"
"""The command the guard exists to check."""

PASSING: Final = "true"
"""A stand-in gate that reports nothing."""

FAILING: Final = "echo bad; exit 1"
"""A stand-in gate that fails the way `make lint-staged` fails."""


def _env(lint_cmd: str) -> dict[str, str]:
    """Build an environment that replaces the gate command.

    Args:
        lint_cmd: What the guard should run instead of `make -s lint-staged`.

    Returns:
        This process's environment with the seam set.
    """
    return {**os.environ, "GUARD_COMMIT_LINT_CMD": lint_cmd}


@pytest.mark.slow
@pytest.mark.parametrize("binary", BASH_BINARIES)
@pytest.mark.parametrize("script", SCRIPTS)
def test_a_passing_gate_says_nothing(repo: Path, hooks: Path, binary: str, script: str) -> None:
    """Silence and exit 0 are what let an ordinary commit through without noise."""
    completed = run_hook(
        hooks / script, bash_payload(COMMIT, repo), binary=binary, cwd=repo, env=_env(PASSING)
    )
    assert completed.stdout == ""
    assert completed.returncode == int(ExitCode.OK)


@pytest.mark.slow
@pytest.mark.parametrize("binary", BASH_BINARIES)
@pytest.mark.parametrize("script", SCRIPTS)
def test_a_failing_gate_denies_and_shows_the_output(
    repo: Path, hooks: Path, binary: str, script: str
) -> None:
    """A denial with no output would send the maintainer back to the terminal to guess."""
    completed = run_hook(
        hooks / script, bash_payload(COMMIT, repo), binary=binary, cwd=repo, env=_env(FAILING)
    )
    text = reason(completed)
    assert "make lint-staged" in text
    assert "bad" in text
    assert completed.returncode == int(ExitCode.OK)


@pytest.mark.slow
@pytest.mark.parametrize("binary", BASH_BINARIES)
@pytest.mark.parametrize("script", SCRIPTS)
def test_a_missing_environment_names_make_setup(
    scratch_repo: Path, hooks: Path, binary: str, script: str
) -> None:
    """Without `.venv` the gate cannot run, so the guard refuses and says how to fix it."""
    completed = run_hook(
        hooks / script,
        bash_payload(COMMIT, scratch_repo),
        binary=binary,
        cwd=scratch_repo,
        env=_env(PASSING),
    )
    assert "make setup" in reason(completed)


@pytest.mark.slow
@pytest.mark.parametrize("binary", BASH_BINARIES)
@pytest.mark.parametrize("script", SCRIPTS)
def test_a_command_that_is_not_a_commit_is_ignored(
    repo: Path, hooks: Path, binary: str, script: str
) -> None:
    """Every Bash call passes through this hook; only `git commit` may pay for the gate."""
    completed = run_hook(
        hooks / script,
        bash_payload("ls -la", repo),
        binary=binary,
        cwd=repo,
        env=_env(FAILING),
    )
    assert completed.stdout == ""
    assert completed.returncode == int(ExitCode.OK)


@pytest.mark.slow
@pytest.mark.parametrize("binary", BASH_BINARIES)
def test_a_chained_commit_is_still_a_commit(repo: Path, hooks: Path, binary: str) -> None:
    """`git add … && git commit` is how a commit is actually made here."""
    completed = run_hook(
        hooks / GUARD,
        bash_payload("git add -A && git -C . commit -m x", repo),
        binary=binary,
        cwd=repo,
        env=_env(FAILING),
    )
    assert decision(completed) is not None


@pytest.mark.slow
@pytest.mark.parametrize("binary", BASH_BINARIES)
def test_a_directory_that_is_not_a_working_tree_is_refused(
    tmp_path: Path, hooks: Path, binary: str
) -> None:
    """An unreadable git state must never wave a commit through unchecked."""
    (tmp_path / ".venv" / "bin").mkdir(parents=True)
    interpreter = tmp_path / ".venv" / "bin" / "python"
    _ = interpreter.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    interpreter.chmod(0o755)
    completed = run_hook(
        hooks / GUARD,
        bash_payload(COMMIT, tmp_path),
        binary=binary,
        cwd=tmp_path,
        env=_env(PASSING),
    )
    assert "not a git working tree" in reason(completed)
