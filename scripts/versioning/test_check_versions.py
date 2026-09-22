"""Tests for the version gate: the golden last line, the JSON contract and the exit codes."""

from __future__ import annotations

from dataclasses import replace
import json
import stat
from typing import TYPE_CHECKING, Final

import pytest

from scripts.common.errors import ExitCode, Finding
from scripts.common.jsontext import is_json_object
from scripts.common.plugins import parse_json
from scripts.versioning.check_versions import (
    DEFAULT_BASE,
    LABEL_PREFIX,
    finding_line,
    main,
    parse_args,
    plugin_line,
    render,
    verify_tags,
)
from scripts.versioning.conftest import fetch_as_pull_request, manifest_text, write_file
from scripts.versioning.tag_versions import CLAUDE_BIN_ENV
from scripts.versioning.version_plan import (
    Plan,
    PluginPlan,
    build_plan,
    plugin_json_obj,
    to_json_obj,
)

if TYPE_CHECKING:
    from pathlib import Path

GOLDEN_LABEL: Final = "Computed label: bump: none"
"""The exact last line `.claude/hooks/guard-push.sh` searches for before a direct push."""

JSON_KEYS: Final = (
    "name",
    "predecessor",
    "tagged",
    "version",
    "runtime_changed",
    "first_runtime_path",
    "required",
    "ok",
    "reason",
)


EXEMPT_PLUGIN: Final = PluginPlan(
    name="alpha",
    predecessor=None,
    tagged="0.1.0",
    version="0.1.0",
    runtime_changed=False,
    first_runtime_path=None,
    required=False,
    ok=True,
    reason="",
    level="none",
)
"""A plugin whose only changed files were exempt; every other case is a `replace` of it."""


def test_parse_args_defaults_to_origin_main() -> None:
    """The route is measured against `origin/main` unless the caller says otherwise."""
    options = parse_args([])
    assert options.base == DEFAULT_BASE
    assert not options.verify_tag
    assert not options.deferred
    assert not options.as_json
    assert options.output_format == "text"


def test_parse_args_reads_every_flag_ci_passes() -> None:
    """The exact invocation the `version-check` job builds."""
    options = parse_args(["--base", "origin/main", "--verify-tag", "--deferred", "--json"])
    assert options.base == "origin/main"
    assert options.verify_tag
    assert options.deferred
    assert options.as_json


def test_parse_args_reads_the_head_ref_triage_passes() -> None:
    """`triage.yml` reads the pull request head as git objects, never as a working tree."""
    assert parse_args([]).head is None
    assert parse_args(["--head", "FETCH_HEAD"]).head == "FETCH_HEAD"


def test_verify_tag_and_head_are_refused_together(capsys: pytest.CaptureFixture[str]) -> None:
    """`claude plugin tag --dry-run` runs on the working tree, which `--head` never reads."""
    assert main(["--head", "FETCH_HEAD", "--verify-tag"]) == ExitCode.USAGE
    assert "cannot run with --head" in capsys.readouterr().err


def test_parse_args_reads_the_github_output_format() -> None:
    """CI renders findings as workflow annotations."""
    assert parse_args(["--output-format", "github"]).output_format == "github"


def test_plugin_line_for_an_exempt_plugin() -> None:
    """Nothing Claude loads changed."""
    assert plugin_line(EXEMPT_PLUGIN) == "alpha 0.1.0 exempt"


def test_plugin_line_for_a_new_plugin() -> None:
    """A plugin with no tag has no baseline to compare against."""
    assert (
        plugin_line(replace(EXEMPT_PLUGIN, tagged=None, level="initial"))
        == "alpha 0.1.0 new plugin"
    )


def test_plugin_line_for_a_removed_plugin() -> None:
    """A removed plugin has no version left to print."""
    assert plugin_line(replace(EXEMPT_PLUGIN, version="", level="removal")) == "alpha removed"


def test_plugin_line_names_the_file_and_the_level_owed() -> None:
    """The maintainer needs the path, not just the verdict."""
    line = plugin_line(
        replace(
            EXEMPT_PLUGIN,
            runtime_changed=True,
            first_runtime_path="skills/demo/SKILL.md",
            required=True,
        ),
    )
    assert line == "alpha 0.1.0 runtime: skills/demo/SKILL.md → needs patch"


def test_plugin_line_reports_a_bump_that_happened() -> None:
    """A correctly bumped plugin still shows what changed and by how much."""
    line = plugin_line(
        replace(
            EXEMPT_PLUGIN,
            version="0.1.1",
            runtime_changed=True,
            first_runtime_path="skills/demo/SKILL.md",
            level="patch",
        ),
    )
    assert line == "alpha 0.1.1 runtime: skills/demo/SKILL.md → bumped from 0.1.0 (patch)"


