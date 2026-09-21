"""Tests for the issue forms: the real files against the real vendored schemas (G1)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from scripts.common.plugins import plugin_ids, repo_root
from scripts.github.issue_forms import (
    CATALOG_OPTION,
    CONFIG_FILE,
    CONFIG_SCHEMA,
    FORMS_SCHEMA,
    GITHUB_SCHEMAS_DIR,
    ISSUE_TEMPLATE_DIR,
    UNSURE_OPTION,
    JsonValue,
    dropdown_options,
    expected_options,
    form_labels,
    form_paths,
    load_schema,
    load_yaml,
    schema_findings,
    validate_forms,
)

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.slow
def test_the_real_forms_pass_every_check() -> None:
    """Schema, dropdown and labels, on the repository as it stands."""
    assert validate_forms(repo_root()) == []


@pytest.mark.slow
def test_every_form_is_found() -> None:
    """The chooser configuration is not a form and is validated separately."""
    names = {path.name for path in form_paths(repo_root())}
    assert CONFIG_FILE not in names
    assert names


@pytest.mark.slow
def test_both_vendored_schemas_load() -> None:
    """They are the only consumers of `schemas/github/`, through one constant."""
    root = repo_root()
    assert (root / GITHUB_SCHEMAS_DIR).is_dir()
    assert load_schema(root, FORMS_SCHEMA)
    assert load_schema(root, CONFIG_SCHEMA)


@pytest.mark.slow
def test_the_expected_dropdown_brackets_the_plugin_list() -> None:
    """A reporter can always pick the catalog or say they are unsure."""
    root = repo_root()
    assert expected_options(root) == [CATALOG_OPTION, *plugin_ids(root), UNSURE_OPTION]


@pytest.mark.slow
def test_every_form_that_carries_the_dropdown_carries_the_generated_list() -> None:
    """Two forms carry it today; both must agree with `plugins/`."""
    root = repo_root()
    carried = [
        options
        for path in form_paths(root)
        if (options := dropdown_options(load_yaml(path))) is not None
    ]
    assert carried
    assert all(options == expected_options(root) for options in carried)


@pytest.mark.slow
def test_every_form_label_exists_in_the_taxonomy() -> None:
    """A form that applies an undeclared label creates drift no sync can fix."""
    root = repo_root()
    assert all(form_labels(load_yaml(path)) for path in form_paths(root))


@pytest.mark.slow
def test_a_stale_dropdown_is_reported(tmp_path: Path) -> None:
    """The defect the generator exists to prevent."""
    root = repo_root()
    directory = tmp_path / ISSUE_TEMPLATE_DIR
    directory.mkdir(parents=True)
    source = form_paths(root)[0]
    text = source.read_text(encoding="utf-8").replace(CATALOG_OPTION, "Something else")
    _ = (directory / source.name).write_text(text, encoding="utf-8")
    document = load_yaml(directory / source.name)
    assert dropdown_options(document) != expected_options(root)


def test_a_schema_violation_is_reported() -> None:
    """The vendored schema is what decides, not a rule written here."""
    schema = {"type": "object", "required": ["name"]}
    findings = schema_findings({}, schema, rel="x.yml")
    assert [finding.invariant_id for finding in findings] == ["G1"]


def test_a_form_without_a_dropdown_returns_none() -> None:
    """The documentation form carries no plugin dropdown and owes nothing."""
    assert dropdown_options({"body": [{"type": "input", "id": "location"}]}) is None


@pytest.mark.parametrize("document", [None, "text", [], {"body": "text"}])
def test_dropdown_options_tolerates_a_broken_document(document: JsonValue) -> None:
    """The schema check reports the shape; this helper must not raise on it."""
    assert dropdown_options(document) is None
