"""Tests for the repository gates.

Each negative test copies the repository to a temporary directory, injects one
defect, and asserts that the gate fails for that reason and no other. The
positive baseline proves the unmodified copy passes, so a failure in a
negative test can only come from the injected defect.

Run: scripts/check.py tests
"""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import tempfile
from typing import override
import unittest

import add_component
import bump_version
import check
import check_commit_msg
import check_docs
import check_pr
import check_repo
import claude_hooks
import drive_plugin
import repo
import validate_adrs

ROOT = repo.ROOT

# The plugin every gate test mutates: a fixture outside the catalog, copied into each
# temporary repository, so the tests do not depend on which plugins the catalog lists.
PLUGIN = "sample-plugin"
PLUGIN_CATEGORY = "development"
FIXTURE_PLUGIN = ROOT / "tests" / "fixtures" / "plugins" / PLUGIN
# A CLAUDE.local.md in the format the clean-room hook reads.
LOCAL_NOTES = """\
- GitHub: `owner/old-repo`, `owner/kept-deprecated`.
- Local: `~/projects/marketplace/kept`.
"""
IGNORED = shutil.ignore_patterns(".git", "__pycache__", ".venv", ".ruff_cache", ".DS_Store")


def make_fixture_dir(case: unittest.TestCase) -> Path:
    """A temporary directory for one test, removed when the test ends (docs/testing.md#cleanup)."""
    tmp = tempfile.TemporaryDirectory(prefix="gate-fixture-")
    location = Path(tmp.name)

    def remove() -> None:
        tmp.cleanup()
        assert not location.exists(), f"fixture {location} was not removed"

    case.addCleanup(remove)
    return location


class RepositoryFixture(unittest.TestCase):
    """A fresh copy of the repository for every test."""

    root: Path = ROOT

    @override
    def setUp(self) -> None:
        self.root = make_fixture_dir(self) / "repo"
        _ = shutil.copytree(ROOT, self.root, ignore=IGNORED, symlinks=True)
        self.install_fixture_plugin()

    @property
    def plugin(self) -> Path:
        return self.root / "plugins" / PLUGIN

    @property
    def marketplace(self) -> Path:
        return self.root / ".claude-plugin" / "marketplace.json"

    def install_fixture_plugin(self) -> None:
        """Add the fixture plugin to the copy: directory, catalog entry, label and labeler rules."""
        _ = shutil.copytree(FIXTURE_PLUGIN, self.plugin, symlinks=True)
        entry: dict[str, repo.JSON] = {
            "name": PLUGIN,
            "source": f"./plugins/{PLUGIN}",
            "description": "Fixture plugin used only by the gate tests.",
            "category": PLUGIN_CATEGORY,
            "tags": ["example"],
        }
        data = repo.as_dict(repo.load_json(self.marketplace)) or {}
        data["plugins"] = [*(repo.as_list(data.get("plugins")) or []), entry]
        _ = self.marketplace.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

        github = self.root / ".github"
        labels = github / "labels.yml"
        text = labels.read_text(encoding="utf-8").rstrip("\n")
        label = f'- name: "plugin:{PLUGIN}"\n  color: "c5def5"\n  description: "Fixture plugin"\n'
        _ = labels.write_text(f"{text}\n{label}", encoding="utf-8")

        labeler = github / "labeler.yml"
        text = labeler.read_text(encoding="utf-8").rstrip("\n") + "\n"
        rule = (
            f"  - changed-files:\n      - any-glob-to-any-file:\n          - plugins/{PLUGIN}/**\n"
        )
        category = f'"category:{PLUGIN_CATEGORY}":\n'
        if category in text:
            text = text.replace(category, category + rule, 1)
        else:
            text += f"\n{category}{rule}"
        _ = labeler.write_text(f'{text}\n"plugin:{PLUGIN}":\n{rule}', encoding="utf-8")

    def errors(self) -> list[str]:
        return check_repo.run_checks(self.root).errors

    def edit_readme(self, old: str, new: str) -> None:
        """Replace the one occurrence of `old` in the fixture plugin's README."""
        readme = self.plugin / "README.md"
        text = readme.read_text(encoding="utf-8")
        assert text.count(old) == 1, old
        _ = readme.write_text(text.replace(old, new), encoding="utf-8")

    def assert_fails_with(self, fragment: str) -> None:
        errors = self.errors()
        assert errors, "the gate passed although a defect was injected"
        assert all(fragment in error for error in errors), (
            f"expected every error to mention {fragment!r}, got: {errors}"
        )

    def edit_json(self, path: Path, key: str, value: repo.JSON) -> None:
        data = repo.as_dict(repo.load_json(path)) or {}
        data[key] = value
        _ = path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    def append(self, path: Path, text: str) -> None:
        with path.open("a", encoding="utf-8") as handle:
            _ = handle.write(text)


class BaselineTest(RepositoryFixture):
    def test_unmodified_repository_passes(self) -> None:
        assert self.errors() == []


class PortabilityGateTest(RepositoryFixture):
    def test_macos_home_path_fails(self) -> None:
        self.append(
            self.plugin / "skills" / "hello" / "SKILL.md",
            "\nRead /Users/someone/notes.md first.\n",
        )
        self.assert_fails_with("macOS home path")

    def test_linux_home_path_fails(self) -> None:
        self.append(
            self.plugin / "skills" / "hello" / "SKILL.md",
            "\nRun /home/someone/bin/tool.\n",
        )
        self.assert_fails_with("Linux home path")

    def test_home_relative_path_fails(self) -> None:
        self.append(self.plugin / "README.md", "\nCopy the file to ~/notes.\n")
        self.assert_fails_with("home-relative path")

    def test_github_token_fails(self) -> None:
        token = "ghp_" + "a1B2c3D4e5" * 4
        self.append(self.plugin / "README.md", f"\nUse the token {token} to log in.\n")
        self.assert_fails_with("GitHub token")

    def test_private_key_fails(self) -> None:
        marker = "-----BEGIN " + "PRIVATE KEY-----"
        self.append(self.plugin / "README.md", f"\n{marker}\n")
        self.assert_fails_with("private key")

    def test_personal_email_fails(self) -> None:
        self.append(self.plugin / "README.md", "\nWrite to someone@personal-mail.io for help.\n")
        self.assert_fails_with("personal email")

    def test_example_email_passes(self) -> None:
        self.append(self.plugin / "README.md", "\nFor example, user@example.com.\n")
        assert self.errors() == []

    def test_unfinished_placeholder_fails(self) -> None:
        self.append(self.plugin / "skills" / "hello" / "SKILL.md", "\nTODO: write the steps.\n")
        self.assert_fails_with("unfinished placeholder")


