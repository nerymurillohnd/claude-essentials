"""Rewrite the generated `plugins` array of `.claude-plugin/marketplace.json` in place.

Only that one array is owned by this script. Every other key the catalog carries is authored
by hand, so the rewrite reads the file, replaces `plugins` with what the manifests on disk
say, and writes the document back in the same key order. The one field it removes is
`$schema`: the repository's mirror schemas are deleted at step 9 of the migration, and a hint
pointing at a file that no longer exists is worse than no hint (M10).

`make generate` runs this and then `git diff --exit-code`, so a manifest edit that was never
regenerated fails the gate rather than reaching users as a stale catalog.
"""

from __future__ import annotations

import argparse
import sys
from typing import TYPE_CHECKING, Final

from scripts.common.errors import ExitCode, MaintainerError, MissingPathError
from scripts.common.jsontext import canonical_json
from scripts.common.plugins import as_mapping, load_json, repo_root
from scripts.marketplace.catalog import SCHEMA_KEY, build_plugins_array
from scripts.versioning.version_plan import CATALOG_GENERATED_KEY, MARKETPLACE_PATH

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

REMOVED_KEYS: Final = (SCHEMA_KEY,)
"""Top-level keys this generator drops rather than carries over."""


def render(root: Path) -> str:
    """Build the whole catalog document as it should be written.

    Args:
        root: The repository root.

    Returns:
        Canonical JSON text: every authored key in its original order, `plugins` regenerated,
        `$schema` removed.

    Raises:
        MaintainerError: If the catalog or a manifest cannot be read or has the wrong shape.
    """
    path = root / MARKETPLACE_PATH
    if not path.is_file():
        raise MissingPathError(path, "the marketplace catalog")
    catalog = as_mapping(load_json(path), path=path)
    document: dict[str, object] = {
        key: value for key, value in catalog.items() if key not in REMOVED_KEYS
    }
    document[CATALOG_GENERATED_KEY] = build_plugins_array(root)
    return canonical_json(document)


def write(root: Path) -> bool:
    """Write the catalog if the generated document differs from what is on disk.

    Args:
        root: The repository root.

    Returns:
        True when the file was rewritten.

    Raises:
        MaintainerError: If the catalog or a manifest cannot be read or has the wrong shape.
    """
    path = root / MARKETPLACE_PATH
    rendered = render(root)
    if path.read_text(encoding="utf-8") == rendered:
        return False
    _ = path.write_text(rendered, encoding="utf-8")
    return True


def parse_args(argv: Sequence[str] | None) -> bool:
    """Parse the command line.

    Args:
        argv: Arguments without the program name; `sys.argv[1:]` when None.

    Returns:
        True when the caller asked for a dry run.

    Raises:
        SystemExit: If argparse refuses the arguments.
    """
    parser = argparse.ArgumentParser(
        prog="python -m scripts.marketplace.generate_marketplace",
        description="Regenerate the `plugins` array of .claude-plugin/marketplace.json.",
    )
    _ = parser.add_argument(
        "--dry-run",
        action="store_true",
        help="report whether the catalog is stale without writing it",
    )
    values: dict[str, object] = vars(parser.parse_args(argv))
    return bool(values["dry_run"])


def main(argv: Sequence[str] | None = None) -> int:
    """Regenerate the catalog.

    Args:
        argv: Arguments without the program name; `sys.argv[1:]` when None.

    Returns:
        0 when the catalog is written or already current, 2 when the inputs are unusable.
    """
    dry_run = parse_args(argv)
    try:
        root = repo_root()
        if dry_run:
            stale = render(root) != (root / MARKETPLACE_PATH).read_text(encoding="utf-8")
            print(f"{MARKETPLACE_PATH} {'is stale' if stale else 'is current'}")
            return int(ExitCode.OK)
        changed = write(root)
    except (MaintainerError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return int(ExitCode.USAGE)
    print(f"{MARKETPLACE_PATH} {'rewritten' if changed else 'unchanged'}")
    return int(ExitCode.OK)


if __name__ == "__main__":
    raise SystemExit(main())
