"""Tests for L4: actionlint blocks, the zizmor ignore policy is enforced, zizmor advises."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from scripts.lint.conftest import write_file
from scripts.lint.workflows_files import (
    ADVISORY_INVARIANT,
    ADVISORY_PREFIX,
    INVARIANT,
    WORKFLOW_DIR,
    ZIZMOR_BLOCKING,
    check,
    check_ignore_policy,
    select,
    zizmor_summary,
)

if TYPE_CHECKING:
    from pathlib import Path

VALID = """name: Demo
on:
  push:
    branches: [main]
permissions: {}
jobs:
  demo:
    name: Demo
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - run: echo hi
"""
"""A workflow actionlint accepts, used as the control."""

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


def test_zizmor_stays_advisory_until_the_workflows_are_rewritten() -> None:
    """Today's files carry findings the step-7 rewrite addresses in one piece."""
    assert ZIZMOR_BLOCKING is False


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
def test_a_valid_workflow_produces_only_the_advisory(tree: Path) -> None:
    """A clean tree still reports the zizmor count, because reporting is the point of it."""
    rel = _write_workflow(tree, "ok.yml", VALID)
    findings = check(tree, [rel])
    assert [finding.invariant_id for finding in findings] == [ADVISORY_INVARIANT]
    assert findings[0].severity == "warning"
    assert findings[0].message.startswith(ADVISORY_PREFIX)


@pytest.mark.slow
def test_the_advisory_carries_zizmor_s_own_count(tree: Path) -> None:
    """The summary is what gate output shows, so it has to be zizmor's line, not a paraphrase."""
    rel = _write_workflow(tree, "ok.yml", VALID)
    summary = zizmor_summary(tree, [rel])
    assert "finding" in summary


def test_nothing_runs_without_a_workflow(tree: Path) -> None:
    """An edit to a plugin must not pay for two audits of files it never touched."""
    assert check(tree, ["README.md"]) == []
