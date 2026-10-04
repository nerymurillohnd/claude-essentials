"""Tests for the repository gates.

Each negative test copies the repository to a temporary directory, injects one
defect, and asserts that the gate fails for that reason and no other. The
positive baseline proves the unmodified copy passes, so a failure in a
negative test can only come from the injected defect.

Run: python3 scripts/check.py tests
"""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import tempfile
from typing import override
import unittest

import bump_version
import check_commit_msg
import check_pr
import check_repo
import repo
import validate_adrs

ROOT = repo.ROOT

PLUGIN = "hello-example"
IGNORED = shutil.ignore_patterns(".git", "__pycache__", ".venv", ".ruff_cache", ".DS_Store")


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
            assert not location.exists(), f"fixture {location} was not removed"

    @property
    def plugin(self) -> Path:
        return self.root / "plugins" / PLUGIN

    def errors(self) -> list[str]:
        return check_repo.run_checks(self.root).errors

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
        assert any("## Permissions" in e for e in errors), errors


class CatalogGateTest(RepositoryFixture):
    @property
    def marketplace(self) -> Path:
        return self.root / ".claude-plugin" / "marketplace.json"

    def test_missing_disclaimer_fails(self) -> None:
        self.edit_json(self.marketplace, "description", "Community plugins for Claude Code.")
        self.assert_fails_with("not affiliated")

    def test_version_in_entry_fails(self) -> None:
        data = repo.as_dict(repo.load_json(self.marketplace)) or {}
        entries = repo.as_list(data.get("plugins")) or []
        entry = repo.as_dict(entries[0]) or {}
        entry["version"] = "0.1.0"
        _ = self.marketplace.write_text(json.dumps(data, indent=2), encoding="utf-8")
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

    def test_hook_pin_drift_fails(self) -> None:
        config = self.root / ".pre-commit-config.yaml"
        text = config.read_text(encoding="utf-8").replace("rev: 1.40.1", "rev: 1.40.0")
        _ = config.write_text(text, encoding="utf-8")
        self.assert_fails_with("must be 1.40.1 (BASEDPYRIGHT_VERSION in check.py)")

    def test_unknown_category_fails(self) -> None:
        data = repo.as_dict(repo.load_json(self.marketplace)) or {}
        entry = repo.as_dict((repo.as_list(data.get("plugins")) or [])[0]) or {}
        entry["category"] = "misc"
        _ = self.marketplace.write_text(json.dumps(data, indent=2), encoding="utf-8")
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
        readme = self.plugin / "README.md"
        _ = readme.write_text(
            readme.read_text(encoding="utf-8").replace("## Usage", "## How to use"),
            encoding="utf-8",
        )
        self.assert_fails_with('missing "## Usage" section')

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
        assert repo.plugin_name_problems("claude-helper")

    def test_brand_word(self) -> None:
        assert repo.plugin_name_problems("tools-for-claude")

    def test_not_kebab_case(self) -> None:
        assert repo.plugin_name_problems("MyPlugin")


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
        assert parsed is not None

    def test_breaking_footer(self) -> None:
        parsed, problems = check_commit_msg.parse(
            "fix(x): change output\n\nBREAKING CHANGE: new format"
        )
        assert problems == []
        assert parsed is not None
        assert parsed.breaking

    def test_unknown_type_fails(self) -> None:
        _, problems = check_commit_msg.parse("feature: add thing")
        assert problems

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
        assert check_pr.label_problems([], ["semver:patch"])

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
        assert check_pr.catalog_problems([check_pr.CATALOG_FILE])
        assert check_pr.catalog_problems([check_pr.CATALOG_FILE, "CHANGELOG.md"]) == []


class TagFormatTest(unittest.TestCase):
    def test_official_format_round_trip(self) -> None:
        tag = repo.plugin_tag(PLUGIN, "1.2.3")
        assert tag == f"{PLUGIN}--v1.2.3"
        assert repo.split_tag(tag) == (PLUGIN, "1.2.3")

    def test_other_formats_rejected(self) -> None:
        for tag in ("v1.2.3", f"{PLUGIN}-v1.2.3", f"{PLUGIN}--v1.2"):
            assert repo.split_tag(tag) is None, tag


if __name__ == "__main__":
    _ = unittest.main()
