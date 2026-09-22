"""Tests for the harness reader: the wiring it reports, and the state it prunes."""

from __future__ import annotations

import os
import time
from typing import TYPE_CHECKING, Final

import pytest

from scripts.common.errors import ExitCode
from scripts.common.jsontext import canonical_json
from scripts.harness.inventory import (
    CHECKLIST_DIR,
    CHECKLIST_MAX_AGE,
    STAMP_DIR,
    STAMP_MAX_AGE,
    agent_files,
    clean,
    hook_bindings,
    index_entries,
    index_files,
    inventory_lines,
    main,
    rule_paths,
    settings_hooks,
    skill_hooks,
    stale_state,
)

if TYPE_CHECKING:
    from pathlib import Path

    from _pytest.capture import CaptureFixture

INDEX = """# Project

Some prose that is not a table.

| Name | Trigger | Purpose |
| --- | --- | --- |
| `shell.md` | a `.sh` file is read | how shell scripts are written here |
| `python.md` | a `.py` file is read | the lint and type policy |

More prose.
"""
"""A `CLAUDE.md` with one index table, the shape step 10 introduces."""

SETTINGS: Final[dict[str, object]] = {
    "hooks": {
        "PreToolUse": [
            {
                "matcher": "Bash",
                "hooks": [
                    {"type": "command", "command": "$DIR/.claude/hooks/a.sh", "timeout": 5},
                    {"type": "command", "command": "$DIR/.claude/hooks/b.sh"},
                ],
            }
        ],
        "SessionStart": [{"hooks": [{"type": "command", "command": "$DIR/.claude/hooks/c.sh"}]}],
    }
}
"""A settings file with two events, one of them without a matcher."""

SETTINGS_HOOK_COUNT: Final = 3
"""How many handlers the fixture settings file wires."""

SKILL_HOOK_COUNT: Final = 1
"""How many the fixture skill wires; the two sources have to come back together."""

SKILL = """---
name: demo
hooks:
  Stop:
    - hooks:
        - type: command
          command: '"${CLAUDE_PROJECT_DIR}/.claude/hooks/gate.sh"'
---

# Demo
"""
"""A skill that wires its own Stop hook, the way the three delivery skills do."""