class SelfContainmentGateTest(RepositoryFixture):
    def test_parent_reference_fails(self) -> None:
        self.append(
            self.plugin / "skills" / "hello" / "SKILL.md",
            "\nLoad ../shared/rules.md.\n",
        )
        self.assert_fails_with('"../" reference')

    def test_symlink_outside_plugin_fails(self) -> None:
        (self.plugin / "shared").symlink_to(self.root / "docs")
        self.assert_fails_with("symlink points outside")

    def test_relative_hook_command_fails(self) -> None:
        hooks = self.plugin / "hooks"
        hooks.mkdir()
        config = {
            "hooks": {
                "PostToolUse": [{"hooks": [{"type": "command", "command": "./scripts/format.sh"}]}]
            }
        }
        _ = (hooks / "hooks.json").write_text(json.dumps(config), encoding="utf-8")
        errors = self.errors()
        assert any('command path "./scripts/format.sh"' in e for e in errors), errors

    def test_plugin_root_hook_command_passes_self_containment(self) -> None:
        hooks = self.plugin / "hooks"
        hooks.mkdir()
        command = '"${CLAUDE_PLUGIN_ROOT}"/scripts/format.sh'
        config = {"hooks": {"PostToolUse": [{"hooks": [{"type": "command", "command": command}]}]}}
        _ = (hooks / "hooks.json").write_text(json.dumps(config), encoding="utf-8")
        errors = self.errors()
        assert not any("command path" in e for e in errors), errors
        # A hook makes the plugin privileged, so its README must document Permissions.
        assert any(repo.readme_heading("Permissions") in e for e in errors), errors


class CheckRunnerTest(unittest.TestCase):
    def test_missing_tool_fails_the_gate(self) -> None:
        assert check.run_commands([["claude-essentials-no-such-tool"]]) is False

    def test_passing_command_passes(self) -> None:
        assert check.run_commands([["true"]]) is True


class PluginScriptGateTest(RepositoryFixture):
    def write_script(self, text: str, mode: int) -> None:
        scripts = self.plugin / "scripts"
        scripts.mkdir(exist_ok=True)
        script = scripts / "run.sh"
        _ = script.write_text(text, encoding="utf-8")
        script.chmod(mode)

    def write_config(self, name: str, data: repo.JSON) -> None:
        path = self.plugin / name
        path.parent.mkdir(parents=True, exist_ok=True)
        _ = path.write_text(json.dumps(data), encoding="utf-8")

    def assert_interpreter_in_front(self, interpreter: str) -> None:
        errors = self.errors()
        assert any(f"runs a plugin script through {interpreter}" in e for e in errors), errors

    def test_shebang_without_executable_bit_fails(self) -> None:
        self.write_script("#!/usr/bin/env sh\nexit 0\n", 0o644)
        self.assert_fails_with("has a shebang but is not executable")

    def test_executable_without_shebang_fails(self) -> None:
        self.write_script("exit 0\n", 0o755)
        self.assert_fails_with("is executable but has no shebang")

    def test_absolute_interpreter_shebang_fails(self) -> None:
        self.write_script("#!/bin/bash\nexit 0\n", 0o755)
        self.assert_fails_with('must be "#!/usr/bin/env <interpreter>')

    def test_shebang_with_options_fails(self) -> None:
        self.write_script("#!/usr/bin/env -S uv run --script\nexit 0\n", 0o755)
        self.assert_fails_with('must be "#!/usr/bin/env <interpreter>')

    def test_versioned_interpreter_shebang_fails(self) -> None:
        self.write_script("#!/usr/bin/env python3.12\nraise SystemExit(0)\n", 0o755)
        self.assert_fails_with("names a versioned interpreter")

    def test_unversioned_executable_script_passes(self) -> None:
        self.write_script("#!/usr/bin/env sh\nexit 0\n", 0o755)
        assert self.errors() == []

    def test_shell_form_hook_with_interpreter_fails(self) -> None:
        command = 'bash "${CLAUDE_PLUGIN_ROOT}/scripts/run.sh"'
        hook: repo.JSON = {"hooks": [{"type": "command", "command": command}]}
        self.write_config("hooks/hooks.json", {"hooks": {"PostToolUse": [hook]}})
        self.assert_interpreter_in_front("bash")

    def test_exec_form_hook_with_interpreter_fails(self) -> None:
        hook: repo.JSON = {
            "type": "command",
            "command": "python3",
            "args": ["${CLAUDE_PLUGIN_ROOT}/x.py"],
        }
        self.write_config("hooks/hooks.json", {"hooks": {"Stop": [{"hooks": [hook]}]}})
        self.assert_interpreter_in_front("python3")

    def test_mcp_server_with_interpreter_fails(self) -> None:
        server: repo.JSON = {"command": "node", "args": ["${CLAUDE_PLUGIN_ROOT}/server.js"]}
        self.write_config(".mcp.json", {"mcpServers": {"local": server}})
        self.assert_interpreter_in_front("node")

    def test_lsp_server_with_interpreter_fails(self) -> None:
        server: repo.JSON = {"command": "sh", "args": ["${CLAUDE_PLUGIN_ROOT}/lsp.sh"]}
        self.write_config(".lsp.json", {"shell": server})
        self.assert_interpreter_in_front("sh")

    def test_monitor_with_interpreter_fails(self) -> None:
        monitor: repo.JSON = {"name": "watch", "command": 'zsh "${CLAUDE_PLUGIN_ROOT}/watch.sh"'}
        self.write_config("monitors/monitors.json", [monitor])
        self.assert_interpreter_in_front("zsh")

    def test_script_by_path_and_user_tools_pass(self) -> None:
        self.write_script("#!/usr/bin/env sh\nexit 0\n", 0o755)
        command = '"${CLAUDE_PLUGIN_ROOT}/scripts/run.sh"'
        hook: repo.JSON = {"hooks": [{"type": "command", "command": command}]}
        self.write_config("hooks/hooks.json", {"hooks": {"PostToolUse": [hook]}})
        self.write_config(".mcp.json", {"mcpServers": {"tool": {"command": "npx", "args": ["x"]}}})
        errors = self.errors()
        assert not any("plugin script" in e or "shebang" in e for e in errors), errors
        # Hooks and MCP servers make the plugin privileged, so only Permissions is missing.
        assert errors, "the privileged plugin passed without a Permissions section"
        assert all(repo.readme_heading("Permissions") in e for e in errors), errors