def test_plugin_line_reports_a_deferred_drift() -> None:
    """A deferred plugin is not failing; it is waiting for the next release."""
    line = plugin_line(
        replace(EXEMPT_PLUGIN, runtime_changed=True, first_runtime_path="skills/demo/SKILL.md"),
    )
    assert line == "alpha 0.1.0 runtime: skills/demo/SKILL.md → deferred"


def test_no_plugin_line_can_contain_the_label_prefix() -> None:
    """`guard-push.sh` searches the whole output for `bump: `, so only the label may carry it."""
    lines = [
        plugin_line(EXEMPT_PLUGIN),
        plugin_line(replace(EXEMPT_PLUGIN, tagged=None, level="initial")),
        plugin_line(replace(EXEMPT_PLUGIN, version="", level="removal")),
        plugin_line(
            replace(EXEMPT_PLUGIN, runtime_changed=True, first_runtime_path="a", required=True)
        ),
        plugin_line(
            replace(EXEMPT_PLUGIN, version="0.2.0", runtime_changed=True, first_runtime_path="a")
        ),
    ]
    assert not any("bump: " in line for line in lines)


def test_finding_line_renders_plain_text() -> None:
    """P14: every message starts with the id of the invariant it violates."""
    finding = Finding("V1", "plugins/alpha/skills/demo/SKILL.md", "needs a bump")
    assert finding_line(finding, output_format="text") == (
        "V1 plugins/alpha/skills/demo/SKILL.md: needs a bump"
    )


def test_finding_line_renders_a_github_annotation() -> None:
    """CI puts the finding on the offending line of the pull request."""
    finding = Finding("V1", "plugins/alpha/skills/demo/SKILL.md", "needs a bump")
    assert finding_line(finding, output_format="github") == (
        "::error file=plugins/alpha/skills/demo/SKILL.md::V1 needs a bump"
    )


def test_finding_line_handles_a_repository_wide_finding() -> None:
    """A finding with no path still annotates the run."""
    assert finding_line(Finding("V6", None, "no CLI"), output_format="github") == (
        "::error::V6 no CLI"
    )


def test_render_puts_the_label_last() -> None:
    """The contract is positional: the label is the last line and nothing follows it."""
    plan = Plan(
        route="direct", label="bump: none", deferred=False, plugins=(EXEMPT_PLUGIN,), findings=()
    )
    lines = render(plan, extra=["extra line"], findings=[], output_format="text")
    assert lines[-1] == f"{LABEL_PREFIX}bump: none"
    assert lines == ["alpha 0.1.0 exempt", "extra line", GOLDEN_LABEL]


