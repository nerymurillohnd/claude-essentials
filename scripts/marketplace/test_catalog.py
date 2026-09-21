"""Tests for the catalog entry shape and the field rules M2, M3, M6, M9 and M10."""

from __future__ import annotations

from pathlib import Path
import shutil

import pytest

from scripts.common.errors import UnexpectedShapeError
from scripts.common.plugins import as_mapping, load_json, repo_root
from scripts.marketplace.catalog import (
    CATALOG_ENTRY_KEYS,
    MARKETPLACE_CATEGORIES,
    MAX_PLUGIN_NAME_LENGTH,
    build_plugins_array,
    catalog_entry,
    check_category,
    check_links,
    check_name,
    check_renames,
    check_tags,
)
from scripts.marketplace.conftest import (
    PLUGIN_ID,
    catalog_obj,
    manifest_obj,
    regenerate,
    write_catalog,
    write_file,
    write_manifest,
)
from scripts.versioning.version_plan import CATALOG_GENERATED_KEY, MARKETPLACE_PATH


def test_entry_carries_exactly_the_documented_keys_in_order() -> None:
    """The catalog never pins a version, and the key order is part of the artifact."""
    entry = catalog_entry(PLUGIN_ID, manifest_obj(), path=Path("plugin.json"))
    assert tuple(entry) == CATALOG_ENTRY_KEYS


def test_entry_source_is_the_repository_relative_directory() -> None:
    """Claude Code resolves the plugin from this path when the marketplace is added."""
    entry = catalog_entry(PLUGIN_ID, manifest_obj(), path=Path("plugin.json"))
    assert entry["source"] == f"./plugins/{PLUGIN_ID}"


def test_entry_refuses_a_manifest_without_a_category() -> None:
    """A missing catalog field is a shape error, not a silently empty entry."""
    manifest = manifest_obj()
    manifest["metadata"] = {"marketplace": {"tags": ["one"]}}
    with pytest.raises(UnexpectedShapeError):
        _ = catalog_entry(PLUGIN_ID, manifest, path=Path("plugin.json"))


@pytest.mark.slow
def test_build_plugins_array_reproduces_the_tracked_catalog() -> None:
    """The generated array on this tree is exactly what `marketplace.json` already carries."""
    root = repo_root()
    path = root / MARKETPLACE_PATH
    tracked = as_mapping(load_json(path), path=path)[CATALOG_GENERATED_KEY]
    assert build_plugins_array(root) == tracked


def test_check_name_accepts_a_kebab_case_name() -> None:
    """The grammar every plugin directory and its derived label follow."""
    assert check_name("agent-self-knowledge") == []


@pytest.mark.parametrize("name", ["Alpha", "alpha_beta", "-alpha", "alpha--beta", "alpha-"])
def test_check_name_refuses_anything_but_kebab_case(name: str) -> None:
    """Each of these would install under a directory the catalog cannot name."""
    assert [finding.invariant_id for finding in check_name(name)] == ["M6"]


def test_check_name_refuses_a_name_over_the_label_limit() -> None:
    """A longer name makes `plugin: <name>` exceed GitHub's 50-character limit."""
    name = "a" * (MAX_PLUGIN_NAME_LENGTH + 1)
    assert [finding.invariant_id for finding in check_name(name)] == ["M6"]


def test_check_category_accepts_every_allowed_value() -> None:
    """The constant is the single home of the list, so every value in it must pass."""
    for category in MARKETPLACE_CATEGORIES:
        assert check_category(PLUGIN_ID, category) == []


@pytest.mark.parametrize("category", ["Development", "migration", "", None])
def test_check_category_refuses_free_text(category: object) -> None:
    """A category outside the list would render as an unknown filter in the catalog."""
    assert [finding.invariant_id for finding in check_category(PLUGIN_ID, category)] == ["M2"]


@pytest.mark.parametrize(
    "tags",
    [
        [],
        ["a"] * 9,
        ["one", "one"],
        ["One"],
        ["a_b"],
        ["ok", 3],
        None,
    ],
)
def test_check_tags_refuses_every_broken_list(tags: object) -> None:
    """Empty, over the cap, duplicated, not kebab-case, not a string, or absent."""
    findings = check_tags(PLUGIN_ID, tags)
    assert findings
    assert findings[0].invariant_id == "M3"


def test_check_tags_accepts_a_normal_list() -> None:
    """The shape every shipping plugin already uses."""
    assert check_tags(PLUGIN_ID, ["one", "two-three"]) == []


def test_check_renames_passes_on_a_clean_tree(tree: Path) -> None:
    """A catalog with no `renames` key owes nothing."""
    assert check_renames(tree) == []


def test_check_renames_refuses_a_key_that_still_ships(tree: Path) -> None:
    """A plugin cannot be renamed away and still be on disk under its old name."""
    catalog = catalog_obj([])
    catalog["renames"] = {PLUGIN_ID: "beta"}
    write_catalog(tree, catalog)
    regenerate(tree)
    assert [finding.invariant_id for finding in check_renames(tree)] == ["M9"]


def test_check_renames_refuses_a_removed_plugin_with_a_readme_row(tree: Path) -> None:
    """DEBT-0006: the catalog table kept offering a plugin that had been removed."""
    shutil.rmtree(tree / "plugins" / PLUGIN_ID)
    catalog = catalog_obj([])
    catalog["renames"] = {PLUGIN_ID: None}
    write_catalog(tree, catalog)
    findings = check_renames(tree)
    assert [finding.invariant_id for finding in findings] == ["M9"]
    assert findings[0].path == "README.md"


def test_check_links_passes_on_a_clean_tree(tree: Path) -> None:
    """A homepage that ends with the plugin's own directory, and no `$schema` hint."""
    assert check_links(tree) == []


def test_check_links_refuses_a_homepage_that_names_another_plugin(tree: Path) -> None:
    """A copied manifest points every reader at the plugin it was copied from."""
    manifest = manifest_obj()
    manifest["homepage"] = "https://example.test/tree/main/plugins/beta"
    write_manifest(tree, manifest)
    assert [finding.invariant_id for finding in check_links(tree)] == ["M10"]


def test_check_links_refuses_a_schema_hint_with_nothing_behind_it(tree: Path) -> None:
    """The mirror schemas are deleted at step 9; a hint left behind is a dead path."""
    catalog = catalog_obj([])
    catalog["$schema"] = "../schemas/marketplace.schema.json"
    write_catalog(tree, catalog)
    assert [finding.invariant_id for finding in check_links(tree)] == ["M10"]


def test_check_links_ignores_a_remote_schema_url(tree: Path) -> None:
    """A published schema URL is not a path this repository can resolve."""
    manifest = manifest_obj()
    manifest["$schema"] = "https://example.test/plugin.schema.json"
    write_manifest(tree, manifest)
    write_file(tree / "README.md", f"| [Alpha](plugins/{PLUGIN_ID}/README.md) |\n")
    assert check_links(tree) == []
