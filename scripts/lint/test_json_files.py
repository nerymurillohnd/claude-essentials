"""Tests for L2: the canonical form, the one exclusion list, and the JSONC carve-out."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from scripts.common.jsontext import canonical_json
from scripts.lint.conftest import write_file
from scripts.lint.json_files import (
    INVARIANT,
    JSON_EXCLUDED,
    check,
    fix,
    is_excluded,
    is_jsonc,
    select,
)

if TYPE_CHECKING:
    from pathlib import Path

COMPACT = '{"name":"alpha","tags":["one","two"]}'
"""A document written the way a person or another tool would, not the way this repository does."""


def test_the_canonical_form_expands_arrays_and_ends_in_a_newline() -> None:
    """The form is the one `make generate` writes, so a generator can never drift from it."""
    assert canonical_json({"tags": ["one"]}) == '{\n  "tags": [\n    "one"\n  ]\n}\n'


def test_a_compact_document_is_reported(tmp_path: Path) -> None:
    """Two spellings of the same data would make every later diff unreadable."""
    write_file(tmp_path / "a.json", COMPACT)
    findings = check(tmp_path, ["a.json"])
    assert [(finding.invariant_id, finding.path) for finding in findings] == [(INVARIANT, "a.json")]


def test_a_canonical_document_passes(tmp_path: Path) -> None:
    """The control: the gate accepts exactly what its own writer produces."""
    write_file(tmp_path / "a.json", canonical_json({"name": "alpha", "tags": ["one", "two"]}))
    assert check(tmp_path, ["a.json"]) == []


def test_broken_json_is_reported_rather_than_raised(tmp_path: Path) -> None:
    """A gate that crashes on one bad file tells the maintainer nothing about the rest."""
    write_file(tmp_path / "a.json", "{nope}\n")
    findings = check(tmp_path, ["a.json"])
    assert len(findings) == 1
    assert "is not valid JSON" in findings[0].message


def test_fix_writes_the_canonical_form(tmp_path: Path) -> None:
    """After the writer runs, the checker has nothing left to report."""
    path = tmp_path / "a.json"
    write_file(path, COMPACT)
    assert fix(tmp_path, ["a.json"]) == ["a.json"]
    assert check(tmp_path, ["a.json"]) == []


def test_a_dry_run_reports_without_writing(tmp_path: Path) -> None:
    """The churn of a formatting pass is measured before it is committed."""
    path = tmp_path / "a.json"
    write_file(path, COMPACT)
    assert fix(tmp_path, ["a.json"], dry_run=True) == ["a.json"]
    assert path.read_text(encoding="utf-8") == COMPACT


def test_fix_leaves_broken_json_alone(tmp_path: Path) -> None:
    """Guessing at what unparseable text meant would destroy it, not format it."""
    path = tmp_path / "a.json"
    write_file(path, "{nope}\n")
    assert fix(tmp_path, ["a.json"]) == []
    assert path.read_text(encoding="utf-8") == "{nope}\n"


@pytest.mark.parametrize("rel", ["knip.jsonc", "tsconfig.json", "packages/tsconfig.build.json"])
def test_json_with_comments_is_never_parsed(rel: str) -> None:
    """A strict parser would call every commented file broken, which is not a defect."""
    assert is_jsonc(rel)


@pytest.mark.parametrize("rel", JSON_EXCLUDED)
def test_every_excluded_pattern_excludes_itself(rel: str) -> None:
    """The exclusion list is read as patterns, so a literal entry has to match literally."""
    assert is_excluded(rel.replace("*", "x"))


def test_the_vendored_schemas_are_excluded() -> None:
    """X2 pins those files byte for byte; reformatting them would break the hash."""
    assert is_excluded("schemas/github/issue-forms.schema.json")


def test_an_ordinary_manifest_is_not_excluded() -> None:
    """The exclusion list is closed: everything this repository writes is held to the form."""
    assert not is_excluded("plugins/alpha/.claude-plugin/plugin.json")


def test_select_drops_everything_the_gate_does_not_own() -> None:
    """One candidate list reaches every checker; each keeps only what it answers for."""
    assert select(["a.json", "b.md", "knip.jsonc", ".mcp.json"]) == ["a.json"]
