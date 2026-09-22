"""Smoke test for the session snapshot: it answers, and it answers in the documented shape.

This hook is the first thing that runs in a session and the only place the maintainer learns
that the environment is wrong before working in it. Its contents change with the toolchain
(step 8 replaces the Node lines with the Python ones), so what is pinned here is the contract
rather than the wording: exit 0, valid JSON, and an `additionalContext` a session can load.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

import pytest

from scripts.common.errors import ExitCode
from scripts.common.jsontext import is_json_object
from scripts.harness.conftest import BASH_BINARIES, hook_output, payload, run_hook

if TYPE_CHECKING:
    from pathlib import Path

HOOK: Final = "session-start.sh"
"""The hook under test."""

EVENT: Final = "SessionStart"
"""The event name the payload has to carry back."""


def _context(stdout: str) -> str:
    """Read the text the hook loads into the session.

    Args:
        stdout: What the hook printed.

    Returns:
        The `additionalContext` string.
    """
    specific = hook_output(stdout).get("hookSpecificOutput")
    assert is_json_object(specific), stdout
    assert specific.get("hookEventName") == EVENT, specific
    text = specific.get("additionalContext")
    assert isinstance(text, str), specific
    return text


@pytest.mark.slow
@pytest.mark.parametrize("binary", BASH_BINARIES)
def test_a_startup_produces_a_snapshot(repo: Path, hooks: Path, binary: str) -> None:
    """A hook that fails at startup would take the whole session's first turn with it."""
    completed = run_hook(
        hooks / HOOK, payload(source="startup", cwd=str(repo)), binary=binary, cwd=repo
    )
    assert completed.returncode == int(ExitCode.OK)
    context = _context(completed.stdout)
    assert context.strip()
    assert "Git" in context


@pytest.mark.slow
@pytest.mark.parametrize("binary", BASH_BINARIES)
def test_a_clear_produces_a_snapshot_too(repo: Path, hooks: Path, binary: str) -> None:
    """`settings.json` matches `startup|clear`, so both have to answer."""
    completed = run_hook(
        hooks / HOOK, payload(source="clear", cwd=str(repo)), binary=binary, cwd=repo
    )
    assert completed.returncode == int(ExitCode.OK)
    assert _context(completed.stdout).strip()