class CatalogGateTest(RepositoryFixture):
    def test_missing_disclaimer_fails(self) -> None:
        self.edit_json(self.marketplace, "description", "Community plugins for Claude Code.")
        self.assert_fails_with("not affiliated")

    def set_fixture_entry_field(self, key: str, value: repo.JSON) -> None:
        """Set one field on the fixture plugin's catalog entry."""
        data = repo.as_dict(repo.load_json(self.marketplace)) or {}
        for raw in repo.as_list(data.get("plugins")) or []:
            entry = repo.as_dict(raw) or {}
            if entry.get("name") == PLUGIN:
                entry[key] = value
        _ = self.marketplace.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def test_version_in_entry_fails(self) -> None:
        self.set_fixture_entry_field("version", "0.1.0")
        self.assert_fails_with('"version" belongs only in plugin.json')

    def test_catalog_version_fails(self) -> None:
        self.edit_json(self.marketplace, "version", "1.0.0")
        self.assert_fails_with('the catalog has no "version"')

    def test_versioned_catalog_changelog_fails(self) -> None:
        changelog = self.root / "CHANGELOG.md"
        text = changelog.read_text(encoding="utf-8").replace(
            "## 2026-10-03", "## [0.1.0] - 2026-10-03"
        )
        _ = changelog.write_text(text, encoding="utf-8")
        self.assert_fails_with('expected "## YYYY-MM-DD"')

    def test_issue_form_label_must_exist(self) -> None:
        form = self.root / ".github" / "ISSUE_TEMPLATE" / "bug_report.yml"
        text = form.read_text(encoding="utf-8").replace('"type:bug"', '"type:defect"')
        _ = form.write_text(text, encoding="utf-8")
        self.assert_fails_with('label "type:defect" is not defined')

    def test_missing_plugin_license_fails(self) -> None:
        (self.plugin / "LICENSE").unlink()
        self.assert_fails_with("missing plugin LICENSE")

    def test_unfilled_plugin_license_fails(self) -> None:
        template = (self.root / "templates" / "license" / "LICENSE").read_text(encoding="utf-8")
        _ = (self.plugin / "LICENSE").write_text(template.replace("{{YEAR}}", "2026"), "utf-8")
        errors = self.errors()
        assert any("with the year and holder filled in" in e for e in errors), errors

    def test_remote_hook_repository_fails(self) -> None:
        remote = "  - repo: https://github.com/astral-sh/ruff-pre-commit\n    hooks: []\n"
        self.append(self.root / ".pre-commit-config.yaml", remote)
        self.assert_fails_with("must be local: hooks run the installed tools")

    def test_hook_rev_fails(self) -> None:
        self.append(self.root / ".pre-commit-config.yaml", "    rev: v1.0.0\n")
        self.assert_fails_with("rev pins a hook version")

    def test_unknown_category_fails(self) -> None:
        self.set_fixture_entry_field("category", "misc")
        errors = self.errors()
        assert any('"category" must be one of' in e for e in errors), errors

    def test_unlisted_plugin_directory_fails(self) -> None:
        _ = shutil.copytree(self.plugin, self.root / "plugins" / "orphan-plugin")
        errors = self.errors()
        assert any("not listed in marketplace.json" in e for e in errors), errors

    def test_invalid_semver_fails(self) -> None:
        self.edit_json(self.plugin / ".claude-plugin" / "plugin.json", "version", "1.0")
        errors = self.errors()
        assert any("not a valid SemVer version" in e for e in errors), errors

    def test_changelog_version_mismatch_fails(self) -> None:
        manifest = self.plugin / ".claude-plugin" / "plugin.json"
        released = repo.as_str((repo.as_dict(repo.load_json(manifest)) or {}).get("version"))
        self.edit_json(manifest, "version", "99.0.0")
        self.assert_fails_with(f'latest release is {released} but plugin.json says "99.0.0"')

    def test_missing_readme_section_fails(self) -> None:
        usage = repo.readme_heading("Usage")
        self.edit_readme(usage, "## How to use")
        self.assert_fails_with(f'missing "{usage}" section')

    def test_faq_with_too_few_questions_fails(self) -> None:
        self.edit_readme("<summary>Does it need network access?</summary>", "")
        self.assert_fails_with("needs 3 to 5 questions, found 2")

    def test_faq_with_too_many_questions_fails(self) -> None:
        extra = "".join(
            f"<details>\n<summary>Question {n}?</summary>\n\nAnswer.\n\n</details>\n\n"
            for n in range(3)
        )
        update = repo.readme_heading("Update and uninstall")
        self.edit_readme(update, extra + update)
        self.assert_fails_with("needs 3 to 5 questions, found 6")

    def test_faq_without_the_fixed_first_question_fails(self) -> None:
        self.edit_readme(repo.FAQ_FIRST_QUESTION, "Is this plugin useful?")
        self.assert_fails_with(f'must open with "{repo.FAQ_FIRST_QUESTION}"')

    def test_missing_plugin_label_fails(self) -> None:
        labels = self.root / ".github" / "labels.yml"
        _ = labels.write_text(
            labels.read_text(encoding="utf-8").replace(f'"plugin:{PLUGIN}"', '"plugin:other"'),
            encoding="utf-8",
        )
        self.assert_fails_with(f'label "plugin:{PLUGIN}" is not defined')

    def test_release_workflow_tag_pattern_fails(self) -> None:
        workflow = self.root / ".github" / "workflows" / "release.yml"
        _ = workflow.write_text(
            workflow.read_text(encoding="utf-8").replace('"*--v[0-9]*"', '"v*"'),
            encoding="utf-8",
        )
        self.assert_fails_with("on.push.tags")

    def test_mod_without_minimum_version_fails(self) -> None:
        hooks = self.plugin / "hooks"
        hooks.mkdir()
        _ = (hooks / "hooks.json").write_text(
            json.dumps({"modules": ["./register.js"]}), encoding="utf-8"
        )
        _ = (hooks / "register.js").write_text(
            "export function register(on) {}\n", encoding="utf-8"
        )
        manifest = self.plugin / ".claude-plugin" / "plugin.json"
        self.edit_json(manifest, "metadata", {"minClaudeCodeVersion": "2.1.200"})
        errors = self.errors()
        assert any("mods require" in e for e in errors), errors
        assert any("*.test.ts" in e for e in errors), errors


