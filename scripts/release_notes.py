#!/usr/bin/env python3
"""Release workflow helpers (.github/workflows/release.yml).

Usage:
  python3 scripts/release_notes.py verify <tag>   # the tag matches the manifest version
  python3 scripts/release_notes.py notes <tag>    # print that version's changelog section

Tags use the official `claude plugin tag` format `<name>--v<version>`; the
marketplace uses `marketplace--v<version>`.
"""

from __future__ import annotations

import argparse
import sys
from typing import TYPE_CHECKING

import repo

if TYPE_CHECKING:
    from pathlib import Path


def _fail(message: str) -> int:
    repo.emit(f"✘ {message}")
    return 1


def _sources(tag: str) -> tuple[str, Path, Path] | str:
    parts = repo.split_tag(tag)
    if parts is None:
        return f'"{tag}" is not a <name>--v<version> tag'
    name, version = parts
    if name == repo.MARKETPLACE_TAG_NAME:
        return version, repo.MARKETPLACE_FILE, repo.ROOT / "CHANGELOG.md"
    plugin = repo.PLUGINS_DIR / name
    return version, plugin / ".claude-plugin" / "plugin.json", plugin / "CHANGELOG.md"


def verify(tag: str) -> int:
    """Check that the tag's version matches the version in its manifest."""
    sources = _sources(tag)
    if isinstance(sources, str):
        return _fail(sources)
    version, manifest, _changelog = sources
    if not manifest.is_file():
        return _fail(f"{tag}: {manifest.relative_to(repo.ROOT)} does not exist")
    data = repo.as_dict(repo.load_json(manifest)) or {}
    declared = repo.as_str(data.get("version"))
    if declared != version:
        return _fail(f'{tag}: {manifest.relative_to(repo.ROOT)} declares version "{declared}"')
    repo.emit(f"✔ {tag} matches {manifest.relative_to(repo.ROOT)}")
    return 0


def notes(tag: str) -> int:
    """Print the changelog section of the tagged version (the release notes)."""
    sources = _sources(tag)
    if isinstance(sources, str):
        return _fail(sources)
    version, _manifest, changelog_path = sources
    if not changelog_path.is_file():
        return _fail(f"{changelog_path.relative_to(repo.ROOT)} not found")
    changelog = repo.parse_changelog(changelog_path.read_text(encoding="utf-8"))
    for release in changelog.releases:
        if release.version == version:
            repo.emit(release.body)
            return 0
    return _fail(f"{changelog_path.relative_to(repo.ROOT)} has no section for {version}")


def main() -> int:
    """Parse the command line and run `verify` or `notes`."""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    _ = parser.add_argument("command", choices=("verify", "notes"))
    _ = parser.add_argument("tag")
    args = parser.parse_args()
    command: str = args.command  # pyright: ignore[reportAny]  # argparse Namespace attributes are Any
    tag: str = args.tag  # pyright: ignore[reportAny]  # argparse Namespace attributes are Any
    return verify(tag) if command == "verify" else notes(tag)


if __name__ == "__main__":
    sys.exit(main())
