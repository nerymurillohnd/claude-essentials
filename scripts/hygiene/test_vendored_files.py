"""X2: the vendored schemas are byte-pinned, because "unmodified" is the whole claim.

GitHub publishes no schema for issue forms, so this repository vendors SchemaStore's copies
and validates every form against them. The value of that is the word *unmodified*: a schema
edited to accept what a form happens to say validates nothing. Nothing else would notice —
the forms would still pass — so the hash is the check.

The hashes below were recorded at gate 0 of the migration, before anything moved, and are
compared again at gate 9 after `schemas/github/` becomes `.github/schemas/`. Only the path
constant changes then; the hashes may not.
"""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING, Final

import pytest

from scripts.common.plugins import working_files
from scripts.lint.json_files import is_excluded

if TYPE_CHECKING:
    from pathlib import Path

VENDORED_DIR: Final = ".github/schemas"
"""Where the copies live until step 9 moves them to `.github/schemas`."""

HASHES: Final[dict[str, str]] = {
    "issue-config.schema.json": (
        "0988613c0ace111998e94d1883ad1a6110fbd8525385e1bff88ccb102e851e60"
    ),
    "issue-forms.schema.json": ("31ed735665dfe33739dc41a2342871d32199154ea8a1dd7411ca6303a0e868c5"),
}
"""SHA-256 of each file, recorded at gate 0 (2026-09-21)."""


def _digest(path: Path) -> str:
    """Hash one file.

    Args:
        path: The file to read.

    Returns:
        Its SHA-256, hex-encoded.
    """
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.mark.parametrize("name", sorted(HASHES))
def test_each_vendored_schema_is_byte_identical(repo: Path, name: str) -> None:
    """An edited schema validates whatever the forms happen to say, and nothing reports it."""
    assert _digest(repo / VENDORED_DIR / name) == HASHES[name]


def test_the_vendored_directory_holds_exactly_these_files(repo: Path) -> None:
    """A third file would be vendored text nothing pins, which is the same defect."""
    listed = sorted(rel.rsplit("/", 1)[-1] for rel in working_files(repo, f"{VENDORED_DIR}/*.json"))
    assert listed == sorted(HASHES)


@pytest.mark.parametrize("name", sorted(HASHES))
def test_the_formatter_leaves_them_alone(name: str) -> None:
    """`make fix` rewrites every other JSON file; on these it would break the hash."""
    assert is_excluded(f"{VENDORED_DIR}/{name}")