class AdrValidatorTest(RepositoryFixture):
    """validate_adrs.py fails for each defect in a record, and only for it."""

    record_name: str = "ADR_2026-10-03_testing-approach.md"

    @property
    def decisions(self) -> Path:
        return self.root / "docs" / "adr" / "decisions"

    @property
    def record(self) -> Path:
        return self.decisions / self.record_name

    def adr_errors(self) -> list[str]:
        return validate_adrs.validate(self.root)

    def assert_adr_fails_with(self, fragment: str) -> None:
        errors = self.adr_errors()
        assert errors, "the ADR gate passed although a defect was injected"
        assert all(fragment in error for error in errors), (
            f"expected every error to mention {fragment!r}, got: {errors}"
        )

    def replace_in_record(self, old: str, new: str) -> None:
        text = self.record.read_text(encoding="utf-8")
        assert old in text
        _ = self.record.write_text(text.replace(old, new, 1), encoding="utf-8")

    def test_records_pass(self) -> None:
        assert self.adr_errors() == []

    def test_numbered_file_name_fails(self) -> None:
        _ = self.record.rename(self.decisions / "0010-testing-approach.md")
        self.assert_adr_fails_with("file name must be ADR_YYYY-MM-DD")

    def test_date_mismatch_fails(self) -> None:
        self.replace_in_record("date: 2026-10-03", "date: 2026-10-02")
        self.assert_adr_fails_with("must equal the file name date")

    def test_unknown_status_fails(self) -> None:
        self.replace_in_record("status: accepted", "status: approved")
        self.assert_adr_fails_with('status "approved"')

    def test_template_placeholder_fails(self) -> None:
        self.replace_in_record(
            "## Purpose\n", "## Purpose\n\n{State what this decision establishes.}\n"
        )
        self.assert_adr_fails_with("template placeholder left")

    def test_missing_section_fails(self) -> None:
        self.replace_in_record("### Confirmation", "### Verification")
        self.assert_adr_fails_with('missing "### Confirmation" section')

    def test_superseded_without_successor_fails(self) -> None:
        self.replace_in_record("status: accepted", "status: superseded")
        self.assert_adr_fails_with("must link to the record that supersedes it")

    def test_broken_link_fails(self) -> None:
        self.replace_in_record(
            "## Purpose\n", "## Purpose\n\nSee [missing](ADR_2026-10-03_missing.md).\n"
        )
        self.assert_adr_fails_with("broken link")

    def test_plugin_root_variable_is_not_a_placeholder(self) -> None:
        self.replace_in_record("## Purpose\n", "## Purpose\n\nPaths use `${CLAUDE_PLUGIN_ROOT}`.\n")
        assert self.adr_errors() == []


class NameRulesTest(unittest.TestCase):
    def test_valid_name(self) -> None:
        assert repo.plugin_name_problems("release-notes-writer") == []

    def test_reserved_prefix(self) -> None:
        problems = repo.plugin_name_problems("claude-helper")
        assert any("starts with a prefix reserved" in p for p in problems), problems

    def test_brand_word(self) -> None:
        problems = repo.plugin_name_problems("tools-for-claude")
        assert any("as a word" in p for p in problems), problems

    def test_repository_area(self) -> None:
        problems = repo.plugin_name_problems("docs")
        assert problems == ['"docs" is a repository area (commit scope and branch prefix)']
        assert repo.plugin_name_problems("docs-writer") == []

    def test_not_kebab_case(self) -> None:
        problems = repo.plugin_name_problems("MyPlugin")
        assert any("is not kebab-case" in p for p in problems), problems


