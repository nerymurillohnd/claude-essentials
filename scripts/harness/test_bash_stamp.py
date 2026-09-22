"""Smoke tests for the Bash stamp: `post-edit.sh` cannot work without it.

A Bash call carries no `file_path`, so the only way `post-edit.sh` can know which files a
shell command changed is to compare them against a mark left when the command started. If
this hook writes nothing, every edit made through a shell command goes unchecked and nothing
says so.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

import pytest

from scripts.common.errors import ExitCode
from scripts.harness.conftest import BASH_BINARIES, bash_payload, run_hook

if TYPE_CHECKING:
    from pathlib import Path

HOOK: Final = "bash-stamp.sh"
"""The hook under test."""

STAMP_DIR: Final = ".claude/.cache/hooks"
"""Where the stamps land, which `make clean` later prunes."""


@pytest.mark.slow
@pytest.mark.parametrize("binary", BASH_BINARIES)
def test_a_stamp_is_written_for_the_session(tmp_path: Path, hooks: Path, binary: str) -> None:
    """The stamp is per session, so two sessions never read each other's edits."""
    completed = run_hook(
        hooks / HOOK,
        bash_payload("echo hi", tmp_path, session_id="abc-123"),
        binary=binary,
        cwd=tmp_path,
    )
    assert completed.returncode == int(ExitCode.OK)
    assert (tmp_path / STAMP_DIR / "bash-stamp-abc-123").is_file()


@pytest.mark.slow
@pytest.mark.parametrize("binary", BASH_BINARIES)
def test_a_session_id_with_separators_is_made_safe(
    tmp_path: Path, hooks: Path, binary: str
) -> None:
    """A session id reaches the hook as data; it must never become a path of its own."""
    _ = run_hook(
        hooks / HOOK,
        bash_payload("echo hi", tmp_path, session_id="a/b c"),
        binary=binary,
        cwd=tmp_path,
    )
    assert (tmp_path / STAMP_DIR / "bash-stamp-a_b_c").is_file()


@pytest.mark.slow
@pytest.mark.parametrize("binary", BASH_BINARIES)
def test_a_payload_without_a_session_writes_nothing(
    tmp_path: Path, hooks: Path, binary: str
) -> None:
    """Without a session there is nothing to key the stamp by, so the hook steps aside."""
    completed = run_hook(hooks / HOOK, '{"tool_name":"Bash"}', binary=binary, cwd=tmp_path)
    assert completed.returncode == int(ExitCode.OK)
    assert not (tmp_path / STAMP_DIR).exists()
