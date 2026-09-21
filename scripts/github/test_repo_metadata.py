"""Tests for the cross-file pins: the CLI version, the tool pins, the SHAs, the pipeline."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from scripts.common.plugins import repo_root
from scripts.github.repo_metadata import (
    GATE_WORKFLOW,
    TAG_WORKFLOW,
    WORKFLOWS_DIR,
    advertised_minimum,
    check_claude_code_versions,
    check_pipeline_invocation,
    check_tool_pins,
    check_workflow_pins,
    collect,
    locked_version,
    version_tuple,
    workflow_document,
    workflow_env,
    workflow_triggers,
)
from scripts.marketplace.conftest import write_file

if TYPE_CHECKING:
    from pathlib import Path

PINNED_STEP = """name: CI
on:
  push:
    branches: [main]
env:
  CLAUDE_CODE_VERSION: "2.1.276"
jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
      - run: make check
"""
"""A workflow that satisfies every pin rule."""


def workflow(root: Path, name: str, text: str) -> None:
    """Write a workflow into a fixture tree.

    Args:
        root: The fixture repository root.
        name: The workflow file name.
        text: Its contents.
    """
    write_file(root / WORKFLOWS_DIR / name, text)


@pytest.mark.parametrize(
    ("text", "expected"),
    [("0.11.0", (0, 11, 0)), ("3.12", (3, 12)), ("0.10 (0.11 later)", (0, 10)), ("none", ())],
)
def test_version_tuple_reads_the_first_dotted_number(text: str, expected: tuple[int, ...]) -> None:
    """A Requirements cell may carry a parenthetical; the minimum is what comes first."""
    assert version_tuple(text) == expected


def test_the_on_key_survives_yaml_one_point_one(tmp_path: Path) -> None:
    """PyYAML resolves the bare key `on` to `True`, which would hide every trigger."""
    workflow(tmp_path, "ci.yml", PINNED_STEP)
    document = workflow_document(tmp_path / WORKFLOWS_DIR / "ci.yml")
    assert "on" in document
    assert workflow_triggers(document) == {"push"}


def test_env_is_collected_from_every_level(tmp_path: Path) -> None:
    """A workflow may set the CLI version at the top or inside a job."""
    workflow(tmp_path, "ci.yml", PINNED_STEP)
    env = workflow_env(workflow_document(tmp_path / WORKFLOWS_DIR / "ci.yml"))
    assert env["CLAUDE_CODE_VERSION"] == "2.1.276"


@pytest.mark.slow
def test_the_real_workflows_agree_on_the_cli_version() -> None:
    """One pinned version across the repository, as it stands."""
    assert check_claude_code_versions(repo_root()) == []


def test_a_disagreeing_cli_version_is_reported(tmp_path: Path) -> None:
    """The gate and the tag workflow would then validate against different CLIs."""
    workflow(tmp_path, GATE_WORKFLOW, PINNED_STEP)
    workflow(tmp_path, TAG_WORKFLOW, PINNED_STEP.replace("2.1.276", "2.1.200"))
    findings = check_claude_code_versions(tmp_path)
    assert [finding.invariant_id for finding in findings] == ["G2"]
    assert "differs across workflows" in findings[0].message


def test_a_floating_cli_version_is_refused_on_a_required_check(tmp_path: Path) -> None:
    """A required check that floats can go red with no commit behind it."""
    workflow(tmp_path, GATE_WORKFLOW, PINNED_STEP.replace('"2.1.276"', "latest"))
    assert [f.invariant_id for f in check_claude_code_versions(tmp_path)] == ["G2"]


def test_a_floating_cli_version_is_allowed_on_a_nightly(tmp_path: Path) -> None:
    """The nightly exists precisely to find upstream drift."""
    nightly = PINNED_STEP.replace('"2.1.276"', "latest").replace(
        "on:\n  push:\n    branches: [main]\n", "on:\n  schedule:\n    - cron: '0 3 * * *'\n"
    )
    workflow(tmp_path, "nightly.yml", nightly)
    assert check_claude_code_versions(tmp_path) == []


@pytest.mark.slow
def test_the_real_tool_pins_agree() -> None:
    """Ruff, Python, ShellCheck, shfmt and the CLI, on the repository as it stands."""
    assert check_tool_pins(repo_root()) == []


@pytest.mark.slow
def test_the_lock_resolves_the_pinned_ruff() -> None:
    """The `required-version` floor is met by what uv actually installs (G3)."""
    assert locked_version(repo_root(), "ruff") is not None


def test_a_lock_below_the_required_version_is_reported(tmp_path: Path) -> None:
    """A Dependabot bump of the lock must never drop below the declared floor."""
    write_file(
        tmp_path / "pyproject.toml",
        '[project]\nrequires-python = ">=3.14"\n\n[tool.ruff]\nrequired-version = ">=0.16.7"\n',
    )
    write_file(tmp_path / ".python-version", "3.14\n")
    write_file(tmp_path / "uv.lock", '[[package]]\nname = "ruff"\nversion = "0.16.1"\n')
    findings = check_tool_pins(tmp_path)
    assert [finding.invariant_id for finding in findings] == ["G3"]
    assert "below the `required-version` floor" in findings[0].message


def test_a_python_version_that_is_not_the_floor_is_reported(tmp_path: Path) -> None:
    """Uv would install an interpreter the project does not declare."""
    write_file(tmp_path / "pyproject.toml", '[project]\nrequires-python = ">=3.14"\n')
    write_file(tmp_path / ".python-version", "3.13\n")
    findings = check_tool_pins(tmp_path)
    assert [finding.invariant_id for finding in findings] == ["G3"]


@pytest.mark.slow
def test_the_advertised_shellcheck_minimum_is_read_from_a_readme() -> None:
    """A plugin README's Requirements table is a contract, not documentation."""
    assert advertised_minimum(repo_root(), "ShellCheck") >= (0, 10)


