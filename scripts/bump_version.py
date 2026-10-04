#!/usr/bin/env python3
"""Prepare a version bump from the hand-written changelog (docs/releasing.md).

Usage:
  python3 scripts/bump_version.py plugin <name> <major|minor|patch> [--dry-run]

Run it in the same pull request as the change: every change inside
plugins/<name>/ ships with its own release. The marketplace catalog has no
version.

It only prepares files; it never commits, tags or pushes:

  1. checks the changelog: `## [Unreleased]` has notes, and a MAJOR bump has a
     non-empty `### Migration` section;
  2. moves the `## [Unreleased]` notes into `## [<version>] - <date>` (UTC);
  3. bumps `version` in plugin.json, the only place a version lives, so the
     catalog needs no other change;
  4. regenerates the README content that shows the version;
  5. runs `claude plugin validate --strict` and scripts/check_repo.py.

Then review the diff and commit it in the pull request; after the merge, tag
by hand as docs/releasing.md describes.
Releases are not bundled into a single command until the first real release
shows which steps belong together
(docs/adr/decisions/ADR_2026-10-03_release-automation.md).
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import datetime as dt
import sys
from typing import TYPE_CHECKING

import repo

if TYPE_CHECKING:
    from pathlib import Path

    from repo import JSON

LEVELS = ("major", "minor", "patch")


class NotAJsonObjectError(SystemExit):
    """A manifest that must be a JSON object is something else."""

    def __init__(self, path: Path) -> None:
        """Name the file that is not a JSON object."""
        super().__init__(f"{path} is not a JSON object")


@dataclass(frozen=True)
class Target:
    """What a bump changes: the changelog, the manifest and what to validate."""

    label: str
    changelog: Path
    manifest: Path
    validate: Path


def _fail(message: str) -> int:
    repo.emit(f"✘ {message}")
    return 1


def rewrite_changelog(text: str, version: str, date: str) -> str:
    """Move the Unreleased notes under a new `## [version] - date` heading."""
    lines = text.splitlines()
    start = lines.index("## [Unreleased]")
    end = next(
        (i for i in range(start + 1, len(lines)) if lines[i].startswith("## [")),
        len(lines),
    )
    notes = "\n".join(lines[start + 1 : end]).strip()
    block = ["", f"## [{version}] - {date}", "", *notes.splitlines(), ""]
    return "\n".join([*lines[: start + 1], *block, *lines[end:]]).rstrip("\n") + "\n"


def prepare(changelog_path: Path, current: str, level: str) -> tuple[str, str] | str:
    """Return (new_version, new_changelog_text), or an error message."""
    text = changelog_path.read_text(encoding="utf-8")
    changelog = repo.parse_changelog(text)
    if changelog.problems:
        return f"{changelog_path}: " + "; ".join(changelog.problems)
    if not changelog.unreleased:
        return f"{changelog_path}: ## [Unreleased] is empty; write the user-facing notes first"
    if changelog.releases and changelog.releases[0].version != current:
        latest = changelog.releases[0].version
        return f"{changelog_path}: latest release {latest} does not match current version {current}"
    if level == "major" and not repo.has_section_content(changelog.unreleased, "Migration"):
        return f'{changelog_path}: a major release needs a non-empty "### Migration" section'
    new_version = repo.bump(current, level)
    today = dt.datetime.now(dt.UTC).date().isoformat()
    return new_version, rewrite_changelog(text, new_version, today)


def set_version(path: Path, version: str) -> None:
    """Replace `version` in a manifest, keeping every other key and the key order."""
    data = repo.as_dict(repo.load_json(path))
    if data is None:
        raise NotAJsonObjectError(path)
    updated: dict[str, JSON] = {
        key: (version if key == "version" else value) for key, value in data.items()
    }
    repo.dump_json(path, updated)


def _apply(target: Target, level: str, *, dry_run: bool) -> int:
    data = repo.as_dict(repo.load_json(target.manifest)) or {}
    current = repo.as_str(data.get("version")) or ""
    prepared = prepare(target.changelog, current, level)
    if isinstance(prepared, str):
        return _fail(prepared)
    new_version, changelog_text = prepared
    repo.emit(f"{target.label}: {current} → {new_version} ({level})")
    if dry_run:
        repo.emit(changelog_text)
        return 0
    _ = target.changelog.write_text(changelog_text, encoding="utf-8")
    set_version(target.manifest, new_version)
    for command in (
        [sys.executable, str(repo.ROOT / "scripts" / "sync_readmes.py")],
        ["claude", "plugin", "validate", str(target.validate), "--strict"],
        [sys.executable, str(repo.ROOT / "scripts" / "check_repo.py")],
    ):
        result = repo.run(command, check=False)
        if result.returncode != 0:
            repo.emit(result.stdout + result.stderr)
            return _fail(f"{' '.join(command)} failed; fix it before committing")
    tag = repo.plugin_tag(target.label, new_version)
    next_steps = "Review `git diff` and commit in the pull request; tag after the merge."
    repo.emit(f"✔ files prepared for {tag}. {next_steps}")
    return 0


def main() -> int:
    """Parse the command line and prepare the bump."""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest="command", required=True)
    plugin_parser = sub.add_parser("plugin", help="bump one plugin")
    _ = plugin_parser.add_argument("name")
    _ = plugin_parser.add_argument("level", choices=LEVELS)
    _ = plugin_parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    level: str = args.level  # pyright: ignore[reportAny]  # argparse Namespace attributes are Any
    dry_run: bool = args.dry_run  # pyright: ignore[reportAny]  # argparse Namespace attributes are Any
    name: str = args.name  # pyright: ignore[reportAny]  # argparse Namespace attributes are Any
    plugin = repo.PLUGINS_DIR / name
    manifest = plugin / ".claude-plugin" / "plugin.json"
    if not manifest.is_file():
        return _fail(f"unknown plugin {name}")
    target = Target(name, plugin / "CHANGELOG.md", manifest, plugin)
    return _apply(target, level, dry_run=dry_run)


if __name__ == "__main__":
    sys.exit(main())
