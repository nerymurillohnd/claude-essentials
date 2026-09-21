"""Tests for the catalog generator: what it owns, what it keeps, and what it removes."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from scripts.common.errors import ExitCode, MissingPathError
from scripts.common.jsontext import canonical_json
from scripts.common.plugins import as_mapping, load_json, repo_root
from scripts.marketplace.catalog import SCHEMA_KEY, build_plugins_array
from scripts.marketplace.conftest import (
    PLUGIN_ID,
    catalog_obj,
    manifest_obj,
    write_catalog,
    write_manifest,
)
from scripts.marketplace.generate_marketplace import main, render, write
from scripts.versioning.version_plan import CATALOG_GENERATED_KEY, MARKETPLACE_PATH

if TYPE_CHECKING:
    from pathlib import Path


def test_render_keeps_every_authored_key_in_its_original_order(tree: Path) -> None:
    """Only `plugins` is generated; reordering the rest would churn every diff."""
    catalog = catalog_obj([])
    catalog["description"] = "A marketplace."
    catalog["metadata"] = {"pluginRoot": "./plugins"}
    write_catalog(tree, catalog)
    document = as_mapping(load_json(tree / MARKETPLACE_PATH), path=tree / MARKETPLACE_PATH)
    _ = write(tree)
    rewritten = as_mapping(load_json(tree / MARKETPLACE_PATH), path=tree / MARKETPLACE_PATH)
    assert list(rewritten) == list(document)


def test_render_drops_the_schema_hint(tree: Path) -> None:
    """The mirror schema it points at is deleted at step 9 of the migration."""
    catalog = catalog_obj([])
    catalog[SCHEMA_KEY] = "../schemas/marketplace.schema.json"
    write_catalog(tree, catalog)
    assert SCHEMA_KEY not in render(tree)


def test_render_rebuilds_the_array_from_the_manifests(tree: Path) -> None:
    """A manifest edit reaches the catalog through the generator, never by hand."""
    manifest = manifest_obj()
    manifest["description"] = "Changed."
    write_manifest(tree, manifest)
    _ = write(tree)
    catalog = as_mapping(load_json(tree / MARKETPLACE_PATH), path=tree / MARKETPLACE_PATH)
    entries = catalog[CATALOG_GENERATED_KEY]
    assert entries == [
        {
            "name": PLUGIN_ID,
            "source": f"./plugins/{PLUGIN_ID}",
            "description": "Changed.",
            "category": "development",
            "tags": ["one", "two"],
        },
    ]


def test_write_is_idempotent(tree: Path) -> None:
    """The second run changes nothing, so `make generate` leaves a clean tree."""
    assert write(tree) is False


def test_render_is_canonical_json(tree: Path) -> None:
    """The generator writes what `make lint` accepts, so the two can never disagree."""
    document = as_mapping(load_json(tree / MARKETPLACE_PATH), path=tree / MARKETPLACE_PATH)
    assert render(tree) == canonical_json(document)


@pytest.mark.slow
def test_the_tracked_catalog_differs_only_by_the_schema_hint() -> None:
    """On this tree the generator reproduces the artifact except for the one removal."""
    root = repo_root()
    current = (root / MARKETPLACE_PATH).read_text(encoding="utf-8")
    removed = [line for line in current.splitlines(keepends=True) if SCHEMA_KEY not in line]
    assert "".join(removed) == render(root)


@pytest.mark.slow
def test_the_generated_array_matches_the_tracked_one() -> None:
    """M7 on the real tree: nothing was hand-edited into the catalog."""
    root = repo_root()
    path = root / MARKETPLACE_PATH
    assert as_mapping(load_json(path), path=path)[CATALOG_GENERATED_KEY] == build_plugins_array(
        root
    )


def test_a_tree_without_a_catalog_is_refused(tmp_path: Path) -> None:
    """The generator names the missing file instead of raising `FileNotFoundError`.

    Args:
        tmp_path: pytest's per-test temporary directory.
    """
    with pytest.raises(MissingPathError):
        _ = render(tmp_path)


@pytest.mark.slow
def test_main_outside_a_repository_is_one_line(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Running the generator outside a working tree prints a sentence, not a traceback.

    Args:
        tmp_path: pytest's per-test temporary directory.
        capsys: Captures what the entrypoint printed.
        monkeypatch: Moves the process outside any git working tree.
    """
    monkeypatch.chdir(tmp_path)
    assert main([]) == int(ExitCode.USAGE)
    captured = capsys.readouterr()
    assert captured.err.startswith("error: ")
    assert "Traceback" not in captured.err
