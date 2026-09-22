"""Running this repository's own hooks the way Claude Code runs them.

Every hook reads one JSON payload on standard input and answers on standard output, so a
test is a payload and an expectation. Two things make that worth a shared fixture. The
payloads have a fixed shape, and getting a field name wrong would make a test pass against a
hook that never fires. And macOS ships bash 3.2 at `/bin/bash` while Homebrew's bash is on
`PATH`: a hook that uses a bash 4 feature works for whoever wrote it and fails for the next
person, so every process-spawning test here runs under both.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
from typing import TYPE_CHECKING, Final

import pytest

from scripts.common.jsontext import is_json_object
from scripts.common.plugins import parse_json, repo_root

if TYPE_CHECKING:
    from collections.abc import Mapping

HERE: Final = Path(__file__).resolve().parent
"""This area's directory, so a fixture finds the checkout without using the cwd."""

HOOK_OUTPUT: Final = Path("<hook output>")
"""The label a parse failure names, since a hook's output comes from a pipe, not a file."""

HOOKS_DIR: Final = ".claude/hooks"
"""Where this repository's hooks live."""


def bash_binaries() -> list[str]:
    """Resolve the bash binaries a hook may be run under.

    Returns:
        `bash` from PATH, plus `/bin/bash` when it is a different file.
    """
    found = shutil.which("bash")
    assert found is not None, "bash must be on PATH for the maintainer test suite"
    binaries = [found]
    system = "/bin/bash"
    if Path(system).exists() and Path(system).resolve() != Path(found).resolve():
        binaries.append(system)
    return binaries


BASH_BINARIES: Final[tuple[str, ...]] = tuple(bash_binaries())
"""Parametrised by every process-spawning hook test in this area."""


def payload(**fields: object) -> str:
    """Render a hook input payload.

    Args:
        **fields: The payload's keys, for example `tool_name` and `cwd`.

    Returns:
        The JSON text to write to the hook's standard input.
    """
    return json.dumps(fields)


def bash_payload(command: str, cwd: Path, session_id: str = "test-session") -> str:
    """Render the `PreToolUse` payload Claude Code sends before a Bash command.

    Args:
        command: The command line Claude is about to run.
        cwd: The directory Claude is working in.
        session_id: The session the call belongs to.

    Returns:
        The JSON text.
    """
    return payload(
        tool_name="Bash",
        tool_input={"command": command},
        cwd=str(cwd),
        session_id=session_id,
    )


def edit_payload(file_path: Path, cwd: Path, **extra: object) -> str:
    """Render the payload Claude Code sends around an `Edit` call.

    Args:
        file_path: The file being edited.
        cwd: The directory Claude is working in.
        **extra: Further `tool_input` keys, such as `old_string` and `new_string`.

    Returns:
        The JSON text.
    """
    tool_input: dict[str, object] = {"file_path": str(file_path), **extra}
    return payload(tool_name="Edit", tool_input=tool_input, cwd=str(cwd), session_id="test-session")


SESSION_ONLY_VARIABLES: Final[frozenset[str]] = frozenset({"CLAUDE_PROJECT_DIR"})
"""What Claude Code exports to its own hooks; a test inheriting it would aim a hook at this
checkout instead of the scratch repository, so the suite passes in a shell and fails in a
session (measured 2026-09-22 when the checklist gate ran `make test-slow` from a Stop hook)."""


def ambient_env() -> dict[str, str]:
    """This process's environment without the variables a Claude Code session sets.

    Returns:
        A copy the caller may extend.
    """
    return {key: value for key, value in os.environ.items() if key not in SESSION_ONLY_VARIABLES}


def run_hook(
    script: Path,
    text: str,
    *,
    binary: str,
    cwd: Path,
    env: Mapping[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run one hook with a payload on standard input.

    Args:
        script: The hook to run.
        text: The payload.
        binary: The bash binary to run it under.
        cwd: The working directory, which is what a hook falls back to.
        env: The environment; `ambient_env()` when None.

    Returns:
        The completed process, with both streams as text.
    """
    return subprocess.run(
        [binary, str(script)],
        executable=binary,
        input=text,
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
        env=ambient_env() if env is None else dict(env),
    )


def hook_output(text: str) -> Mapping[str, object]:
    """Parse what a hook printed, as untyped data the caller narrows.

    Args:
        text: The hook's standard output.

    Returns:
        The parsed object.
    """
    parsed = parse_json(text, path=HOOK_OUTPUT)
    assert is_json_object(parsed), text
    return parsed


def decision(completed: subprocess.CompletedProcess[str]) -> Mapping[str, object] | None:
    """Read a `PreToolUse` decision out of a hook's output.

    Args:
        completed: What the hook printed.

    Returns:
        The `hookSpecificOutput` object, or None when the hook allowed the call silently.
    """
    if not completed.stdout.strip():
        return None
    specific = hook_output(completed.stdout).get("hookSpecificOutput")
    assert is_json_object(specific), completed.stdout
    return specific


def reason(completed: subprocess.CompletedProcess[str]) -> str:
    """Read the text a denying hook showed Claude.

    Args:
        completed: What the hook printed.

    Returns:
        The denial's reason.
    """
    specific = decision(completed)
    assert specific is not None, "the hook allowed the call"
    assert specific.get("permissionDecision") == "deny", specific
    text = specific.get("permissionDecisionReason")
    assert isinstance(text, str), specific
    return text


def git_in(root: Path, *args: str) -> str:
    """Run git in a temporary repository.

    Args:
        root: The repository root.
        *args: The arguments after the binary.

    Returns:
        Standard output.
    """
    executable = shutil.which("git")
    assert executable is not None, "git must be on PATH for the maintainer test suite"
    completed = subprocess.run(
        ["/usr/bin/git", *args],
        executable=executable,
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout


def commit_all(root: Path, message: str) -> str:
    """Stage everything and commit it.

    Args:
        root: The repository root.
        message: The commit message.

    Returns:
        The new commit's sha.
    """
    _ = git_in(root, "add", "--all")
    _ = git_in(
        root,
        "-c",
        "user.email=test@example.test",
        "-c",
        "user.name=Test",
        "commit",
        "--quiet",
        "--message",
        message,
    )
    return git_in(root, "rev-parse", "HEAD").strip()


@pytest.fixture
def scratch_repo(tmp_path: Path) -> Path:
    """Build a git working tree with one commit and no project environment.

    Args:
        tmp_path: pytest's per-test temporary directory.

    Returns:
        The repository root.
    """
    _ = git_in(tmp_path, "init", "--quiet", "--initial-branch=main")
    _ = (tmp_path / "README.md").write_text("# scratch\n", encoding="utf-8")
    _ = commit_all(tmp_path, "initial")
    return tmp_path


@pytest.fixture
def repo() -> Path:
    """Locate this checkout, for the tests that read the real harness.

    Returns:
        The repository root.
    """
    return repo_root(HERE)


@pytest.fixture
def hooks(repo: Path) -> Path:
    """Locate this repository's hooks.

    Args:
        repo: The repository root.

    Returns:
        The hooks directory.
    """
    return repo / HOOKS_DIR
