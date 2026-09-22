"""A minimal marketplace tree the catalog tests seed defects into.

Nothing here needs git: every catalog invariant is answered from the manifests, the catalog
and the root README, so the fixtures are plain directories and the tests stay fast.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

import pytest

from scripts.common.jsontext import canonical_json
from scripts.marketplace.generate_marketplace import write

if TYPE_CHECKING:
    from pathlib import Path

PLUGIN_ID: Final = "alpha"
"""The one plugin every fixture tree ships."""


def write_file(path: Path, text: str) -> None:
    """Create a file and every parent directory it needs.

    Args:
        path: The file to write.
        text: Its contents.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text(text, encoding="utf-8")


def manifest_obj(plugin_id: str = PLUGIN_ID) -> dict[str, object]:
    """Build a manifest that passes every invariant.

    Args:
        plugin_id: The plugin directory name.

    Returns:
        The manifest as a mutable document a test can break one field of.
    """
    return {
        "name": plugin_id,
        "version": "0.1.0",
        "description": f"{plugin_id} does one thing.",
        "author": {"name": "Test"},
        "homepage": f"https://example.test/tree/main/plugins/{plugin_id}",
        "license": "Apache-2.0",
        "metadata": {"marketplace": {"category": "development", "tags": ["one", "two"]}},
    }


def catalog_obj(entries: list[dict[str, object]]) -> dict[str, object]:
    """Build the catalog document around a generated `plugins` array.

    Args:
        entries: The array to embed.

    Returns:
        The catalog as a mutable document.
    """
    return {
        "name": "test-market",
        "owner": {"name": "Test"},
        "plugins": entries,
    }


def write_manifest(root: Path, manifest: dict[str, object], *, plugin_id: str = PLUGIN_ID) -> None:
    """Write one plugin manifest into a fixture tree.

    Args:
        root: The fixture repository root.
        manifest: The document to write.
        plugin_id: The directory the manifest goes into.
    """
    write_file(
        root / "plugins" / plugin_id / ".claude-plugin" / "plugin.json",
        canonical_json(manifest),
    )


def write_catalog(root: Path, catalog: dict[str, object]) -> None:
    """Write the marketplace catalog into a fixture tree.

    Args:
        root: The fixture repository root.
        catalog: The document to write.
    """
    write_file(root / ".claude-plugin" / "marketplace.json", canonical_json(catalog))


def regenerate(root: Path) -> None:
    """Rewrite the fixture catalog from its manifests, the way `make generate` would.

    Args:
        root: The fixture repository root.
    """
    _ = write(root)


def build_tree(root: Path) -> Path:
    """Build a marketplace with one plugin that passes M1 to M10.

    Args:
        root: The directory to build in.

    Returns:
        The same directory, now a fixture repository root.
    """
    write_manifest(root, manifest_obj())
    write_catalog(root, catalog_obj([]))
    write_file(
        root / "README.md",
        f"| [Alpha](plugins/{PLUGIN_ID}/README.md) | Does one thing. |\n",
    )
    regenerate(root)
    return root


@pytest.fixture
def tree(tmp_path: Path) -> Path:
    """Build a marketplace with one plugin that passes M1 to M10.

    Args:
        tmp_path: pytest's per-test temporary directory.

    Returns:
        The fixture repository root.
    """
    return build_tree(tmp_path)
