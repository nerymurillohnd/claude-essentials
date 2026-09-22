"""Tests for the two-trees library: which checkout a hook acts on inside a worktree.

`${CLAUDE_PROJECT_DIR}` keeps pointing at the checkout the session started from while the
payload's `cwd` follows Claude into a worktree. A gate that reads the wrong one inspects a
tree nobody is changing; state written into the wrong one disappears with the worktree. The
two functions exist so each caller states which it means, and this test pins that.
"""

from __future__ import annotations

import os
import subprocess
from typing import TYPE_CHECKING, Final

import pytest

from scripts.harness.conftest import BASH_BINARIES, payload

if TYPE_CHECKING:
    from pathlib import Path

LIBRARY: Final = "lib/repo-root.sh"
"""The library under test; it is sourced, never executed."""

DRIVER: Final = """
set -euo pipefail
# shellcheck source=/dev/null
source "$1"
printf 'session=%s\\n' "$(session_tree "$2")"
printf 'project=%s\\n' "$(project_dir "$2")"
"""
"""Sources the library and prints both answers for one payload."""


def _ask(
    binary: str, library: Path, text: str, *, cwd: Path, project: str | None
) -> dict[str, str]:
    """Run the driver and read back the two paths.

    Args:
        binary: The bash binary to run under.
        library: The library to source.
        text: The hook payload.
        cwd: The working directory.
        project: The value of `CLAUDE_PROJECT_DIR`, or None to unset it.

    Returns:
        The `session` and `project` answers.
    """
    environment = {key: value for key, value in os.environ.items() if key != "CLAUDE_PROJECT_DIR"}
    if project is not None:
        environment["CLAUDE_PROJECT_DIR"] = project
    completed = subprocess.run(
        [binary, "-c", DRIVER, "driver", str(library), text],
        executable=binary,
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )
    assert completed.returncode == 0, completed.stderr
    answers: dict[str, str] = {}
    for line in completed.stdout.splitlines():
        key, separator, value = line.partition("=")
        if separator:
            answers[key] = value
    return answers


@pytest.mark.slow
@pytest.mark.parametrize("binary", BASH_BINARIES)
def test_the_session_tree_follows_claude_into_the_worktree(
    tmp_path: Path, hooks: Path, binary: str
) -> None:
    """A gate must read the tree holding the change, which is the worktree."""
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    project = tmp_path / "checkout"
    project.mkdir()
    answers = _ask(
        binary,
        hooks / LIBRARY,
        payload(cwd=str(worktree)),
        cwd=tmp_path,
        project=str(project),
    )
    assert answers["session"] == str(worktree.resolve())


@pytest.mark.slow
@pytest.mark.parametrize("binary", BASH_BINARIES)
def test_project_state_stays_in_the_checkout_that_outlives_the_worktree(
    tmp_path: Path, hooks: Path, binary: str
) -> None:
    """A subagent's worktree is removed when it finishes; a recorded audit must not go with it."""
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    project = tmp_path / "checkout"
    project.mkdir()
    answers = _ask(
        binary,
        hooks / LIBRARY,
        payload(cwd=str(worktree)),
        cwd=tmp_path,
        project=str(project),
    )
    assert answers["project"] == str(project.resolve())


@pytest.mark.slow
@pytest.mark.parametrize("binary", BASH_BINARIES)
def test_an_unusable_directory_falls_back_rather_than_failing(
    tmp_path: Path, hooks: Path, binary: str
) -> None:
    """Both functions always print a path, so no caller needs an `||` that disables `set -e`."""
    answers = _ask(
        binary,
        hooks / LIBRARY,
        payload(cwd=str(tmp_path / "gone")),
        cwd=tmp_path,
        project=None,
    )
    assert answers["session"] == str(tmp_path.resolve())


@pytest.mark.slow
@pytest.mark.parametrize("binary", BASH_BINARIES)
def test_a_payload_without_a_cwd_uses_the_project_directory(
    tmp_path: Path, hooks: Path, binary: str
) -> None:
    """An event that carries no `cwd` still has to resolve to the session's own checkout."""
    project = tmp_path / "checkout"
    project.mkdir()
    answers = _ask(binary, hooks / LIBRARY, payload(), cwd=tmp_path, project=str(project))
    assert answers["session"] == str(project.resolve())
    assert answers["project"] == str(project.resolve())
