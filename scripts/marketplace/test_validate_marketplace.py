"""Tests for the catalog gate: the registry, a clean tree, and one seeded defect per ID."""

from __future__ import annotations

import shutil
from typing import TYPE_CHECKING

import pytest

from scripts.common.errors import ExitCode, MissingPathError
from scripts.common.plugins import repo_root
from scripts.marketplace.catalog import build_plugins_array
from scripts.marketplace.conftest import (
    PLUGIN_ID,
    catalog_obj,
    manifest_obj,
    regenerate,
    write_catalog,
    write_manifest,
)
from scripts.marketplace.validate_marketplace import (
    MARKETPLACE_INVARIANTS,
    collect,
    main,
    registry_lines,
)

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from scripts.common.errors import Finding

EXPECTED_IDS = tuple(f"M{number}" for number in range(1, 11))
"""Every invariant §A6 assigns to the catalog area, in order."""


def ids(findings: Sequence[Finding]) -> list[str]:
    """Return the invariant ids of a finding list.

    Args:
        findings: The findings to read.

    Returns:
        One id per finding, in the order they were reported.
    """
    return [finding.invariant_id for finding in findings]


def test_registry_covers_exactly_the_documented_invariants() -> None:
    """§A6 assigns M1 to M10 to this area; the registry is that table."""
    assert tuple(ident for ident, _, _ in MARKETPLACE_INVARIANTS) == EXPECTED_IDS


def test_every_registry_row_names_its_defect() -> None:
    """P14: a check exists only with a concrete defect recorded next to it."""
    for _, check, defect in MARKETPLACE_INVARIANTS:
        assert check.strip()
        assert defect.strip()


def test_registry_lines_print_one_row_each() -> None:
    """`--list` is the registry a maintainer reads from gate output alone."""
    assert len(registry_lines()) == len(MARKETPLACE_INVARIANTS)


@pytest.mark.slow
def test_the_real_tree_passes() -> None:
    """The gate is green on this repository as it stands."""
    assert collect(repo_root()) == []


def test_main_exits_zero_on_the_real_tree() -> None:
    """The exit status `make validate` reads."""
    assert main([]) == 0


def test_main_prints_the_registry() -> None:
    """`--list` never checks anything, so it always succeeds."""
    assert main(["--list"]) == 0


def test_a_clean_fixture_tree_passes(tree: Path) -> None:
    """The fixture itself owes nothing, so every probe below is the defect it seeds."""
    assert collect(tree) == []


def test_m1_fires_when_the_manifest_name_is_not_the_directory(tree: Path) -> None:
    """A catalog/directory mismatch breaks install."""
    manifest = manifest_obj()
    manifest["name"] = "beta"
    write_manifest(tree, manifest)
    assert "M1" in ids(collect(tree))


def test_m2_fires_on_a_free_text_category(tree: Path) -> None:
    """Categories come from one list, never from the plugin."""
    manifest = manifest_obj()
    manifest["metadata"] = {"marketplace": {"category": "misc", "tags": ["one"]}}
    write_manifest(tree, manifest)
    assert "M2" in ids(collect(tree))


def test_m3_fires_on_nine_tags(tree: Path) -> None:
    """The cap is eight, so a ninth tag is an unbounded list starting."""
    manifest = manifest_obj()
    manifest["metadata"] = {
        "marketplace": {"category": "development", "tags": [f"t{n}" for n in range(9)]},
    }
    write_manifest(tree, manifest)
    regenerate(tree)
    assert "M3" in ids(collect(tree))


def test_m4_fires_on_a_license_that_is_not_apache(tree: Path) -> None:
    """ADR-0005: every plugin here ships under Apache-2.0."""
    manifest = manifest_obj()
    manifest["license"] = "MIT"
    write_manifest(tree, manifest)
    assert "M4" in ids(collect(tree))


def test_m5_fires_on_a_two_part_version(tree: Path) -> None:
    """The official CLI accepts `1.0`; Claude Code then orders it differently."""
    manifest = manifest_obj()
    manifest["version"] = "1.0"
    write_manifest(tree, manifest)
    assert "M5" in ids(collect(tree))


