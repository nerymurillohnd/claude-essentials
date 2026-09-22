"""Tests for L4 and G2: actionlint, the zizmor ignore policy, and zizmor itself all block."""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

import pytest

from scripts.lint import workflows_files
from scripts.lint.conftest import write_file
from scripts.lint.workflows_files import (
    INVARIANT,
    WORKFLOW_DIR,
    ZIZMOR_BLOCKING,
    ZIZMOR_INVARIANT,
    ZIZMOR_OFFLINE,
    check,
    check_ignore_policy,
    finding_lines,
    select,
    zizmor_summary,
)

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

VALID = """name: Demo
on:
  push:
    branches: [main]
permissions: {}
concurrency:
  group: demo
  cancel-in-progress: false
jobs:
  demo:
    name: Demo
    runs-on: ubuntu-latest
    permissions:
      contents: read # read the tree
    steps:
      - run: echo hi
"""
"""A workflow actionlint and zizmor both accept, used as the control."""

BROKEN = """name: Demo
on:
  push:
    branches: [main]
jobs:
  demo:
    runs-on: ubuntu-latest
    steps:
      - run: echo "${{ github.no_such_context }}"
"""
"""An undefined context: a workflow that only fails once it is on the runner."""


def _write_workflow(tree: Path, name: str, text: str) -> str:
    """Put a workflow in the tree and return its repository-relative path.

    Args:
        tree: The fixture tree.
        name: The file name.
        text: The workflow.

    Returns:
        The repository-relative path.
    """
    rel = f"{WORKFLOW_DIR}/{name}"
    write_file(tree / rel, text)
    return rel


def test_select_keeps_both_yaml_spellings() -> None:
    """A workflow renamed to `.yaml` must not become silently unchecked."""
    assert select([f"{WORKFLOW_DIR}/a.yml", f"{WORKFLOW_DIR}/b.yaml", "docs/c.yml"]) == [
        f"{WORKFLOW_DIR}/a.yml",
        f"{WORKFLOW_DIR}/b.yaml",
    ]


def test_zizmor_blocks() -> None:
    """The step-7 rewrite left zero findings; turning this off again must be a visible edit."""
    assert ZIZMOR_BLOCKING is True


def test_every_finding_is_named_with_its_location() -> None:
    """A refused commit has to say which audit fired and where, not only a count."""
    output = (
        "help[anonymous-definition]: workflow or action definition without a name\n"
        "  --> .github/workflows/a.yml:3:3\n"
        "   |\n"
        "warning[artipacked]: credential persistence through GitHub Actions artifacts\n"
        " --> .github/workflows/b.yml:9:9\n"
    )
    first, second = finding_lines(output)
    assert first.startswith(".github/workflows/a.yml:3:3: help[anonymous-definition]:")
    assert second.startswith(".github/workflows/b.yml:9:9: warning[artipacked]:")


def test_an_ignore_of_another_rule_is_refused(tree: Path) -> None:
    """Exactly one suppression is policy; a second one would be a silent exception."""
    rel = _write_workflow(tree, "a.yml", "# zizmor: ignore[artipacked] ADR-0004\n")
    findings = check_ignore_policy(tree, [rel])
    assert [finding.invariant_id for finding in findings] == [INVARIANT]
    assert "only `dangerous-triggers`" in findings[0].message


def test_the_allowed_ignore_still_needs_its_citation(tree: Path) -> None:
    """A suppression without the decision behind it is indistinguishable from a shortcut."""
    rel = _write_workflow(tree, "a.yml", "# zizmor: ignore[dangerous-triggers]\n")
    findings = check_ignore_policy(tree, [rel])
    assert "cites no ADR-0004" in findings[0].message


def test_the_recorded_ignore_is_accepted(tree: Path) -> None:
    """The triage workflow's `pull_request_target` is the one case ADR-0004 decided."""
    text = "on: # zizmor: ignore[dangerous-triggers] head is never checked out, ADR-0004\n"
    rel = _write_workflow(tree, "a.yml", text)
    assert check_ignore_policy(tree, [rel]) == []


@pytest.mark.slow
def test_actionlint_reports_an_undefined_context(tree: Path) -> None:
    """The defect L4 exists for: a workflow that parses and still fails on the runner."""
    rel = _write_workflow(tree, "broken.yml", BROKEN)
    findings = [finding for finding in check(tree, [rel]) if finding.invariant_id == INVARIANT]
    assert findings
    assert all(finding.path == rel for finding in findings)


@pytest.mark.slow
def test_a_valid_workflow_is_clean(tree: Path) -> None:
    """The control: a workflow with minimal, documented grants and named jobs passes both."""
    rel = _write_workflow(tree, "ok.yml", VALID)
    assert check(tree, [rel]) == []
    assert "No findings" in zizmor_summary(tree, [rel])


@pytest.mark.slow
def test_a_zizmor_finding_fails_the_gate(tree: Path) -> None:
    """An unnamed job with an undocumented grant is what the auditor persona exists to catch."""
    rel = _write_workflow(tree, "loose.yml", BROKEN.replace("jobs:", "permissions: {}\njobs:"))
    findings = [f for f in check(tree, [rel]) if f.invariant_id == ZIZMOR_INVARIANT]
    assert findings
    assert {finding.severity for finding in findings} == {"error"}
    assert any("anonymous-definition" in finding.message for finding in findings)


def test_nothing_runs_without_a_workflow(tree: Path) -> None:
    """An edit to a plugin must not pay for two audits of files it never touched."""
    assert check(tree, ["README.md"]) == []


def test_zizmor_runs_offline_everywhere_including_ci() -> None:
    """The offline decision is pinned: flipping it back needs a tagged or vendored action."""
    assert ZIZMOR_OFFLINE


def test_the_zizmor_command_line_carries_offline(
    tree: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The constant is only a promise; this checks the argv zizmor actually receives.

    The fixture's `.venv/bin/zizmor` is a symlink to the real binary, so the test never
    writes to it; `run` is replaced and nothing is executed.
    """
    seen: list[list[str]] = []

    def fake_run(
        _executable: Path, args: Sequence[str], *, cwd: Path
    ) -> subprocess.CompletedProcess[str]:
        del cwd
        seen.append(list(args))
        return subprocess.CompletedProcess(list(args), 0, "No findings to report.\n", "")

    monkeypatch.setattr(workflows_files, "run", fake_run)
    rel = _write_workflow(tree, "ok.yml", VALID)
    assert workflows_files.zizmor_findings(tree, [rel]) == []
    assert seen
    assert seen[0][:4] == ["--persona=auditor", "--format", "plain", "--offline"]
