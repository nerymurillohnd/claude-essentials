"""Tests for the audit recorder: `/pr-delivery` trusts this file instead of a hand-written note.

The record is what lets the delivery checklist verify that `repo-auditor` passed on the exact
head being shipped. Two things therefore have to hold: a verdict is recorded only when the
report carries both lines, and never when the tree is dirty, because then the audited content
is not what the commit holds.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Final

import pytest

from scripts.common.errors import ExitCode
from scripts.common.plugins import load_json
from scripts.harness.conftest import BASH_BINARIES, payload, run_hook

if TYPE_CHECKING:
    from pathlib import Path

HOOK: Final = "record-audit.sh"
"""The hook under test."""

AUDITS: Final = ".claude/state/audits"
"""Where a verdict is recorded, in the checkout that outlives any worktree."""

SHA: Final = "0123456789abcdef0123456789abcdef01234567"
"""A head the fixture reports on; the hook only ever treats it as text."""


def _report(verdict: str, sha: str = SHA) -> str:
    """Render a `repo-auditor` final message.

    Args:
        verdict: PASS or FAIL.
        sha: The head the auditor claims to have read.

    Returns:
        The message text.
    """
    return f"Audit complete.\nHEAD: {sha}\nVERDICT: {verdict}\n"


def _payload(root: Path, message: str, agent: str = "repo-auditor") -> str:
    """Render the `SubagentStop` payload Claude Code sends.

    Args:
        root: The tree the subagent worked in.
        message: The subagent's final message.
        agent: The subagent type the matcher scopes on.

    Returns:
        The JSON text.
    """
    return payload(agent_type=agent, cwd=str(root), last_assistant_message=message)


def _env(root: Path) -> dict[str, str]:
    """Point project state at a temporary checkout.

    Args:
        root: The checkout the record belongs to.

    Returns:
        This process's environment with `CLAUDE_PROJECT_DIR` set.
    """
    return {**os.environ, "CLAUDE_PROJECT_DIR": str(root)}


@pytest.mark.slow
@pytest.mark.parametrize("binary", BASH_BINARIES)
def test_a_pass_on_a_clean_tree_is_recorded(scratch_repo: Path, hooks: Path, binary: str) -> None:
    """This file is the evidence `/pr-delivery` checks before it calls a change delivered."""
    completed = run_hook(
        hooks / HOOK,
        _payload(scratch_repo, _report("PASS")),
        binary=binary,
        cwd=scratch_repo,
        env=_env(scratch_repo),
    )
    assert completed.returncode == int(ExitCode.OK)
    record = load_json(scratch_repo / AUDITS / f"{SHA}.json")
    assert record == {"head": SHA, "verdict": "PASS"}


@pytest.mark.slow
@pytest.mark.parametrize("binary", BASH_BINARIES)
def test_a_fail_is_recorded_too(scratch_repo: Path, hooks: Path, binary: str) -> None:
    """A recorder that only wrote passes would let a failed audit look like no audit."""
    _ = run_hook(
        hooks / HOOK,
        _payload(scratch_repo, _report("FAIL")),
        binary=binary,
        cwd=scratch_repo,
        env=_env(scratch_repo),
    )
    record = load_json(scratch_repo / AUDITS / f"{SHA}.json")
    assert record == {"head": SHA, "verdict": "FAIL"}


@pytest.mark.slow
@pytest.mark.parametrize("binary", BASH_BINARIES)
def test_a_dirty_tree_records_nothing_and_says_why(
    scratch_repo: Path, hooks: Path, binary: str
) -> None:
    """With uncommitted changes the verdict is not about the commit it names."""
    _ = (scratch_repo / "scratch.txt").write_text("uncommitted\n", encoding="utf-8")
    completed = run_hook(
        hooks / HOOK,
        _payload(scratch_repo, _report("PASS")),
        binary=binary,
        cwd=scratch_repo,
        env=_env(scratch_repo),
    )
    assert not (scratch_repo / AUDITS).exists()
    assert "uncommitted changes" in completed.stdout


@pytest.mark.slow
@pytest.mark.parametrize("binary", BASH_BINARIES)
def test_a_report_without_both_lines_records_nothing(
    scratch_repo: Path, hooks: Path, binary: str
) -> None:
    """A report missing its contract lines is a report nobody can verify."""
    completed = run_hook(
        hooks / HOOK,
        _payload(scratch_repo, "Looks fine to me."),
        binary=binary,
        cwd=scratch_repo,
        env=_env(scratch_repo),
    )
    assert not (scratch_repo / AUDITS).exists()
    assert "no " in completed.stdout


@pytest.mark.slow
@pytest.mark.parametrize("binary", BASH_BINARIES)
def test_another_subagent_is_ignored(scratch_repo: Path, hooks: Path, binary: str) -> None:
    """Every subagent stop reaches this hook; only the auditor's verdict is recorded."""
    completed = run_hook(
        hooks / HOOK,
        _payload(scratch_repo, _report("PASS"), agent="general-purpose"),
        binary=binary,
        cwd=scratch_repo,
        env=_env(scratch_repo),
    )
    assert completed.stdout == ""
    assert not (scratch_repo / AUDITS).exists()
