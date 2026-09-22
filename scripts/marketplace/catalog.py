"""What a catalog entry contains, the field rules it obeys, and the catalog's own top level.

`.claude-plugin/marketplace.json` is the file Claude Code reads when a user runs
`/plugin marketplace add`. Its `plugins` array is generated from the manifests on disk, so
this module owns two things at once: the shape of one entry (`catalog_entry`) and the rules
that shape must satisfy (M2, M3, M6, M9, M10). `generate_marketplace` writes the array and
`validate_marketplace` checks it; both read their answer from here, so the generator can
never emit something the validator would refuse.

`MARKETPLACE_CATEGORIES` is transcribed from
`schemas/plugin.schema.json#/definitions/marketplaceCategory`, read 2026-09-21. That schema
is deleted at step 9 of the migration, which makes this constant the single home of the
allowed categories; a new category is added here and nowhere else.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Final

from scripts.common.errors import Finding, MaintainerError, UnexpectedShapeError
from scripts.common.jsontext import is_json_array
from scripts.common.plugins import (
    MANIFEST_RELATIVE_PATH,
    PLUGINS_DIRNAME,
    as_mapping,
    as_str,
    load_json,
    plugin_ids,
)
from scripts.versioning.version_plan import MARKETPLACE_PATH, read_renames

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

MARKETPLACE_CATEGORIES: Final[tuple[str, ...]] = (
    "automation",
    "database",
    "deployment",
    "design",
    "development",
    "learning",
    "monitoring",
    "productivity",
    "security",
    "testing",
)
"""The one list of catalog categories this marketplace allows (M2).

A curated subset of the categories the official Anthropic marketplace
(`anthropics/claude-plugins-official`) uses: `location`, `math` and `migration` are left out
as outside this marketplace's scope.
"""

PLUGIN_NAME_RE: Final = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
"""Kebab-case, no leading, trailing or doubled hyphen (M6)."""

MAX_PLUGIN_NAME_LENGTH: Final = 42
"""So the derived GitHub label `plugin: <name>` stays inside GitHub's 50-character limit."""

TAG_RE: Final = PLUGIN_NAME_RE
"""Tags follow the same kebab-case grammar as a plugin name (M3)."""

MIN_TAGS: Final = 1
MAX_TAGS: Final = 8
"""An entry carries between one and eight unique tags (M3)."""

CATALOG_ENTRY_KEYS: Final = (
    "name",
    "source",
    "description",
    "category",
    "tags",
    "author",
    "license",
)
"""Exactly the keys of one entry, in the order they are written.

`author` and `license` are copied from the manifest so the catalog shows them before anyone
installs. `version` is deliberately absent: the catalog never pins a version, so an entry can
never go stale against the manifest it describes (M8).
"""

SCHEMA_KEY: Final = "$schema"
"""An editor hint, never a field Claude Code reads."""

ROOT_README: Final = "README.md"
"""Where the catalog row of every shipping plugin lives (M9)."""


def plugin_source(plugin_id: str) -> str:
    """Return the `source` a catalog entry carries for a plugin in this repository.

    Args:
        plugin_id: The plugin directory name.

    Returns:
        The relative path Claude Code resolves the plugin from.
    """
    return f"./{PLUGINS_DIRNAME}/{plugin_id}"


def manifest_path(root: Path, plugin_id: str) -> Path:
    """Return the absolute path of a plugin's manifest.

    Args:
        root: The repository root.
        plugin_id: The plugin directory name.

    Returns:
        The path of `plugins/<id>/.claude-plugin/plugin.json`.
    """
    return root / PLUGINS_DIRNAME / plugin_id / MANIFEST_RELATIVE_PATH


def manifest_rel(plugin_id: str) -> str:
    """Return the repository-relative path a finding points at.

    Args:
        plugin_id: The plugin directory name.

    Returns:
        The path as it is printed in gate output.
    """
    return f"{PLUGINS_DIRNAME}/{plugin_id}/{MANIFEST_RELATIVE_PATH.as_posix()}"


