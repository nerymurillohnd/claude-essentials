"""Tests for the Stop gate: a skill cannot report a run as finished before it is.

The three skills that deliver work here each register this hook. Its whole purpose is to
refuse the end of a turn while an item is open or its verification fails, so the cases that
matter are: open items block, a failing verification blocks and reopens the item it belongs
to, a question for the user does not block, and another session is never affected.
"""

from __future__ import annotations

import os
import subprocess
from typing import TYPE_CHECKING, Final

import pytest

from scripts.common.errors import ExitCode
from scripts.common.jsontext import canonical_json, is_json_array, is_json_object
from scripts.common.plugins import load_json
from scripts.harness.conftest import BASH_BINARIES, payload, run_hook

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

HOOK: Final = "checklist-gate.sh"
"""The hook under test."""

LIBRARY: Final = "lib/checklist.sh"
"""The state machine the skills drive and the gate reads."""

SESSION: Final = "session-under-test"
"""The session that owns the fixture checklist."""

TEMPLATE_REL: Final = ".claude/skills/demo/checklist.json"
"""Where the committed template lives; verifications are read from it, never from the state."""

SUBJECT: Final = "demo-subject"
"""What the fixture checklist is about; the state file is named after it."""

STATE_REL: Final = f".claude/state/checklists/demo--{SUBJECT}.json"
"""Where `checklist.sh` keeps the run; the gate removes `.active` when it completes."""

BLOCK: Final = 2
"""The exit status that stops the turn and shows stderr to Claude."""


def _template(verify: str) -> dict[str, object]:
    """Build a two-item checklist template.

    Args:
        verify: The command the second item's verification runs.

    Returns:
        The template document.
    """
    return {
        "skill": "demo",
        "items": [
            {"id": "first", "text": "Do the first thing"},
            {"id": "second", "text": "Do the second thing", "verify": verify},
        ],
    }


def _tree(root: Path, verify: str) -> Path:
    """Write the template into a scratch tree.

    Args:
        root: The tree to write into.
        verify: The verification command for the second item.

    Returns:
        The template's path.
    """
    path = root / TEMPLATE_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text(canonical_json(_template(verify)), encoding="utf-8")
    return path


def _env(root: Path) -> dict[str, str]:
    """Point the checklist state at a scratch tree.

    Args:
        root: The tree that holds the template and the state.

    Returns:
        This process's environment with `CLAUDE_PROJECT_DIR` set.
    """
    return {**os.environ, "CLAUDE_PROJECT_DIR": str(root)}


def _checklist(hooks: Path, root: Path, binary: str, *args: str) -> str:
    """Drive the checklist state machine the way a skill does.

    Args:
        hooks: The hooks directory.
        root: The scratch tree.
        binary: The bash binary to run under.
        *args: The subcommand and its arguments.

    Returns:
        Standard output.
    """
    completed = subprocess.run(
        [binary, str(hooks / LIBRARY), *args],
        executable=binary,
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
        env=_env(root),
    )
    return completed.stdout


def _state(root: Path) -> Mapping[str, object]:
    """Read the active checklist's state file.

    Args:
        root: The scratch tree.

    Returns:
        The parsed state.
    """
    path = root / STATE_REL
    document = load_json(path)
    assert is_json_object(document), path
    return document


def _stop(hooks: Path, root: Path, binary: str, session: str = SESSION) -> tuple[int, str]:
    """Send the `Stop` payload and read the verdict.

    Args:
        hooks: The hooks directory.
        root: The scratch tree.
        binary: The bash binary to run under.
        session: The session ending its turn.

    Returns:
        The exit status and what the hook told Claude.
    """
    completed = run_hook(
        hooks / HOOK, payload(session_id=session), binary=binary, cwd=root, env=_env(root)
    )
    return completed.returncode, completed.stderr


@pytest.mark.slow
@pytest.mark.parametrize("binary", BASH_BINARIES)
def test_an_open_item_blocks_the_turn(tmp_path: Path, hooks: Path, binary: str) -> None:
    """The gate exists so a run cannot be reported as finished while work is left."""
    template = _tree(tmp_path, "true")
    _ = _checklist(hooks, tmp_path, binary, "start", str(template), SUBJECT, SESSION)
    status, message = _stop(hooks, tmp_path, binary)
    assert status == BLOCK
    assert "first" in message


@pytest.mark.slow
@pytest.mark.parametrize("binary", BASH_BINARIES)
def test_a_complete_checklist_with_passing_verifications_lets_the_turn_end(
    tmp_path: Path, hooks: Path, binary: str
) -> None:
    """The control: every item done with evidence, every verification green."""
    template = _tree(tmp_path, "true")
    _ = _checklist(hooks, tmp_path, binary, "start", str(template), SUBJECT, SESSION)
    _ = _checklist(hooks, tmp_path, binary, "check", "first", "done it")
    _ = _checklist(hooks, tmp_path, binary, "check", "second", "done that")
    status, _message = _stop(hooks, tmp_path, binary)
    assert status == int(ExitCode.OK)
    assert _state(tmp_path)["status"] == "complete"


@pytest.mark.slow
@pytest.mark.parametrize("binary", BASH_BINARIES)
def test_a_failing_verification_blocks_and_reopens_the_item(
    tmp_path: Path, hooks: Path, binary: str
) -> None:
    """An item marked done whose check fails was not done; the gate says so and reopens it."""
    template = _tree(tmp_path, "echo nope; exit 1")
    _ = _checklist(hooks, tmp_path, binary, "start", str(template), SUBJECT, SESSION)
    _ = _checklist(hooks, tmp_path, binary, "check", "first", "done it")
    _ = _checklist(hooks, tmp_path, binary, "check", "second", "claimed")
    status, message = _stop(hooks, tmp_path, binary)
    assert status == BLOCK
    assert "nope" in message
    items = _state(tmp_path)["items"]
    assert is_json_array(items)
    assert any(item.get("state") == "open" for item in items if is_json_object(item))


@pytest.mark.slow
@pytest.mark.parametrize("binary", BASH_BINARIES)
def test_an_item_waiting_on_the_user_lets_the_turn_end(
    tmp_path: Path, hooks: Path, binary: str
) -> None:
    """Later items depend on the answer, so the turn has to end for the user to give it."""
    template = _tree(tmp_path, "true")
    _ = _checklist(hooks, tmp_path, binary, "start", str(template), SUBJECT, SESSION)
    _ = _checklist(hooks, tmp_path, binary, "needs-user", "first", "May I merge?")
    status, _message = _stop(hooks, tmp_path, binary)
    assert status == int(ExitCode.OK)


@pytest.mark.slow
@pytest.mark.parametrize("binary", BASH_BINARIES)
def test_another_session_is_never_blocked(tmp_path: Path, hooks: Path, binary: str) -> None:
    """A checklist belongs to the session that started it, not to the checkout."""
    template = _tree(tmp_path, "true")
    _ = _checklist(hooks, tmp_path, binary, "start", str(template), SUBJECT, SESSION)
    status, _message = _stop(hooks, tmp_path, binary, session="another-session")
    assert status == int(ExitCode.OK)


@pytest.mark.slow
@pytest.mark.parametrize("binary", BASH_BINARIES)
def test_no_active_checklist_never_blocks(tmp_path: Path, hooks: Path, binary: str) -> None:
    """Most sessions run no skill at all; the gate must be invisible to them."""
    status, _message = _stop(hooks, tmp_path, binary)
    assert status == int(ExitCode.OK)
