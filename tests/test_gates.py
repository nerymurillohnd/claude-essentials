"""Tests for the repository gates.

Each negative test copies the repository to a temporary directory, injects one
defect, and asserts that the gate fails for that reason and no other. The
positive baseline proves the unmodified copy passes, so a failure in a
negative test can only come from the injected defect.

Run: uv run scripts/check.py tests
"""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from typing import override

import bump_version
import check_commit_msg
import check_repo
import repo

ROOT = repo.ROOT

PLUGIN = "hello-example"
IGNORED = shutil.ignore_patterns(
    ".git", "__pycache__", ".venv", ".ruff_cache", ".DS_Store"
)


class RepositoryFixture(unittest.TestCase):
    """A fresh copy of the repository for every test."""

    root: Path = ROOT
    _tmp: tempfile.TemporaryDirectory[str] | None = None

    @override
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="gate-fixture-")
        self.root = Path(self._tmp.name) / "repo"
        _ = shutil.copytree(ROOT, self.root, ignore=IGNORED, symlinks=True)

    @override
    def tearDown(self) -> None:
        if self._tmp is not None:
            location = Path(self._tmp.name)
            self._tmp.cleanup()
            # Every fixture is removed; nothing may outlive a test (docs/testing.md#cleanup).
            self.assertFalse(location.exists(), f"fixture {location} was not removed")

    @property
    def plugin(self) -> Path:
        return self.root / "plugins" / PLUGIN

    def errors(self) -> list[str]:
        return check_repo.run_checks(self.root).errors

    def assert_fails_with(self, fragment: str) -> None:
        errors = self.errors()
        self.assertTrue(errors, "the gate passed although a defect was injected")
        self.assertTrue(
            all(fragment in error for error in errors),
            f"expected every error to mention {fragment!r}, got: {errors}",
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
        self.assertEqual(self.errors(), [])


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
        self.append(
            self.plugin / "README.md", "\nWrite to someone@personal-mail.io for help.\n"
        )
        self.assert_fails_with("personal email")

    def test_example_email_passes(self) -> None:
        self.append(self.plugin / "README.md", "\nFor example, user@example.com.\n")
        self.assertEqual(self.errors(), [])

    def test_unfinished_placeholder_fails(self) -> None:
        self.append(
            self.plugin / "skills" / "hello" / "SKILL.md", "\nTODO: write the steps.\n"
        )
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
                "PostToolUse": [
                    {"hooks": [{"type": "command", "command": "./scripts/format.sh"}]}
                ]
            }
        }
        _ = (hooks / "hooks.json").write_text(json.dumps(config), encoding="utf-8")
        errors = self.errors()
        self.assertTrue(
            any('command path "./scripts/format.sh"' in e for e in errors), errors
        )

    def test_plugin_root_hook_command_passes_self_containment(self) -> None:
        hooks = self.plugin / "hooks"
        hooks.mkdir()
        command = '"${CLAUDE_PLUGIN_ROOT}"/scripts/format.sh'
        config = {
            "hooks": {
                "PostToolUse": [{"hooks": [{"type": "command", "command": command}]}]
            }
        }
        _ = (hooks / "hooks.json").write_text(json.dumps(config), encoding="utf-8")
        errors = self.errors()
        self.assertFalse(any("command path" in e for e in errors), errors)
        # A hook makes the plugin privileged, so its README must document Permissions.
        self.assertTrue(any("## Permissions" in e for e in errors), errors)