def test_ci_installing_less_than_a_readme_promises_is_reported(tmp_path: Path) -> None:
    """A promise nothing keeps: the suites would run under a tool the README rules out."""
    write_file(
        tmp_path / "plugins" / "alpha" / ".claude-plugin" / "plugin.json",
        '{"name": "alpha"}',
    )
    write_file(
        tmp_path / "plugins" / "alpha" / "README.md",
        "## Requirements\n\n| Requirement | Minimum |\n| --- | --- |\n| shfmt | 3.12 |\n",
    )
    workflow(
        tmp_path,
        GATE_WORKFLOW,
        PINNED_STEP.replace(
            "jobs:\n  check:\n", 'jobs:\n  check:\n    env:\n      SHFMT_VERSION: "3.10"\n'
        ),
    )
    findings = check_tool_pins(tmp_path)
    assert [finding.invariant_id for finding in findings] == ["G3"]
    assert "below the 3.12" in findings[0].message


@pytest.mark.slow
def test_the_real_workflow_pins_are_full_shas() -> None:
    """DEBT-0004: every third-party action is pinned to a commit with its tag noted."""
    assert check_workflow_pins(repo_root()) == []


def test_a_tag_reference_is_reported(tmp_path: Path) -> None:
    """A tag can be moved by the action's owner; a commit cannot."""
    workflow(
        tmp_path,
        "ci.yml",
        PINNED_STEP.replace("@3d3c42e5" + "aac5ba805825da76410c181273ba90b1", "@v7"),
    )
    findings = check_workflow_pins(tmp_path)
    assert [finding.invariant_id for finding in findings] == ["G2"]
    assert "40-hex commit SHA" in findings[0].message


def test_a_pinned_sha_without_its_tag_is_reported(tmp_path: Path) -> None:
    """Without the comment nobody can tell which release a SHA is, Dependabot included."""
    workflow(tmp_path, "ci.yml", PINNED_STEP.replace(" # v7.0.1", ""))
    findings = check_workflow_pins(tmp_path)
    assert "carries no `# vX.Y.Z`" in findings[0].message


def test_a_local_action_needs_no_sha(tmp_path: Path) -> None:
    """`uses: ./.github/actions/x` is this repository's own code."""
    workflow(
        tmp_path,
        "ci.yml",
        PINNED_STEP.replace(
            "uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1",
            "uses: ./.github/actions/local",
        ),
    )
    assert check_workflow_pins(tmp_path) == []


@pytest.mark.slow
def test_the_pipeline_check_is_advisory_on_this_tree() -> None:
    """`ci.yml` still calls npm; step 7 rewires it and turns this into an error."""
    findings = check_pipeline_invocation(repo_root())
    assert [finding.severity for finding in findings] == ["warning"]
    assert "advisory until step 7" in findings[0].message


def test_the_pipeline_check_passes_on_a_make_driven_workflow(tmp_path: Path) -> None:
    """What step 7 makes true."""
    workflow(tmp_path, GATE_WORKFLOW, PINNED_STEP)
    assert check_pipeline_invocation(tmp_path) == []


@pytest.mark.slow
def test_collect_on_this_tree_reports_only_the_advisory_warning() -> None:
    """Nothing here fails the gate today."""
    findings = collect(repo_root())
    assert [finding.severity for finding in findings] == ["warning"]