def _write(path: Path, text: str) -> None:
    """Create a file and every parent directory it needs.

    Args:
        path: The file to write.
        text: Its contents.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text(text, encoding="utf-8")


def _age(path: Path, seconds: float) -> None:
    """Backdate a file so an age rule can be tested without waiting.

    Args:
        path: The file to backdate.
        seconds: How far back to move it.
    """
    moment = time.time() - seconds
    os.utime(path, (moment, moment))


@pytest.mark.slow
def test_an_index_table_is_read_row_by_row(scratch_repo: Path) -> None:
    """The index is the contract P7 states; reading it is what lets a test compare it to disk."""
    _write(scratch_repo / "CLAUDE.md", INDEX)
    entries = index_entries(scratch_repo)
    assert [entry.name for entry in entries] == ["`shell.md`", "`python.md`"]
    assert entries[0].trigger == "a `.sh` file is read"
    assert entries[0].source == "CLAUDE.md"


@pytest.mark.slow
def test_a_table_that_is_not_an_index_is_ignored(scratch_repo: Path) -> None:
    """Instruction files are full of tables; only the three-column index one counts."""
    _write(scratch_repo / "CLAUDE.md", "| Command | What it does |\n| --- | --- |\n| `a` | b |\n")
    assert index_entries(scratch_repo) == []


@pytest.mark.slow
def test_a_nested_instruction_file_is_read_too(scratch_repo: Path) -> None:
    """Each level names the next, so the nested files are part of the same index."""
    _write(scratch_repo / "scripts" / "CLAUDE.md", INDEX)
    assert index_files(scratch_repo) == ["scripts/CLAUDE.md"]
    assert {entry.source for entry in index_entries(scratch_repo)} == {"scripts/CLAUDE.md"}


@pytest.mark.slow
def test_every_settings_hook_is_read_with_its_event(scratch_repo: Path) -> None:
    """A hook is wired by an event and a matcher; both have to come back to compare them."""
    _write(scratch_repo / ".claude/settings.json", canonical_json(SETTINGS))
    bindings = settings_hooks(scratch_repo)
    assert [binding.event for binding in bindings] == ["PreToolUse", "PreToolUse", "SessionStart"]
    assert bindings[0].matcher == "Bash"
    assert bindings[2].matcher is None


@pytest.mark.slow
def test_a_settings_file_without_hooks_is_not_an_error(scratch_repo: Path) -> None:
    """A checkout may legitimately wire nothing; that is an empty answer, not a failure."""
    _write(scratch_repo / ".claude/settings.json", canonical_json({"env": {}}))
    assert settings_hooks(scratch_repo) == []


@pytest.mark.slow
def test_a_skill_wires_its_own_hook(scratch_repo: Path) -> None:
    """Three delivery skills register the Stop gate this way; settings.json never names it."""
    _write(scratch_repo / ".claude/skills/demo/SKILL.md", SKILL)
    bindings = skill_hooks(scratch_repo)
    assert len(bindings) == 1
    assert bindings[0].event == "Stop"
    assert bindings[0].source == ".claude/skills/demo/SKILL.md"
    assert "gate.sh" in bindings[0].command


@pytest.mark.slow
def test_both_wiring_sources_come_back_together(scratch_repo: Path) -> None:
    """A wiring check has to see every wire, wherever it was declared."""
    _write(scratch_repo / ".claude/settings.json", canonical_json(SETTINGS))
    _write(scratch_repo / ".claude/skills/demo/SKILL.md", SKILL)
    assert len(hook_bindings(scratch_repo)) == SETTINGS_HOOK_COUNT + SKILL_HOOK_COUNT


@pytest.mark.slow
def test_a_rule_reports_the_paths_it_loads_with(scratch_repo: Path) -> None:
    """A rule with `paths:` loads only beside those files; one without loads every session."""
    _write(scratch_repo / ".claude/rules/shell.md", '---\npaths:\n  - "**/*.sh"\n---\n\n# Shell\n')
    _write(scratch_repo / ".claude/rules/always.md", "# Always\n")
    assert rule_paths(scratch_repo) == {
        ".claude/rules/always.md": [],
        ".claude/rules/shell.md": ["**/*.sh"],
    }


@pytest.mark.slow
def test_the_subagents_are_listed(scratch_repo: Path) -> None:
    """A subagent is loaded at launch; the index has to be able to compare against disk."""
    _write(scratch_repo / ".claude/agents/auditor.md", "---\nname: auditor\n---\n\nAudit.\n")
    assert agent_files(scratch_repo) == [".claude/agents/auditor.md"]


@pytest.mark.slow
def test_an_old_stamp_is_stale_and_a_fresh_one_is_not(scratch_repo: Path) -> None:
    """One file per session accumulates for the life of the checkout unless something prunes."""
    old = scratch_repo / STAMP_DIR / "bash-stamp-old"
    fresh = scratch_repo / STAMP_DIR / "bash-stamp-new"
    _write(old, "")
    _write(fresh, "")
    _age(old, STAMP_MAX_AGE + 60)
    assert stale_state(scratch_repo) == [f"{STAMP_DIR}/bash-stamp-old"]


@pytest.mark.slow
def test_an_abandoned_checklist_is_stale_after_a_month(scratch_repo: Path) -> None:
    """A checklist untouched that long is from a run nobody is going to finish."""
    path = scratch_repo / CHECKLIST_DIR / "demo--x.json"
    _write(path, "{}\n")
    _age(path, CHECKLIST_MAX_AGE + 60)
    assert stale_state(scratch_repo) == [f"{CHECKLIST_DIR}/demo--x.json"]


@pytest.mark.slow
def test_clean_reports_before_it_deletes(scratch_repo: Path) -> None:
    """A writer that deletes on a dry run would be the one thing nobody could undo."""
    path = scratch_repo / STAMP_DIR / "bash-stamp-old"
    _write(path, "")
    _age(path, STAMP_MAX_AGE + 60)
    assert clean(scratch_repo) == [f"{STAMP_DIR}/bash-stamp-old"]
    assert path.is_file()
    assert clean(scratch_repo, apply=True) == [f"{STAMP_DIR}/bash-stamp-old"]
    assert not path.exists()


@pytest.mark.slow
def test_the_inventory_renders_one_line_per_fact(scratch_repo: Path) -> None:
    """The output is what a maintainer reads when asking what this harness actually loads."""
    _write(scratch_repo / ".claude/settings.json", canonical_json(SETTINGS))
    _write(scratch_repo / ".claude/agents/auditor.md", "---\nname: auditor\n---\n\nAudit.\n")
    lines = inventory_lines(scratch_repo)
    assert sum(line.startswith("hook") for line in lines) == SETTINGS_HOOK_COUNT
    assert sum(line.startswith("agent") for line in lines) == 1


@pytest.mark.slow
def test_the_entrypoint_reports_and_cleans(scratch_repo: Path, capsys: CaptureFixture[str]) -> None:
    """`make clean` is this entrypoint; it has to say what it removed."""
    _write(scratch_repo / ".claude/settings.json", canonical_json(SETTINGS))
    path = scratch_repo / STAMP_DIR / "bash-stamp-old"
    _write(path, "")
    _age(path, STAMP_MAX_AGE + 60)
    assert main(["--root", str(scratch_repo), "--clean", "--apply"]) == int(ExitCode.OK)
    assert "removed" in capsys.readouterr().out
    assert not path.exists()


def test_a_tree_without_a_harness_is_a_usage_error(
    tmp_path: Path, capsys: CaptureFixture[str]
) -> None:
    """One `error:` line, never a traceback, is the entrypoint convention."""
    assert main(["--root", str(tmp_path)]) == int(ExitCode.USAGE)
    assert capsys.readouterr().err.startswith("error: ")
