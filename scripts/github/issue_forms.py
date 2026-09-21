"""The issue forms: schema-valid, label-consistent, and carrying the generated dropdown (G1).

GitHub publishes no schema for issue forms, so `schemas/github/` vendors SchemaStore's two,
unmodified except for a `$comment` naming the source. This module is their only consumer: it
parses each form with PyYAML into untyped data, narrows it to plain JSON values, and hands
that to `jsonschema` with the draft the schema itself declares.

Three checks sit on top of the schema, because a form can be perfectly valid and still be
wrong for this repository: the **Affected plugin** dropdown must list exactly the plugins
that ship, every `labels:` entry must exist in the taxonomy, and a form that carries the
dropdown must carry it in the generated shape `generate_issue_forms` writes.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Final

from jsonschema.validators import validator_for
import yaml

from scripts.common.errors import Finding, MaintainerError, UnexpectedShapeError
from scripts.common.jsontext import is_json_array, is_json_object
from scripts.common.plugins import load_json, plugin_ids
from scripts.github.labels import desired_labels

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence
    from pathlib import Path

type JsonValue = str | int | float | bool | Mapping[str, JsonValue] | Sequence[JsonValue] | None
"""Exactly the shape `jsonschema` accepts as a schema and as an instance."""

GITHUB_SCHEMAS_DIR: Final = "schemas/github"
"""The one place schema paths are spelled; step 9 of the migration moves it to
`.github/schemas` by changing this constant and nothing else."""

ISSUE_TEMPLATE_DIR: Final = ".github/ISSUE_TEMPLATE"
"""Where GitHub reads the forms from."""

FORMS_SCHEMA: Final = "issue-forms.schema.json"
CONFIG_SCHEMA: Final = "issue-config.schema.json"
"""The two vendored schemas, one per kind of file in that directory."""

CONFIG_FILE: Final = "config.yml"
"""The chooser configuration, which is not an issue form."""

PLUGIN_DROPDOWN_ID: Final = "plugin"
"""The `id` of the **Affected plugin** dropdown the generator owns."""

CATALOG_OPTION: Final = "Marketplace catalog / installation"
"""The first option: problems with adding the marketplace or installing anything."""

UNSURE_OPTION: Final = "Not sure"
"""The last option, so a reporter is never forced to guess."""

_safe_load: Callable[[str], object] = yaml.safe_load
"""`yaml.safe_load` is annotated `-> Any`; this alias is the one place that becomes `object`."""


def as_json_value(value: object, *, path: Path) -> JsonValue:
    """Narrow parsed YAML or JSON into the plain JSON shape `jsonschema` accepts.

    Args:
        value: The parsed value.
        path: The file it came from, named in the error.

    Returns:
        The same data, typed.

    Raises:
        UnexpectedShapeError: If the document carries a value JSON has no equivalent for,
            such as a YAML date or a set.
    """
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    if is_json_object(value):
        return {key: as_json_value(item, path=path) for key, item in value.items()}
    if is_json_array(value):
        return [as_json_value(item, path=path) for item in value]
    raise UnexpectedShapeError(path, "a JSON value", value)


def load_yaml(path: Path) -> JsonValue:
    """Parse a YAML file into plain JSON values.

    Args:
        path: The file to read.

    Returns:
        The parsed document.

    Raises:
        UnexpectedShapeError: If the document is not representable as JSON.
    """
    return as_json_value(_safe_load(path.read_text(encoding="utf-8")), path=path)


def load_schema(root: Path, name: str) -> Mapping[str, JsonValue]:
    """Read one vendored schema.

    Args:
        root: The repository root.
        name: The schema file name.

    Returns:
        The parsed schema.

    Raises:
        UnexpectedShapeError: If the schema is not a JSON object.
    """
    path = root / GITHUB_SCHEMAS_DIR / name
    schema = as_json_value(load_json(path), path=path)
    if not isinstance(schema, Mapping):
        raise UnexpectedShapeError(path, "an object", schema)
    return schema


def form_paths(root: Path) -> list[Path]:
    """List the issue forms, excluding the chooser configuration.

    Args:
        root: The repository root.

    Returns:
        The form files, sorted by name.
    """
    directory = root / ISSUE_TEMPLATE_DIR
    if not directory.is_dir():
        return []
    return sorted(path for path in directory.glob("*.yml") if path.name != CONFIG_FILE)


def schema_findings(
    instance: JsonValue, schema: Mapping[str, JsonValue], *, rel: str
) -> list[Finding]:
    """Validate one document against one schema, using the draft the schema declares.

    Args:
        instance: The parsed document.
        schema: The parsed schema.
        rel: The document's repository-relative path, named in each finding.

    Returns:
        One finding per schema violation.
    """
    validator_class = validator_for(schema)
    validator = validator_class(schema)
    return [
        Finding("G1", rel, f"{'/'.join(str(part) for part in error.path)}: {error.message}")
        for error in validator.iter_errors(instance)
    ]


def expected_options(root: Path) -> list[str]:
    """Return the **Affected plugin** dropdown exactly as the generator writes it.

    Args:
        root: The repository root.

    Returns:
        The catalog option, every plugin that ships, and the fallback.
    """
    return [CATALOG_OPTION, *plugin_ids(root), UNSURE_OPTION]


def dropdown_options(document: JsonValue) -> list[str] | None:
    """Return the options of the **Affected plugin** dropdown, if the form carries one.

    Args:
        document: The parsed form.

    Returns:
        The option strings, or None when this form has no such dropdown.
    """
    if not is_json_object(document):
        return None
    body = document.get("body")
    if not is_json_array(body):
        return None
    for item in body:
        if not is_json_object(item):
            continue
        if item.get("id") != PLUGIN_DROPDOWN_ID or item.get("type") != "dropdown":
            continue
        attributes = item.get("attributes")
        if not is_json_object(attributes):
            continue
        options = attributes.get("options")
        if is_json_array(options):
            return [option for option in options if isinstance(option, str)]
    return None


def form_labels(document: JsonValue) -> list[str]:
    """Return the labels a form applies when an issue is opened from it.

    Args:
        document: The parsed form.

    Returns:
        The declared label names; empty when the form declares none.
    """
    if not is_json_object(document):
        return []
    labels = document.get("labels")
    if not is_json_array(labels):
        return []
    return [label for label in labels if isinstance(label, str)]


def validate_forms(root: Path) -> list[Finding]:
    """Check every issue form and the chooser configuration (G1).

    Args:
        root: The repository root.

    Returns:
        One finding per schema violation, stale dropdown or undeclared label.
    """
    try:
        return _collect(root)
    except MaintainerError as error:
        return [Finding("G1", ISSUE_TEMPLATE_DIR, str(error))]
    except yaml.YAMLError as error:
        return [Finding("G1", ISSUE_TEMPLATE_DIR, f"a form is not valid YAML: {error}")]


def _collect(root: Path) -> list[Finding]:
    """Run every form check; the raising half of `validate_forms`.

    Args:
        root: The repository root.

    Returns:
        One finding per rule broken.

    Raises:
        MaintainerError: If a file cannot be read or has an unusable shape.
    """
    findings: list[Finding] = []
    forms_schema = load_schema(root, FORMS_SCHEMA)
    known_labels = {label.name for label in desired_labels(root)}
    expected = expected_options(root)
    for path in form_paths(root):
        rel = f"{ISSUE_TEMPLATE_DIR}/{path.name}"
        document = load_yaml(path)
        findings.extend(schema_findings(document, forms_schema, rel=rel))
        options = dropdown_options(document)
        if options is not None and options != expected:
            findings.append(
                Finding(
                    "G1",
                    rel,
                    f"the `{PLUGIN_DROPDOWN_ID}` dropdown lists {options}; run `make generate`",
                ),
            )
        findings.extend(
            Finding("G1", rel, f"applies label {name!r}, which the taxonomy does not declare")
            for name in form_labels(document)
            if name not in known_labels
        )
    config = root / ISSUE_TEMPLATE_DIR / CONFIG_FILE
    if config.is_file():
        findings.extend(
            schema_findings(
                load_yaml(config),
                load_schema(root, CONFIG_SCHEMA),
                rel=f"{ISSUE_TEMPLATE_DIR}/{CONFIG_FILE}",
            ),
        )
    return findings
