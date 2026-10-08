"""Tests for the svelte-development skill-hint hook.

The hook is a plugin script, so a defect ships to every user: these tests run
the script itself and read the hook registration, with no model call.

Run: scripts/check.py tests
"""

from __future__ import annotations

import fnmatch
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import override
import unittest

import repo

PLUGIN = repo.ROOT / "plugins" / "svelte-development"
SCRIPT = PLUGIN / "hooks" / "skill-hint.sh"
HOOKS = PLUGIN / "hooks" / "hooks.json"
KINDS = ("edit", "docs", "check", "cli", "lsp")


def edit_rules() -> dict[str, list[str]]:
    """The `if` rules of every PreToolUse handler that runs the `edit` hint, by matcher."""
    rules: dict[str, list[str]] = {}
    document = repo.as_dict(repo.load_json(HOOKS)) or {}
    hooks = repo.as_dict(document.get("hooks")) or {}
    for entry in repo.as_list(hooks.get("PreToolUse")) or []:
        group = repo.as_dict(entry) or {}
        matcher = repo.as_str(group.get("matcher")) or ""
        for handler in repo.as_list(group.get("hooks")) or []:
            fields = repo.as_dict(handler) or {}
            command = repo.as_str(fields.get("command")) or ""
            if command.endswith('skill-hint.sh" edit'):
                rules.setdefault(matcher, []).append(repo.as_str(fields.get("if")) or "")
    return rules


class SkillHintTest(unittest.TestCase):
    """Each kind prints one hook JSON note, once per session."""

    tmp: Path = Path()
    project: Path = Path()

    @override
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="svelte-hint-"))
        self.addCleanup(shutil.rmtree, self.tmp)
        self.project = self.tmp / "project"
        self.project.mkdir()
        _ = (self.project / "package.json").write_text('{"devDependencies": {"svelte": "5"}}')

    def run_hint(self, kind: str, session: str = "s1", project: Path | None = None) -> str:
        """Run the hint script as Claude Code would, with its plugin variables."""
        env = {
            "PATH": "/usr/bin:/bin",
            "CLAUDE_PLUGIN_DATA": str(self.tmp / "data"),
            "CLAUDE_CODE_SESSION_ID": session,
            "CLAUDE_PROJECT_DIR": str(project or self.project),
        }
        result = subprocess.run(
            [str(SCRIPT), kind], capture_output=True, text=True, env=env, check=True
        )
        return result.stdout

    def note(self, output: str) -> str:
        """The additionalContext of one PreToolUse hook JSON object."""
        reply = self.tmp / "reply.json"
        _ = reply.write_text(output)
        payload = repo.as_dict(repo.load_json(reply)) or {}
        fields = repo.as_dict(payload.get("hookSpecificOutput")) or {}
        assert fields.get("hookEventName") == "PreToolUse", payload
        text = repo.as_str(fields.get("additionalContext"))
        assert text, payload
        return text

    def test_every_kind_prints_a_note(self) -> None:
        for kind in KINDS:
            with self.subTest(kind=kind):
                assert self.note(self.run_hint(kind)).startswith("svelte-development: ")

    def test_note_is_once_per_session(self) -> None:
        assert self.run_hint("edit") != ""
        assert self.run_hint("edit") == ""
        assert self.run_hint("edit", session="s2") != ""

    def test_edit_note_names_the_skill_and_the_agent_type(self) -> None:
        text = self.note(self.run_hint("edit"))
        assert "svelte-development:svelte-best-practices" in text
        assert "subagent_type svelte-development:svelte-component-editor" in text

    def test_lsp_note_is_silent_outside_a_svelte_project(self) -> None:
        other = self.tmp / "other"
        other.mkdir()
        _ = (other / "package.json").write_text('{"dependencies": {"react": "19"}}')
        assert self.run_hint("lsp", project=other) == ""

    def test_unknown_kind_is_silent(self) -> None:
        assert self.run_hint("nothing") == ""


class EditHintRegistrationTest(unittest.TestCase):
    """Write and Edit each get the two patterns, and they match only Svelte files."""

    def test_write_and_edit_have_their_own_handlers(self) -> None:
        rules = edit_rules()
        assert sorted(rules) == ["Edit", "Write"], rules
        for tool, conditions in rules.items():
            with self.subTest(tool=tool):
                assert conditions == [f"{tool}(*.svelte)", f"{tool}(*.svelte.[tj]s)"], conditions

    def test_patterns_match_svelte_files_only(self) -> None:
        patterns = [rule[rule.index("(") + 1 : -1] for rule in edit_rules()["Write"]]
        for name in ("Hello.svelte", "counter.svelte.ts", "store.svelte.js"):
            with self.subTest(name=name):
                assert any(fnmatch.fnmatchcase(name, p) for p in patterns), name
        for name in ("util.ts", "x.svelte-check", "app.svelte.d.ts", "page.svelte.tsx"):
            with self.subTest(name=name):
                assert not any(fnmatch.fnmatchcase(name, p) for p in patterns), name


if __name__ == "__main__":
    _ = unittest.main()