class CatalogGateTest(RepositoryFixture):
    @property
    def marketplace(self) -> Path:
        return self.root / ".claude-plugin" / "marketplace.json"

    def test_missing_disclaimer_fails(self) -> None:
        self.edit_json(
            self.marketplace, "description", "Community plugins for Claude Code."
        )
        self.assert_fails_with("not affiliated")

    def test_version_in_entry_fails(self) -> None:
        data = repo.as_dict(repo.load_json(self.marketplace)) or {}
        entries = repo.as_list(data.get("plugins")) or []
        entry = repo.as_dict(entries[0]) or {}
        entry["version"] = "0.1.0"
        _ = self.marketplace.write_text(json.dumps(data, indent=2), encoding="utf-8")
        self.assert_fails_with('"version" belongs only in plugin.json')

    def test_unknown_category_fails(self) -> None:
        data = repo.as_dict(repo.load_json(self.marketplace)) or {}
        entry = repo.as_dict((repo.as_list(data.get("plugins")) or [])[0]) or {}
        entry["category"] = "misc"
        _ = self.marketplace.write_text(json.dumps(data, indent=2), encoding="utf-8")
        errors = self.errors()
        self.assertTrue(any('"category" must be one of' in e for e in errors), errors)

    def test_unlisted_plugin_directory_fails(self) -> None:
        _ = shutil.copytree(self.plugin, self.root / "plugins" / "orphan-plugin")
        errors = self.errors()
        self.assertTrue(
            any("not listed in marketplace.json" in e for e in errors), errors
        )

    def test_invalid_semver_fails(self) -> None:
        self.edit_json(self.plugin / ".claude-plugin" / "plugin.json", "version", "1.0")
        errors = self.errors()
        self.assertTrue(any("not a valid SemVer version" in e for e in errors), errors)

    def test_changelog_version_mismatch_fails(self) -> None:
        self.edit_json(
            self.plugin / ".claude-plugin" / "plugin.json", "version", "0.2.0"
        )
        self.assert_fails_with("latest release is 0.1.0")

    def test_missing_readme_section_fails(self) -> None:
        readme = self.plugin / "README.md"
        _ = readme.write_text(
            readme.read_text(encoding="utf-8").replace("## Usage", "## How to use"),
            encoding="utf-8",
        )
        self.assert_fails_with('missing "## Usage" section')

    def test_missing_plugin_label_fails(self) -> None:
        labels = self.root / ".github" / "labels.yml"
        _ = labels.write_text(
            labels.read_text(encoding="utf-8").replace(
                f'"plugin:{PLUGIN}"', '"plugin:other"'
            ),
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
        self.assertTrue(any("mods require" in e for e in errors), errors)
        self.assertTrue(any("*.test.ts" in e for e in errors), errors)


class NameRulesTest(unittest.TestCase):
    def test_valid_name(self) -> None:
        self.assertEqual(repo.plugin_name_problems("release-notes-writer"), [])

    def test_reserved_prefix(self) -> None:
        self.assertTrue(repo.plugin_name_problems("claude-helper"))

    def test_brand_word(self) -> None:
        self.assertTrue(repo.plugin_name_problems("tools-for-claude"))

    def test_not_kebab_case(self) -> None:
        self.assertTrue(repo.plugin_name_problems("MyPlugin"))

    def test_reserved_marketplace_name(self) -> None:
        self.assertTrue(repo.plugin_name_problems("marketplace"))


class ChangelogTest(unittest.TestCase):
    VALID: str = "# Changelog\n\n## [Unreleased]\n\n## [1.0.0] - 2026-10-01\n\n### Added\n\n- First.\n"

    def test_valid(self) -> None:
        self.assertEqual(repo.parse_changelog(self.VALID).problems, [])

    def test_placeholder_date(self) -> None:
        text = self.VALID.replace("2026-10-01", "YYYY-MM-DD")
        self.assertTrue(
            any("expected YYYY-MM-DD" in p for p in repo.parse_changelog(text).problems)
        )

    def test_missing_unreleased(self) -> None:
        text = self.VALID.replace("## [Unreleased]\n\n", "")
        self.assertIn(
            'missing "## [Unreleased]" section', repo.parse_changelog(text).problems
        )

    def test_unknown_change_type(self) -> None:
        text = self.VALID.replace("### Added", "### New")
        self.assertTrue(
            any("unknown change type" in p for p in repo.parse_changelog(text).problems)
        )

    def test_release_moves_unreleased_notes(self) -> None:
        text = self.VALID.replace(
            "## [Unreleased]\n", "## [Unreleased]\n\n### Fixed\n\n- A bug.\n"
        )
        result = bump_version.rewrite_changelog(text, "1.0.1", "2026-10-03")
        parsed = repo.parse_changelog(result)
        self.assertEqual(parsed.problems, [])
        self.assertEqual(parsed.unreleased, "")
        self.assertEqual([r.version for r in parsed.releases], ["1.0.1", "1.0.0"])
        self.assertIn("- A bug.", parsed.releases[0].body)

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
            self.assertIsInstance(outcome, str)
            self.assertIn("Migration", str(outcome))


class CommitMessageTest(unittest.TestCase):
    def test_valid_with_scope(self) -> None:
        parsed, problems = check_commit_msg.parse("feat(hello-example): add greeting")
        self.assertEqual(problems, [])
        self.assertIsNotNone(parsed)

    def test_breaking_footer(self) -> None:
        parsed, problems = check_commit_msg.parse(
            "fix(x): change output\n\nBREAKING CHANGE: new format"
        )
        self.assertEqual(problems, [])
        self.assertTrue(parsed is not None and parsed.breaking)

    def test_unknown_type_fails(self) -> None:
        _, problems = check_commit_msg.parse("feature: add thing")
        self.assertTrue(problems)

    def test_missing_blank_line_fails(self) -> None:
        _, problems = check_commit_msg.parse("fix: thing\nbody right away")
        self.assertIn("the line after the header must be blank", problems)

    def test_trailing_period_fails(self) -> None:
        _, problems = check_commit_msg.parse("docs: update readme.")
        self.assertIn("subject must not end with a period", problems)


class TagFormatTest(unittest.TestCase):
    def test_official_format_round_trip(self) -> None:
        tag = repo.plugin_tag(PLUGIN, "1.2.3")
        self.assertEqual(tag, f"{PLUGIN}--v1.2.3")
        self.assertEqual(repo.split_tag(tag), (PLUGIN, "1.2.3"))

    def test_other_formats_rejected(self) -> None:
        for tag in ("v1.2.3", f"{PLUGIN}-v1.2.3", f"{PLUGIN}--v1.2"):
            self.assertIsNone(repo.split_tag(tag), tag)


if __name__ == "__main__":
    _ = unittest.main()
