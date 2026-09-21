"""W1: metadata purity, declared phases, compilation and a stub-runtime run."""

from __future__ import annotations

from typing import TYPE_CHECKING

from scripts.common.plugins import repo_root
from scripts.plugin_validation.workflows import (
    body_source,
    check_meta,
    check_workflow,
    meta_source,
    used_phases,
)

if TYPE_CHECKING:
    from pathlib import Path

SHIPPED = "plugins/verify-completion/workflows/deep-verify.js"


def test_the_shipped_workflow_runs_against_the_stub_runtime() -> None:
    """The one workflow this marketplace publishes compiles and orchestrates end to end."""
    assert check_workflow(repo_root(), SHIPPED) == []


def test_meta_is_extracted_with_balanced_braces() -> None:
    """A brace inside a description must not end the literal."""
    source = 'export const meta = { name: "a", note: "}" };\nreturn 1;\n'
    assert meta_source(source) == '{ name: "a", note: "}" }'


def test_the_body_excludes_the_export_statement() -> None:
    """`export` cannot appear in a function body, so it is removed before compiling."""
    source = 'export const meta = { name: "a" };\nreturn 1;\n'
    meta = meta_source(source)
    assert meta is not None
    assert "export" not in body_source(source, meta)


def test_phases_are_read_from_both_forms() -> None:
    """A phase is named either by a `phase("…")` call or by a `phase:` option."""
    body = 'phase("One");\nawait agent("x", { phase: "Two" });\n'
    assert used_phases(body) == ["One", "Two"]


def test_a_template_literal_in_meta_is_refused() -> None:
    """A template literal can interpolate, so it is not pure data."""
    findings, _ = check_meta("w.js", "export const meta = { name: `a${b}` };\n")
    assert [finding.invariant_id for finding in findings] == ["W1"]


def test_a_call_in_meta_is_refused() -> None:
    """Reading metadata must never execute anything."""
    findings, _ = check_meta("w.js", 'export const meta = { name: String("a") };\n')
    assert [finding.invariant_id for finding in findings] == ["W1"]


def test_a_literal_meta_yields_its_phase_titles() -> None:
    """The declared titles are what an undeclared `phase()` is compared against."""
    findings, titles = check_meta("w.js", 'export const meta = { phases: [{ title: "A" }] };\n')
    assert findings == []
    assert titles == ["A"]


def test_a_workflow_without_meta_is_reported(tmp_path: Path) -> None:
    """A workflow with no metadata cannot be listed or phased by the runtime.

    Args:
        tmp_path: pytest's per-test directory.
    """
    path = tmp_path / "w.js"
    _ = path.write_text("return 1;\n", encoding="utf-8")
    assert [finding.invariant_id for finding in check_workflow(tmp_path, "w.js")] == ["W1"]