class ChangelogTest(unittest.TestCase):
    VALID: str = (
        "# Changelog\n\n## [Unreleased]\n\n## [1.0.0] - 2026-10-01\n\n### Added\n\n- First.\n"
    )

    def test_valid(self) -> None:
        assert repo.parse_changelog(self.VALID).problems == []

    def test_placeholder_date(self) -> None:
        text = self.VALID.replace("2026-10-01", "YYYY-MM-DD")
        assert any("expected YYYY-MM-DD" in p for p in repo.parse_changelog(text).problems)

    def test_missing_unreleased(self) -> None:
        text = self.VALID.replace("## [Unreleased]\n\n", "")
        assert 'missing "## [Unreleased]" section' in repo.parse_changelog(text).problems

    def test_unknown_change_type(self) -> None:
        text = self.VALID.replace("### Added", "### New")
        assert any("unknown change type" in p for p in repo.parse_changelog(text).problems)

    def test_release_moves_unreleased_notes(self) -> None:
        text = self.VALID.replace("## [Unreleased]\n", "## [Unreleased]\n\n### Fixed\n\n- A bug.\n")
        result = bump_version.rewrite_changelog(text, "1.0.1", "2026-10-03")
        parsed = repo.parse_changelog(result)
        assert parsed.problems == []
        assert parsed.unreleased == ""
        assert [r.version for r in parsed.releases] == ["1.0.1", "1.0.0"]
        assert "- A bug." in parsed.releases[0].body

    def test_major_release_requires_migration(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "CHANGELOG.md"
            _ = path.write_text(
                self.VALID.replace(
                    "## [Unreleased]\n",
                    "## [Unreleased]\n\n### Removed\n\n- Old skill.\n",
                ),
                encoding="utf-8",
            )
            outcome = bump_version.prepare(path, "1.0.0", "major")
            assert isinstance(outcome, str)
            assert "Migration" in outcome


class CommitMessageTest(unittest.TestCase):
    def test_valid_with_scope(self) -> None:
        parsed, problems = check_commit_msg.parse("feat(hello-example): add greeting")
        assert problems == []
        expected = check_commit_msg.Parsed(
            type="feat", scope="hello-example", breaking=False, subject="add greeting"
        )
        assert parsed == expected

    def test_breaking_footer(self) -> None:
        parsed, problems = check_commit_msg.parse(
            "fix(x): change output\n\nBREAKING CHANGE: new format"
        )
        assert problems == []
        assert parsed is not None
        assert (parsed.type, parsed.scope, parsed.breaking) == ("fix", "x", True)

    def test_unknown_type_fails(self) -> None:
        _, problems = check_commit_msg.parse("feature: add thing")
        assert any("with type one of: feat, fix" in p for p in problems), problems

    def test_header_over_the_limit_fails(self) -> None:
        _, problems = check_commit_msg.parse("fix: " + "x" * 100)
        assert any("the limit is 100" in p for p in problems), problems
        _, problems = check_commit_msg.parse("fix: " + "x" * 95)
        assert problems == []

    def test_missing_blank_line_fails(self) -> None:
        _, problems = check_commit_msg.parse("fix: thing\nbody right away")
        assert "the line after the header must be blank" in problems

    def test_trailing_period_fails(self) -> None:
        _, problems = check_commit_msg.parse("docs: update readme.")
        assert "subject must not end with a period" in problems


class DatedChangelogTest(unittest.TestCase):
    VALID: str = (
        "# Changelog\n\nIntro.\n\n## 2026-10-02\n\n### Added\n\n- `b`: B.\n\n"
        "## 2026-10-01\n\n### Added\n\n- `a`: A.\n"
    )

    def test_valid(self) -> None:
        assert repo.parse_dated_changelog(self.VALID).problems == []

    def test_oldest_first_fails(self) -> None:
        text = self.VALID.replace("2026-10-02", "2026-09-30")
        problems = repo.parse_dated_changelog(text).problems
        assert problems == ["dated sections must be listed newest first, without duplicates"]

    def test_note_creates_new_date_on_top(self) -> None:
        text = repo.add_dated_note(self.VALID, "2026-10-03", "Removed", "`a`: gone.")
        parsed = repo.parse_dated_changelog(text)
        assert parsed.problems == []
        assert [s.date for s in parsed.sections] == ["2026-10-03", "2026-10-02", "2026-10-01"]
        assert parsed.sections[0].body == "### Removed\n\n- `a`: gone."

    def test_note_joins_existing_date_and_type(self) -> None:
        text = repo.add_dated_note(self.VALID, "2026-10-02", "Added", "`c`: C.")
        section = repo.parse_dated_changelog(text).sections[0]
        assert section.body == "### Added\n\n- `b`: B.\n- `c`: C."

    def test_note_adds_type_to_existing_date(self) -> None:
        text = repo.add_dated_note(self.VALID, "2026-10-02", "Deprecated", "`b`: use c.")
        parsed = repo.parse_dated_changelog(text)
        assert parsed.problems == []
        assert parsed.sections[0].body.endswith("### Deprecated\n\n- `b`: use c.")


class ReleaseDisciplineTest(unittest.TestCase):
    """check_pr: every change inside a plugin ships with its release."""

    RELEASED: str = (
        "# Changelog\n\n## [Unreleased]\n\n## [1.1.0] - 2026-10-03\n\n### Added\n\n- New.\n\n"
        "## [1.0.0] - 2026-10-01\n\n### Added\n\n- First.\n"
    )

    def problems(self, versions: tuple[str, str], text: str = "") -> list[str]:
        log = repo.parse_changelog(text or self.RELEASED)
        return check_pr.release_problems(PLUGIN, versions, log)

    def test_matching_release_passes(self) -> None:
        assert self.problems(("1.0.0", "1.1.0")) == []

    def test_change_without_bump_fails(self) -> None:
        problems = self.problems(("1.0.0", "1.0.0"))
        assert len(problems) == 1
        assert "needs a new version" in problems[0]

    def test_label_is_highest_bump_of_several_plugins(self) -> None:
        assert check_pr.label_problems(["patch", "minor"], ["semver:minor"]) == []
        problems = check_pr.label_problems(["patch", "minor"], ["semver:patch"])
        assert len(problems) == 1
        assert "apply exactly semver:minor" in problems[0]

    def test_label_without_release_fails(self) -> None:
        assert check_pr.label_problems([], []) == []
        problems = check_pr.label_problems([], ["semver:patch"])
        assert len(problems) == 1
        assert "apply only to plugin releases" in problems[0]

    def test_skipped_version_fails(self) -> None:
        problems = self.problems(("1.0.0", "1.2.0"))
        assert len(problems) == 1
        assert "not a single SemVer bump" in problems[0]

    def test_major_needs_migration(self) -> None:
        text = self.RELEASED.replace("[1.1.0]", "[2.0.0]")
        problems = self.problems(("1.0.0", "2.0.0"), text)
        assert len(problems) == 1
        assert "### Migration" in problems[0]

    def test_catalog_change_needs_changelog_note(self) -> None:
        problems = check_pr.catalog_problems([check_pr.CATALOG_FILE])
        assert len(problems) == 1
        assert "add a dated note to CHANGELOG.md" in problems[0]
        assert check_pr.catalog_problems([check_pr.CATALOG_FILE, "CHANGELOG.md"]) == []


class TagFormatTest(unittest.TestCase):
    def test_official_format_round_trip(self) -> None:
        tag = repo.plugin_tag(PLUGIN, "1.2.3")
        assert tag == f"{PLUGIN}--v1.2.3"
        assert repo.split_tag(tag) == (PLUGIN, "1.2.3")

    def test_other_formats_rejected(self) -> None:
        for tag in ("v1.2.3", f"{PLUGIN}-v1.2.3", f"{PLUGIN}--v1.2"):
            assert repo.split_tag(tag) is None, tag


class DocsGateTest(RepositoryFixture):
    """The docs gate fails for each kind of drift, and only for it."""

    def docs_errors(self) -> list[str]:
        return check_docs.run_checks(self.root).errors

    def assert_drift(self, fragment: str) -> None:
        errors = self.docs_errors()
        assert errors, "the docs gate passed although drift was injected"
        assert all(fragment in error for error in errors), (
            f"expected every error to mention {fragment!r}, got: {errors}"
        )

    def replace(self, relative: str, old: str, new: str) -> None:
        path = self.root / relative
        text = path.read_text(encoding="utf-8")
        assert old in text, f"{old!r} not in {relative}"
        _ = path.write_text(text.replace(old, new, 1), encoding="utf-8")

    def test_unmodified_repository_passes(self) -> None:
        assert self.docs_errors() == []

    def test_claude_code_minimum_drift_fails(self) -> None:
        self.replace(
            ".github/ISSUE_TEMPLATE/bug_report.yml",
            f"placeholder: {repo.MIN_CLAUDE_CODE}",
            "placeholder: 2.1.200",
        )
        self.assert_drift("2.1.200 must be")

    def test_moved_pin_sentence_fails(self) -> None:
        self.replace("docs/releasing.md", " or later", " and newer")
        self.assert_drift("update the text or PIN_SITES")

    def test_gate_count_drift_fails(self) -> None:
        self.replace(".claude/rules/testing/gates.md", "10 gates", "9 gates")
        self.assert_drift("gate count is 9")

    def test_missing_target_row_fails(self) -> None:
        self.replace("docs/testing.md", "| `scripts/check.py docs`", "| `docs`")
        self.assert_drift('no row for gate "docs"')

    def test_unknown_script_fails(self) -> None:
        self.append(self.root / "docs" / "testing.md", "\nRun `scripts/no_such.py`.\n")
        self.assert_drift("scripts/no_such.py, which does not exist")

    def test_unknown_check_target_fails(self) -> None:
        self.append(self.root / "docs" / "testing.md", "\nRun `scripts/check.py lint`.\n")
        self.assert_drift('"scripts/check.py lint" is no target')

    def test_rule_matching_nothing_fails(self) -> None:
        rule = self.root / ".claude" / "rules" / "orphan.md"
        _ = rule.write_text('---\npaths:\n  - "nowhere/**"\n---\n\n# Orphan\n', encoding="utf-8")
        self.assert_drift("the rule never loads")

    def test_broken_link_fails(self) -> None:
        self.append(self.root / "docs" / "testing.md", "\nSee [gone](gone.md).\n")
        self.assert_drift("broken link gone.md")

    def test_missing_doc_reference_fails(self) -> None:
        # Built at runtime so this test file itself names no missing document.
        missing = "docs/" + "no-such-guide.md"
        self.append(self.root / "scripts" / "repo.py", f"\n# See {missing}.\n")
        self.assert_drift(f"names {missing}, which does not exist")

    def test_link_in_code_is_ignored(self) -> None:
        self.append(self.root / "docs" / "testing.md", "\nWrite `[x](gone.md)` like this.\n")
        assert self.docs_errors() == []

    def test_skill_name_mismatch_fails(self) -> None:
        self.replace(".claude/skills/verify/SKILL.md", "name: verify", "name: verify-all")
        self.assert_drift("name verify-all must equal verify")

    def test_glob_translation(self) -> None:
        assert check_docs.glob_regex("plugins/**/README.md").match("plugins/a/README.md")
        assert check_docs.glob_regex("plugins/**/README.md").match("plugins/README.md")
        assert not check_docs.glob_regex("scripts/*.py").match("scripts/sub/x.py")
        assert check_docs.glob_regex("**/*.json").match(".claude-plugin/marketplace.json")


class ClaudeHooksTest(unittest.TestCase):
    """The repository's Claude Code hooks decide for the reason they give, and only then."""

    root: Path = ROOT

    @override
    def setUp(self) -> None:
        self.root = make_fixture_dir(self)

    @staticmethod
    def verdict(answer: dict[str, repo.JSON] | None) -> str | None:
        if answer is None:
            return None
        output = repo.as_dict(answer.get("hookSpecificOutput")) or {}
        return repo.as_str(output.get("permissionDecision"))

    def test_pushes_ask_in_every_spelling(self) -> None:
        for command in (
            "git push",
            "git push origin main",
            "git -C . push origin main",
            "git -c push.default=current push",
            "FOO=1 git push",
            "git status && git push --tags",
            "/usr/bin/git push",
        ):
            assert self.verdict(claude_hooks.bash_decision(command)) == "ask", command

    def test_reads_and_local_git_pass(self) -> None:
        for command in ("git status", "git log -1", "echo git push", "git commit -S -m x"):
            assert claude_hooks.bash_decision(command) is None, command

    def test_signing_bypass_is_denied(self) -> None:
        for command in (
            "git commit --no-gpg-sign -m x",
            "git -c commit.gpgsign=false commit -m x",
            "git commit --no-verify -m x",
        ):
            assert self.verdict(claude_hooks.bash_decision(command)) == "deny", command

    def test_wrapped_pushes_ask(self) -> None:
        for command in (
            "bash -c 'git push origin main'",
            "sh -lc 'gh pr merge 3'",
            "echo x | xargs git push",
            "nice -n 5 git push",
            "time git push",
        ):
            assert self.verdict(claude_hooks.bash_decision(command)) == "ask", command

    def test_message_mentioning_a_bypass_flag_passes(self) -> None:
        for command in ("git commit -m 'docs: explain --no-verify'", "git log -n 3"):
            assert claude_hooks.bash_decision(command) is None, command
        for command in ("git commit -n -m x", "git -ccore.hooksPath=/dev/null commit"):
            assert self.verdict(claude_hooks.bash_decision(command)) == "deny", command

    def test_heredoc_message_text_is_not_a_command(self) -> None:
        message = "git commit -S -F - <<'EOF'\nfix: explain --no-verify and -n\nEOF"
        assert claude_hooks.bash_decision(message) is None
        tag = "git tag -a v1 -F - <<'EOF'\nnotes mention --no-verify\nEOF"
        assert claude_hooks.bash_decision(tag) is None

    def test_heredoc_that_is_not_a_git_message_keeps_its_body(self) -> None:
        for command in (
            "git commit --no-verify -F - <<'EOF'\nfix: x\nEOF",
            "git status # <<EOF\ngit -c commit.gpgsign=false commit -m y\nEOF",
            "git commit -m x # <<EOF\ngit commit --no-verify -m y\nEOF",
            'git commit -m "<<EOF"\ngit commit --no-verify -m y\nEOF',
            "git -c alias.p='!sh' p <<'EOF'\ngit commit --no-verify -m y\nEOF",
            "git commit -F - # <<EOF\ngit commit --no-verify -m y\nEOF",
            # Conservative on purpose: any `-c` may define an alias, so the body stays visible.
            "git -c user.name=x commit -F - <<'EOF'\ngit commit --no-verify -m y\nEOF",
        ):
            assert self.verdict(claude_hooks.bash_decision(command)) == "deny", command

    def test_search_walking_into_a_forbidden_source_is_denied(self) -> None:
        _ = self.write("CLAUDE.local.md", LOCAL_NOTES)
        parent = Path.home() / "projects" / "marketplace"
        cases: list[tuple[dict[str, repo.JSON], str | None]] = [
            ({"path": str(parent)}, "deny"),
            ({"path": str(Path.home() / "projects")}, "deny"),
            ({"command": "grep -rn TODO ~/projects/marketplace"}, "deny"),
            ({"command": "find ~/projects -name x"}, "deny"),
            ({"command": "ls ~/projects/marketplace"}, None),
            ({"path": str(Path.home() / "work")}, None),
        ]
        for tool_input, expected in cases:
            answer = claude_hooks.sources_decision(tool_input, self.root)
            assert self.verdict(answer) == expected, tool_input

    def test_github_writes_ask_and_reads_pass(self) -> None:
        for command in (
            "gh pr create --fill",
            "gh release create x",
            "gh api -X POST repos/o/r/labels",
            "gh api repos/o/r/labels -f name=x",
            "claude plugin tag plugins/x --push",
        ):
            assert self.verdict(claude_hooks.bash_decision(command)) == "ask", command
        for command in (
            "gh pr view 2",
            "gh api repos/o/r",
            "claude plugin tag plugins/x --dry-run",
        ):
            assert claude_hooks.bash_decision(command) is None, command

    def write(self, relative: str, text: str) -> Path:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        _ = path.write_text(text, encoding="utf-8")
        return path

    def test_manual_version_edit_is_denied(self) -> None:
        manifest = self.write("plugins/p/.claude-plugin/plugin.json", '{"version": "0.1.0"}\n')
        edit: dict[str, repo.JSON] = {
            "file_path": str(manifest),
            "old_string": '"0.1.0"',
            "new_string": '"0.2.0"',
        }
        assert self.verdict(claude_hooks.edit_decision("Edit", edit, self.root)) == "deny"
        rename: dict[str, repo.JSON] = {
            "file_path": str(manifest),
            "old_string": '{"version"',
            "new_string": '{ "version"',
        }
        assert claude_hooks.edit_decision("Edit", rename, self.root) is None

    def test_generated_block_edit_is_denied(self) -> None:
        readme = self.write(
            "plugins/p/README.md",
            "intro\n<!-- BEGIN GENERATED: header -->\nold\n<!-- END GENERATED: header -->\n",
        )
        inside: dict[str, repo.JSON] = {
            "file_path": str(readme),
            "old_string": "old",
            "new_string": "new",
        }
        assert self.verdict(claude_hooks.edit_decision("Edit", inside, self.root)) == "deny"
        outside: dict[str, repo.JSON] = {
            "file_path": str(readme),
            "old_string": "intro",
            "new_string": "Intro",
        }
        assert claude_hooks.edit_decision("Edit", outside, self.root) is None

    def test_forbidden_sources_are_denied_at_exact_boundaries(self) -> None:
        _ = self.write("CLAUDE.local.md", LOCAL_NOTES)
        forbidden_path = str(Path.home() / "projects" / "marketplace" / "kept" / "x.md")
        allowed_path = str(Path.home() / "work" / "kept" / "x.md")
        cases: list[tuple[dict[str, repo.JSON], str | None]] = [
            ({"file_path": forbidden_path}, "deny"),
            ({"command": "ls ~/projects/marketplace/kept"}, "deny"),
            ({"file_path": allowed_path}, None),
            ({"command": "ls ~/projects/marketplace/kept-new"}, None),
            ({"command": "gh repo clone owner/old-repo"}, "deny"),
            ({"command": "gh repo view owner/kept"}, None),
            ({"owner": "owner", "repo": "kept-deprecated"}, "deny"),
        ]
        for tool_input, expected in cases:
            answer = claude_hooks.sources_decision(tool_input, self.root)
            assert self.verdict(answer) == expected, tool_input

    def test_writing_about_a_forbidden_source_passes(self) -> None:
        _ = self.write("CLAUDE.local.md", LOCAL_NOTES)
        mention = "Never read ~/projects/marketplace/kept or owner/old-repo."
        cases: list[dict[str, repo.JSON]] = [
            {"file_path": str(self.root / "guide.md"), "content": mention},
            {"file_path": str(self.root / "guide.md"), "old_string": "x", "new_string": mention},
        ]
        for tool_input in cases:
            assert claude_hooks.sources_decision(tool_input, self.root) is None, tool_input

    def test_no_local_notes_means_no_denial(self) -> None:
        assert claude_hooks.sources_decision({"command": "ls"}, self.root) is None

    def test_format_reports_only_real_changes(self) -> None:
        messy = self.write("doc.md", "# Title\n\n\n\nText\n")
        answer = claude_hooks.format_file(messy, self.root)
        assert answer is not None
        assert "prettier reformatted doc.md" in json.dumps(answer)
        assert claude_hooks.format_file(messy, self.root) is None
        outside = Path(tempfile.gettempdir()) / "not-in-repo.md"
        assert claude_hooks.format_file(outside, self.root) is None

    def test_session_status_names_the_project_and_the_rule_loading(self) -> None:
        status = claude_hooks.session_status(ROOT)
        assert status.startswith("claude-essentials: "), status
        assert "path-scoped rules" in status


class AddComponentTest(unittest.TestCase):
    """The component scaffold names the copy and leaves a note the gate rejects."""

    def test_rename_sets_frontmatter_and_heading(self) -> None:
        text = add_component.rename("---\nname: example\n---\n\n# example\n\nTODO\n", "greet")
        assert "name: greet\n" in text
        assert "# greet\n" in text

    def test_note_creates_added_section(self) -> None:
        text = "# Changelog\n\n## [Unreleased]\n\n## [0.1.0] - 2026-10-04\n"
        result = add_component.add_unreleased_note(text, "TODO: x")
        assert "## [Unreleased]\n\n### Added\n\n- TODO: x\n\n## [0.1.0]" in result

    def test_note_joins_existing_added_section(self) -> None:
        text = "## [Unreleased]\n\n### Added\n\n- First.\n\n## [0.1.0] - 2026-10-04\n"
        result = add_component.add_unreleased_note(text, "Second.")
        assert "- First.\n- Second.\n\n## [0.1.0]" in result

    def test_target_paths(self) -> None:
        plugin = Path("plugins/p")
        assert add_component.target_path(plugin, "skill", "x") == plugin / "skills/x/SKILL.md"
        assert add_component.target_path(plugin, "agent", "x") == plugin / "agents/x.md"


class ReleaseNotesTest(RepositoryFixture):
    """release_notes.py verify, run as the release workflow runs it, on the fixture copy."""

    def verify(self, tag: str) -> tuple[int, str]:
        script = self.root / "scripts" / "release_notes.py"
        result = repo.run([str(script), "verify", tag], check=False)
        return result.returncode, result.stdout + result.stderr

    def declared_version(self) -> str:
        manifest = self.plugin / ".claude-plugin" / "plugin.json"
        return repo.as_str((repo.as_dict(repo.load_json(manifest)) or {}).get("version")) or ""

    def test_tag_matching_the_manifest_passes(self) -> None:
        code, output = self.verify(repo.plugin_tag(PLUGIN, self.declared_version()))
        assert code == 0, output
        assert "matches" in output

    def test_tag_disagreeing_with_the_manifest_fails(self) -> None:
        self.edit_json(self.plugin / ".claude-plugin" / "plugin.json", "version", "99.0.0")
        code, output = self.verify(repo.plugin_tag(PLUGIN, "1.2.3"))
        assert code == 1, output
        assert 'declares version "99.0.0"' in output

    def test_malformed_tag_fails(self) -> None:
        code, output = self.verify("v1.2.3")
        assert code == 1, output
        assert "is not a <name>--v<version> tag" in output


class DrivePluginTest(unittest.TestCase):
    """The plugin driver's stream parsing, without a model call."""

    @staticmethod
    def stream(*, plugins: list[str], mcp: int = 0, is_error: bool = False) -> str:
        loaded = [
            {"name": source.split("@")[0], "source": source}
            for source in [*(f"{name}@inline" for name in plugins), "cc-plugin-telemetry@builtin"]
        ]
        init = {
            "type": "system",
            "subtype": "init",
            "plugins": loaded,
            "mcp_servers": [{"name": f"server-{i}"} for i in range(mcp)],
        }
        result = {"type": "result", "result": "Hello there", "is_error": is_error}
        return "Warning: not JSON\n" + json.dumps(init) + "\n" + json.dumps(result) + "\n"

    def test_clean_session_passes(self) -> None:
        outcome = drive_plugin.read_stream(self.stream(plugins=[PLUGIN]), PLUGIN)
        assert outcome.errors == []
        assert outcome.reply == "Hello there"

    def test_missing_plugin_fails(self) -> None:
        outcome = drive_plugin.read_stream(self.stream(plugins=[]), PLUGIN)
        assert outcome.errors == [f"{PLUGIN} did not load into the session"]

    def test_foreign_plugin_fails(self) -> None:
        outcome = drive_plugin.read_stream(self.stream(plugins=[PLUGIN, "other"]), PLUGIN)
        assert outcome.errors == ["unexpected plugin loaded: other@inline"]

    def test_leaked_mcp_server_fails(self) -> None:
        outcome = drive_plugin.read_stream(self.stream(plugins=[PLUGIN], mcp=2), PLUGIN)
        assert outcome.errors == ["MCP servers leaked into the session: 2"]

    def test_error_result_fails(self) -> None:
        outcome = drive_plugin.read_stream(self.stream(plugins=[PLUGIN], is_error=True), PLUGIN)
        assert outcome.errors == ["the session ended with an error: Hello there"]

    def test_no_result_fails(self) -> None:
        outcome = drive_plugin.read_stream("", PLUGIN)
        assert outcome.errors == ["the session produced no result event"]

    def test_default_prompt_is_first_skill(self) -> None:
        assert drive_plugin.default_prompt(FIXTURE_PLUGIN) == f"/{PLUGIN}:hello"


if __name__ == "__main__":
    _ = unittest.main()