def test_m6_fires_on_a_name_over_the_label_limit(tree: Path) -> None:
    """DEBT-0021: `plugin: <name>` must stay inside GitHub's 50-character limit."""
    long_id = "a" * 43
    write_manifest(tree, manifest_obj(long_id), plugin_id=long_id)
    regenerate(tree)
    assert "M6" in ids(collect(tree))


def test_m7_fires_on_a_hand_edited_array(tree: Path) -> None:
    """The array is generated; a hand edit is exactly what this catches."""
    catalog = catalog_obj([{"name": PLUGIN_ID, "source": f"./plugins/{PLUGIN_ID}"}])
    write_catalog(tree, catalog)
    assert "M7" in ids(collect(tree))


def test_m8_fires_when_a_plugin_has_no_entry(tree: Path) -> None:
    """A plugin on disk that the catalog never offers cannot be installed."""
    write_catalog(tree, catalog_obj([]))
    assert "M8" in ids(collect(tree))


def test_m9_fires_on_a_renames_key_that_still_ships(tree: Path) -> None:
    """DEBT-0006: the catalog claimed a rename the tree had not made."""
    catalog = catalog_obj([])
    catalog["renames"] = {PLUGIN_ID: "beta"}
    write_catalog(tree, catalog)
    regenerate(tree)
    assert "M9" in ids(collect(tree))


def test_m9_fires_when_a_removed_plugin_keeps_its_readme_row(tree: Path) -> None:
    """A removal leaves the catalog table behind unless the row goes with it."""
    shutil.rmtree(tree / "plugins" / PLUGIN_ID)
    catalog = catalog_obj([])
    catalog["renames"] = {PLUGIN_ID: None}
    write_catalog(tree, catalog)
    assert "M9" in ids(collect(tree))


def test_m10_fires_on_a_dead_schema_hint(tree: Path) -> None:
    """A `$schema` pointing at a file that is gone is a dead link in a shipped artifact."""
    catalog = catalog_obj([])
    catalog["$schema"] = "../schemas/marketplace.schema.json"
    catalog["plugins"] = build_plugins_array(tree)
    write_catalog(tree, catalog)
    assert "M10" in ids(collect(tree))


def test_m10_fires_on_a_homepage_that_names_another_plugin(tree: Path) -> None:
    """A copied manifest sends every reader to the plugin it was copied from."""
    manifest = manifest_obj()
    manifest["homepage"] = "https://example.test/tree/main/plugins/beta"
    write_manifest(tree, manifest)
    assert "M10" in ids(collect(tree))


@pytest.mark.parametrize("identifier", EXPECTED_IDS)
def test_every_invariant_has_a_seeded_probe(identifier: str) -> None:
    """Each ID is proved by a test in this file, so none of them is decorative."""
    names = [name for name in globals() if name.startswith(f"test_{identifier.lower()}_")]
    assert names, f"{identifier} has no seeded-defect test"


def test_a_root_that_does_not_exist_is_one_line(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """`--root /nonexistent` used to end in a `FileNotFoundError` traceback.

    Args:
        capsys: Captures what the entrypoint printed.
    """
    assert main(["--root", "/nonexistent"]) == int(ExitCode.USAGE)
    captured = capsys.readouterr()
    assert captured.err.splitlines() == ["error: /nonexistent: the repository root does not exist"]
    assert "Traceback" not in captured.err


def test_a_tree_without_a_catalog_is_one_line(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A directory that is not a marketplace is a usage error, not a crash.

    Args:
        tmp_path: pytest's per-test temporary directory.
        capsys: Captures what the entrypoint printed.
    """
    assert main(["--root", str(tmp_path)]) == int(ExitCode.USAGE)
    assert "the marketplace catalog does not exist" in capsys.readouterr().err


def test_collect_refuses_a_missing_root(tmp_path: Path) -> None:
    """The precondition is in `collect`, so every caller gets the same error.

    Args:
        tmp_path: pytest's per-test temporary directory.
    """
    with pytest.raises(MissingPathError):
        _ = collect(tmp_path / "absent")