def as_str_list(value: object, *, path: Path) -> list[str]:
    """Narrow a parsed JSON value to a list of strings.

    Args:
        value: The parsed value.
        path: The file it came from, named in the error.

    Returns:
        The same data as a `list[str]`.

    Raises:
        UnexpectedShapeError: If the value is not a list, or an element is not a string.
    """
    if not is_json_array(value):
        raise UnexpectedShapeError(path, "an array", value)
    return [as_str(item, path=path) for item in value]


def marketplace_metadata(manifest: object, *, path: Path) -> dict[str, object]:
    """Return a manifest's `metadata.marketplace` object.

    Args:
        manifest: The parsed `plugin.json`.
        path: The file it came from, named in the error.

    Returns:
        The catalog half of the manifest; an empty object when either key is absent.

    Raises:
        UnexpectedShapeError: If `metadata` or `metadata.marketplace` is not an object.
    """
    document = as_mapping(manifest, path=path)
    metadata = document.get("metadata")
    if metadata is None:
        return {}
    marketplace = as_mapping(metadata, path=path).get("marketplace")
    if marketplace is None:
        return {}
    return as_mapping(marketplace, path=path)


def catalog_entry(plugin_id: str, manifest: object, *, path: Path) -> dict[str, object]:
    """Build the catalog entry one plugin contributes to `marketplace.json`.

    Args:
        plugin_id: The plugin directory name, which is also the entry's `name`.
        manifest: The parsed `plugin.json`.
        path: The manifest's path, named in any shape error.

    Returns:
        A dictionary with exactly `CATALOG_ENTRY_KEYS`, in that order.

    Raises:
        UnexpectedShapeError: If a field the entry needs is missing or of the wrong type.
    """
    document = as_mapping(manifest, path=path)
    marketplace = marketplace_metadata(manifest, path=path)
    return {
        "name": plugin_id,
        "source": plugin_source(plugin_id),
        "description": as_str(document.get("description"), path=path),
        "category": as_str(marketplace.get("category"), path=path),
        "tags": as_str_list(marketplace.get("tags"), path=path),
        "author": dict(as_mapping(document.get("author"), path=path)),
        "license": as_str(document.get("license"), path=path),
    }


def build_plugins_array(root: Path) -> list[dict[str, object]]:
    """Build the whole generated `plugins` array from the manifests on disk.

    Args:
        root: The repository root.

    Returns:
        One entry per plugin, ordered by directory name.

    Raises:
        UnexpectedShapeError: If a manifest is missing a field the entry needs.
        MalformedJsonError: If a manifest is not valid JSON.
    """
    return [
        catalog_entry(
            plugin_id,
            load_json(manifest_path(root, plugin_id)),
            path=manifest_path(root, plugin_id),
        )
        for plugin_id in plugin_ids(root)
    ]


def check_name(plugin_id: str) -> list[Finding]:
    """Check a plugin directory name against the grammar and the length limit (M6).

    Args:
        plugin_id: The plugin directory name.

    Returns:
        One finding per rule broken.
    """
    findings: list[Finding] = []
    rel = manifest_rel(plugin_id)
    if PLUGIN_NAME_RE.match(plugin_id) is None:
        findings.append(
            Finding("M6", rel, f"{plugin_id!r} is not kebab-case `^[a-z0-9]+(-[a-z0-9]+)*$`"),
        )
    if len(plugin_id) > MAX_PLUGIN_NAME_LENGTH:
        findings.append(
            Finding(
                "M6",
                rel,
                (
                    f"{plugin_id!r} is {len(plugin_id)} characters; at most "
                    f"{MAX_PLUGIN_NAME_LENGTH} keeps `plugin: <name>` inside GitHub's limit"
                ),
            ),
        )
    return findings


def check_category(plugin_id: str, category: object) -> list[Finding]:
    """Check that a manifest's catalog category is one of the allowed values (M2).

    Args:
        plugin_id: The plugin directory name.
        category: The value read from `metadata.marketplace.category`.

    Returns:
        One finding when the category is absent or not on the list.
    """
    rel = manifest_rel(plugin_id)
    if not isinstance(category, str):
        return [Finding("M2", rel, "`metadata.marketplace.category` is missing")]
    if category not in MARKETPLACE_CATEGORIES:
        allowed = ", ".join(MARKETPLACE_CATEGORIES)
        return [Finding("M2", rel, f"category {category!r} is not one of: {allowed}")]
    return []


