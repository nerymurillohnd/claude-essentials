# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Prepare a version bump from the hand-written changelog (docs/releasing.md).

Usage:
  uv run scripts/bump_version.py plugin <name> <major|minor|patch> [--dry-run]
  uv run scripts/bump_version.py marketplace <major|minor|patch> [--dry-run]

It only prepares files; it never commits, tags or pushes:

  1. checks the changelog: `## [Unreleased]` has notes, and a MAJOR bump has a
     non-empty `### Migration` section;
  2. moves the `## [Unreleased]` notes into `## [<version>] - <date>` (UTC);
  3. bumps `version` in plugin.json (or marketplace.json for the marketplace),
     the only place a version lives, so the catalog needs no other change;
  4. regenerates the README content that shows the version;
  5. runs `claude plugin validate --strict` and scripts/check_repo.py.

Then review the diff, commit, and tag by hand as docs/releasing.md describes.
Releases are not bundled into a single command until the first real release
shows which steps belong together (docs/adr/decisions/ADR_2026-10-03_release-automation.md).
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

import repo
from repo import JSON

LEVELS = ("major", "minor", "patch")


def _fail(message: str) -> int:
    print(f"✘ {message}")
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
        return f"{changelog_path}: latest release {changelog.releases[0].version} does not match current version {current}"
    if level == "major" and not repo.has_section_content(
        changelog.unreleased, "Migration"
    ):
        return f'{changelog_path}: a major release needs a non-empty "### Migration" section'
    new_version = repo.bump(current, level)
    today = dt.datetime.now(dt.UTC).date().isoformat()
    return new_version, rewrite_changelog(text, new_version, today)


def set_version(path: Path, version: str) -> None:
    data = repo.as_dict(repo.load_json(path))
    if data is None:
        raise SystemExit(f"{path} is not a JSON object")
    updated: dict[str, JSON] = {
        key: (version if key == "version" else value) for key, value in data.items()
    }
    repo.dump_json(path, updated)


def _apply(
    label: str,
    changelog: Path,
    manifest: Path,
    level: str,
    dry_run: bool,
    validate_target: Path,
) -> int:
    data = repo.as_dict(repo.load_json(manifest)) or {}
    current = repo.as_str(data.get("version")) or ""
    prepared = prepare(changelog, current, level)
    if isinstance(prepared, str):
        return _fail(prepared)
    new_version, changelog_text = prepared
    print(f"{label}: {current} → {new_version} ({level})")
    if dry_run:
        print(changelog_text)
        return 0
    _ = changelog.write_text(changelog_text, encoding="utf-8")
    set_version(manifest, new_version)
    for command in (
        ["uv", "run", str(repo.ROOT / "scripts" / "sync_readmes.py")],
        ["claude", "plugin", "validate", str(validate_target), "--strict"],
        ["uv", "run", str(repo.ROOT / "scripts" / "check_repo.py")],
    ):
        result = repo.run(command, check=False)
        if result.returncode != 0:
            print(result.stdout + result.stderr)
            return _fail(f"{' '.join(command)} failed; fix it before committing")
    tag_name = repo.MARKETPLACE_TAG_NAME if label == "marketplace" else label
    tag = repo.plugin_tag(tag_name, new_version)
    print(
        f"✔ files prepared for {tag}. Review `git diff`, then follow docs/releasing.md to commit and tag."
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest="command", required=True)
    plugin_parser = sub.add_parser("plugin", help="bump one plugin")
    _ = plugin_parser.add_argument("name")
    _ = plugin_parser.add_argument("level", choices=LEVELS)
    _ = plugin_parser.add_argument("--dry-run", action="store_true")
    market_parser = sub.add_parser("marketplace", help="bump the marketplace catalog")
    _ = market_parser.add_argument("level", choices=LEVELS)
    _ = market_parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    command: str = args.command  # pyright: ignore[reportAny]  # argparse Namespace attributes are Any
    level: str = args.level  # pyright: ignore[reportAny]  # argparse Namespace attributes are Any
    dry_run: bool = args.dry_run  # pyright: ignore[reportAny]  # argparse Namespace attributes are Any
    if command == "plugin":
        name: str = args.name  # pyright: ignore[reportAny]  # argparse Namespace attributes are Any
        plugin = repo.PLUGINS_DIR / name
        manifest = plugin / ".claude-plugin" / "plugin.json"
        if not manifest.is_file():
            return _fail(f"unknown plugin {name}")
        return _apply(name, plugin / "CHANGELOG.md", manifest, level, dry_run, plugin)
    return _apply(
        "marketplace",
        repo.ROOT / "CHANGELOG.md",
        repo.MARKETPLACE_FILE,
        level,
        dry_run,
        repo.ROOT,
    )


if __name__ == "__main__":
    sys.exit(main())