@pytest.mark.slow
def test_the_golden_last_line(
    repo: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An unchanged tree prints one exempt line and exactly the golden label."""
    monkeypatch.chdir(repo)
    assert main(["--base", "main"]) == int(ExitCode.OK)
    lines = capsys.readouterr().out.splitlines()
    assert lines == ["alpha 0.1.0 exempt", GOLDEN_LABEL]
    assert lines[-1] == GOLDEN_LABEL


@pytest.mark.slow
def test_json_output_is_only_json(
    repo: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`make versions VERSIONS_ARGS=--json | jq` must not have to skip a human report."""
    plan = build_plan(repo, base="main")
    expected = to_json_obj(plan)
    monkeypatch.chdir(repo)
    assert main(["--base", "main", "--json"]) == int(ExitCode.OK)
    assert capsys.readouterr().out.strip() == json.dumps(expected, indent=2)
    assert list(expected) == ["route", "label", "deferred", "plugins"]
    assert expected["route"] == "direct"
    assert expected["label"] == "bump: none"
    assert expected["deferred"] is False
    assert tuple(plugin_json_obj(plan.plugins[0])) == JSON_KEYS


@pytest.mark.slow
def test_an_unbumped_runtime_change_fails(
    repo: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The defect ADR-0003 exists for: two behaviours sharing one version."""
    write_file(repo / "plugins/alpha/skills/demo/SKILL.md", "---\nname: alpha\n---\n\nNew.\n")
    monkeypatch.chdir(repo)
    assert main(["--base", "main"]) == int(ExitCode.FINDINGS)
    out = capsys.readouterr().out
    assert "runtime: skills/demo/SKILL.md → needs patch" in out
    assert "V1 plugins/alpha/skills/demo/SKILL.md:" in out
    assert out.splitlines()[-1] == GOLDEN_LABEL


@pytest.mark.slow
def test_the_github_format_annotates_the_offending_file(
    repo: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CI shows the finding on the pull request's own diff."""
    write_file(repo / "plugins/alpha/skills/demo/SKILL.md", "---\nname: alpha\n---\n\nNew.\n")
    monkeypatch.chdir(repo)
    assert main(["--base", "main", "--output-format", "github"]) == int(ExitCode.FINDINGS)
    assert "::error file=plugins/alpha/skills/demo/SKILL.md::V1 " in capsys.readouterr().out


@pytest.mark.slow
def test_deferred_turns_the_failure_into_a_pass(
    repo: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`bump: deferred` is a maintainer decision the gate honours without arguing."""
    write_file(repo / "plugins/alpha/skills/demo/SKILL.md", "---\nname: alpha\n---\n\nNew.\n")
    monkeypatch.chdir(repo)
    assert main(["--base", "main", "--deferred"]) == int(ExitCode.OK)
    assert "→ deferred" in capsys.readouterr().out


@pytest.mark.slow
def test_an_unresolvable_base_is_a_usage_error(
    repo: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A typo in `--base` must not look like a clean gate."""
    monkeypatch.chdir(repo)
    assert main(["--base", "refs/heads/nope"]) == int(ExitCode.USAGE)
    assert "error: `git" in capsys.readouterr().err


@pytest.mark.slow
def test_verify_tag_asks_the_cli_about_untagged_versions(
    repo: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Before merge, the CLI answers the question the tag workflow would ask on `main`."""
    write_file(repo / "plugins/alpha/.claude-plugin/plugin.json", manifest_text("alpha", "0.1.1"))
    write_file(repo / "plugins/alpha/skills/demo/SKILL.md", "---\nname: alpha\n---\n\nNew.\n")
    stub = tmp_path / "claude-stub"
    write_file(stub, "#!/usr/bin/env bash\nexit 0\n")
    stub.chmod(stub.stat().st_mode | stat.S_IXUSR)
    monkeypatch.setenv(CLAUDE_BIN_ENV, str(stub))
    monkeypatch.chdir(repo)
    assert main(["--base", "main", "--verify-tag"]) == int(ExitCode.OK)
    assert "alpha 0.1.1 tag dry-run: would tag" in capsys.readouterr().out


@pytest.mark.slow
def test_verify_tag_reports_a_refusal(
    repo: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A version the CLI refuses fails the gate instead of failing the tag workflow later."""
    write_file(repo / "plugins/alpha/.claude-plugin/plugin.json", manifest_text("alpha", "0.1.1"))
    write_file(repo / "plugins/alpha/skills/demo/SKILL.md", "---\nname: alpha\n---\n\nNew.\n")
    stub = tmp_path / "claude-stub"
    write_file(stub, "#!/usr/bin/env bash\necho 'catalog disagrees' >&2\nexit 1\n")
    stub.chmod(stub.stat().st_mode | stat.S_IXUSR)
    monkeypatch.setenv(CLAUDE_BIN_ENV, str(stub))
    monkeypatch.chdir(repo)
    assert main(["--base", "main", "--verify-tag"]) == int(ExitCode.FINDINGS)
    out = capsys.readouterr().out
    assert "tag dry-run: refused" in out
    assert "V6 plugins/alpha: alpha--v0.1.1 was refused: catalog disagrees" in out


@pytest.mark.slow
def test_verify_tag_without_the_cli_is_a_finding(
    repo: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`--verify-tag` was asked for, so a missing CLI is reported, never skipped silently."""
    plan = build_plan(repo, base="main")
    monkeypatch.delenv(CLAUDE_BIN_ENV, raising=False)
    monkeypatch.setenv("PATH", str(tmp_path))
    lines, findings = verify_tags(repo, plan)
    assert lines == []
    assert [finding.invariant_id for finding in findings] == ["V6"]
    assert "--verify-tag needs the CLI" in findings[0].message


@pytest.mark.slow
def test_the_head_flag_classifies_a_fetched_pull_request(
    repo: Path,
    tmp_path_factory: pytest.TempPathFactory,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The CLI surface triage relies on: base checkout, head as `FETCH_HEAD`, JSON out."""
    write_file(repo / "plugins/alpha/skills/demo/SKILL.md", "---\nname: alpha\n---\n\nFixed.\n")
    write_file(repo / "plugins/alpha/.claude-plugin/plugin.json", manifest_text("alpha", "0.1.1"))
    clone = fetch_as_pull_request(repo, tmp_path_factory.mktemp("probe") / "base")
    monkeypatch.chdir(clone)
    assert main(["--base", "main", "--head", "FETCH_HEAD", "--json"]) == int(ExitCode.OK)
    payload = parse_json(capsys.readouterr().out, path=clone)
    assert is_json_object(payload)
    assert payload["label"] == "bump: patch"
    assert payload["route"] == "pr"