def check_tags(plugin_id: str, tags: object) -> list[Finding]:
    """Check the tag list of one catalog entry (M3).

    Args:
        plugin_id: The plugin directory name.
        tags: The value read from `metadata.marketplace.tags`.

    Returns:
        One finding per rule broken.
    """
    rel = manifest_rel(plugin_id)
    if not is_json_array(tags):
        return [Finding("M3", rel, "`metadata.marketplace.tags` is missing")]
    findings: list[Finding] = []
    if not MIN_TAGS <= len(tags) <= MAX_TAGS:
        findings.append(
            Finding("M3", rel, f"{len(tags)} tags; between {MIN_TAGS} and {MAX_TAGS} allowed"),
        )
    seen: set[str] = set()
    for tag in tags:
        if not isinstance(tag, str):
            findings.append(Finding("M3", rel, f"tag {tag!r} is not a string"))
            continue
        if TAG_RE.match(tag) is None:
            findings.append(Finding("M3", rel, f"tag {tag!r} is not kebab-case"))
        if tag in seen:
            findings.append(Finding("M3", rel, f"tag {tag!r} is listed twice"))
        seen.add(tag)
    return findings


def check_renames(root: Path) -> list[Finding]:
    """Check the catalog's `renames` map (M9).

    Three rules: every value is a string or null, no key names a directory that still ships,
    and a key mapped to null has no catalog row left in the root README.

    Args:
        root: The repository root.

    Returns:
        One finding per rule broken.
    """
    try:
        renames = read_renames(root)
    except MaintainerError as error:
        return [Finding("M9", MARKETPLACE_PATH, str(error))]
    shipping = set(plugin_ids(root))
    readme = root / ROOT_README
    text = readme.read_text(encoding="utf-8") if readme.is_file() else ""
    findings: list[Finding] = []
    for old, new in renames.items():
        if old in shipping:
            findings.append(
                Finding(
                    "M9",
                    MARKETPLACE_PATH,
                    f"`renames` maps {old!r}, but `{PLUGINS_DIRNAME}/{old}/` still ships",
                ),
            )
        if new is None and f"]({PLUGINS_DIRNAME}/{old}/{ROOT_README})" in text:
            findings.append(
                Finding(
                    "M9",
                    ROOT_README,
                    (
                        f"{old!r} is removed in `renames`, but the catalog table still links to "
                        f"`{PLUGINS_DIRNAME}/{old}/{ROOT_README}`"
                    ),
                ),
            )
    return findings


def _schema_findings(root: Path, rel: str, document: Mapping[str, object]) -> list[Finding]:
    """Check that a document's `$schema` hint resolves to a file that exists (M10).

    Args:
        root: The repository root.
        rel: The repository-relative path of the document.
        document: The parsed document.

    Returns:
        One finding when the hint is a relative path with nothing behind it.
    """
    hint = document.get(SCHEMA_KEY)
    if not isinstance(hint, str) or "://" in hint:
        return []
    target = (root / rel).parent / hint
    if target.is_file():
        return []
    return [Finding("M10", rel, f"`{SCHEMA_KEY}` points at {hint!r}, which does not exist")]


def check_links(root: Path) -> list[Finding]:
    """Check the catalog's and the manifests' outbound paths (M10).

    Args:
        root: The repository root.

    Returns:
        One finding per dead `$schema` hint and per `homepage` that does not name the plugin.
    """
    findings: list[Finding] = []
    catalog_file = root / MARKETPLACE_PATH
    if catalog_file.is_file():
        findings.extend(
            _schema_findings(
                root, MARKETPLACE_PATH, as_mapping(load_json(catalog_file), path=catalog_file)
            ),
        )
    for plugin_id in plugin_ids(root):
        path = manifest_path(root, plugin_id)
        rel = manifest_rel(plugin_id)
        document = as_mapping(load_json(path), path=path)
        findings.extend(_schema_findings(root, rel, document))
        homepage = document.get("homepage")
        expected = f"/{PLUGINS_DIRNAME}/{plugin_id}"
        if isinstance(homepage, str) and not homepage.endswith(expected):
            findings.append(
                Finding("M10", rel, f"`homepage` {homepage!r} does not end with {expected!r}"),
            )
    return findings
