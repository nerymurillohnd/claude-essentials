# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Release a plugin or the marketplace (docs/releasing.md, docs/adr/0007-release-automation.md).

Usage:
  uv run scripts/release.py plugin <name> <major|minor|patch> [--dry-run]
  uv run scripts/release.py marketplace <major|minor|patch> [--dry-run]
  uv run scripts/release.py notes <tag>          # release notes for CI
  uv run scripts/release.py verify <tag>         # CI: tag matches the manifest version

A release moves the hand-written `## [Unreleased]` notes into a dated version
section, bumps the version (plugin.json for a plugin, marketplace.json for the
marketplace), commits with the maintainer's signing key, and tags:
`claude plugin tag` creates the official `<name>--v<version>` tag for plugins;
the marketplace uses `marketplace--v<version>`. Nothing is pushed.
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


def _require_clean_tree() -> str | None:
    status = repo.run(["git", "status", "--porcelain"]).stdout.strip()
    return (
        None
        if not status
        else "the working tree has uncommitted changes; commit or stash them first"
    )


def rewrite_changelog(text: str, version: str, date: str) -> str:
    """Move the Unreleased notes under a new `## [version] - date` heading."""
    lines = text.splitlines()
    start = lines.index("## [Unreleased]")
    end = next(
        (i for i in range(start + 1, len(lines)) if lines[i].startswith("## [")),
        len(lines),
    )
    notes = "\n".join(lines[start + 1 : end]).strip()
    head = lines[: start + 1]
    tail = lines[end:]
    block = ["", f"## [{version}] - {date}", "", *notes.splitlines(), ""]
    return "\n".join([*head, *block, *tail]).rstrip("\n") + "\n"


def prepare(changelog_path: Path, current: str, level: str) -> tuple[str, str] | str:
    """Return (new_version, new_changelog_text) or an error message."""
    text = changelog_path.read_text(encoding="utf-8")
    changelog = repo.parse_changelog(text)
    if changelog.problems:
        return f"{changelog_path}: " + "; ".join(changelog.problems)
    if not changelog.unreleased:
        return f"{changelog_path}: ## [Unreleased] is empty; nothing to release"
    if changelog.releases and changelog.releases[0].version != current:
        return f"{changelog_path}: latest release {changelog.releases[0].version} does not match current version {current}"
    if level == "major" and not repo.has_section_content(
        changelog.unreleased, "Migration"
    ):
        return f'{changelog_path}: a major release needs a non-empty "### Migration" section'
    new_version = repo.bump(current, level)
    today = dt.datetime.now(dt.UTC).date().isoformat()
    return new_version, rewrite_changelog(text, new_version, today)


def _set_version(path: Path, version: str) -> None:
    data = repo.as_dict(repo.load_json(path))
    if data is None:
        raise SystemExit(f"{path} is not a JSON object")
    updated: dict[str, JSON] = {
        key: (version if key == "version" else value) for key, value in data.items()
    }
    repo.dump_json(path, updated)


def _commit_and_tag(
    paths: list[Path], message: str, tag_args: list[str], tag: str
) -> int:
    _ = repo.run(["git", "add", *[str(p) for p in paths]])
    commit = repo.run(["git", "commit", "-m", message], check=False)
    print(commit.stdout.strip() or commit.stderr.strip())
    if commit.returncode != 0:
        return _fail("git commit failed; fix the cause (signing, hooks) and retry")
    tagged = repo.run(tag_args, check=False)
    print(tagged.stdout.strip() or tagged.stderr.strip())
    if tagged.returncode != 0:
        return _fail(f"tagging failed: {' '.join(tag_args)}")
    verify = repo.run(["git", "tag", "-v", tag], check=False)
    if verify.returncode != 0:
        print(verify.stderr.strip())
        return _fail(f"tag {tag} is not signed or its signature does not verify")
    print(f"✔ {tag} created and signed. Push when approved: git push origin main {tag}")
    return 0


def release_plugin(name: str, level: str, dry_run: bool) -> int:
    plugin = repo.PLUGINS_DIR / name
    manifest_path = plugin / ".claude-plugin" / "plugin.json"
    if not manifest_path.is_file():
        return _fail(f"unknown plugin {name}")
    manifest = repo.as_dict(repo.load_json(manifest_path)) or {}
    current = repo.as_str(manifest.get("version")) or ""
    prepared = prepare(plugin / "CHANGELOG.md", current, level)
    if isinstance(prepared, str):
        return _fail(prepared)
    new_version, changelog_text = prepared
    tag = repo.plugin_tag(name, new_version)
    print(f"{name}: {current} → {new_version} ({level}); tag {tag}")
    if dry_run:
        print(changelog_text)
        return 0
    problem = _require_clean_tree()
    if problem:
        return _fail(problem)
    _ = (plugin / "CHANGELOG.md").write_text(changelog_text, encoding="utf-8")
    _set_version(manifest_path, new_version)
    for command in (
        ["claude", "plugin", "validate", str(plugin), "--strict"],
        ["uv", "run", str(repo.ROOT / "scripts" / "check_repo.py")],
    ):
        result = repo.run(command, check=False)
        if result.returncode != 0:
            print(result.stdout + result.stderr)
            return _fail(
                f"{' '.join(command)} failed; the release files are modified but not committed"
            )
    return _commit_and_tag(
        [plugin / "CHANGELOG.md", manifest_path],
        f"chore({name}): release {new_version}",
        ["claude", "plugin", "tag", str(plugin)],
        tag,
    )


def release_marketplace(level: str, dry_run: bool) -> int:
    data = repo.as_dict(repo.load_json(repo.MARKETPLACE_FILE)) or {}
    current = repo.as_str(data.get("version")) or ""
    changelog_path = repo.ROOT / "CHANGELOG.md"
    prepared = prepare(changelog_path, current, level)
    if isinstance(prepared, str):
        return _fail(prepared)
    new_version, changelog_text = prepared
    tag = repo.plugin_tag(repo.MARKETPLACE_TAG_NAME, new_version)
    print(f"marketplace: {current} → {new_version} ({level}); tag {tag}")
    if dry_run:
        print(changelog_text)
        return 0
    problem = _require_clean_tree()
    if problem:
        return _fail(problem)
    _ = changelog_path.write_text(changelog_text, encoding="utf-8")
    _set_version(repo.MARKETPLACE_FILE, new_version)
    return _commit_and_tag(
        [changelog_path, repo.MARKETPLACE_FILE],
        f"chore(marketplace): release {new_version}",
        ["git", "tag", "-a", tag, "-m", f"marketplace {new_version}"],
        tag,
    )


def release_notes(tag: str) -> int:
    parts = repo.split_tag(tag)
    if parts is None:
        return _fail(f'"{tag}" is not a <name>--v<version> tag')
    name, version = parts
    path = (
        repo.ROOT / "CHANGELOG.md"
        if name == repo.MARKETPLACE_TAG_NAME
        else repo.PLUGINS_DIR / name / "CHANGELOG.md"
    )
    if not path.is_file():
        return _fail(f"{path} not found")
    changelog = repo.parse_changelog(path.read_text(encoding="utf-8"))
    for release in changelog.releases:
        if release.version == version:
            print(release.body)
            return 0
    return _fail(f"{path} has no section for {version}")


def verify_tag(tag: str) -> int:
    """CI: the pushed tag must name an existing plugin (or the marketplace) at its current version."""
    parts = repo.split_tag(tag)
    if parts is None:
        return _fail(f'"{tag}" is not a <name>--v<version> tag')
    name, version = parts
    if name == repo.MARKETPLACE_TAG_NAME:
        source = repo.MARKETPLACE_FILE
    else:
        source = repo.PLUGINS_DIR / name / ".claude-plugin" / "plugin.json"
    if not source.is_file():
        return _fail(f"{tag}: {source} does not exist")
    data = repo.as_dict(repo.load_json(source)) or {}
    declared = repo.as_str(data.get("version"))
    if declared != version:
        return _fail(
            f'{tag}: {source.relative_to(repo.ROOT)} declares version "{declared}"'
        )
    print(f"✔ {tag} matches {source.relative_to(repo.ROOT)}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest="command", required=True)
    plugin_parser = sub.add_parser("plugin", help="release one plugin")
    _ = plugin_parser.add_argument("name")
    _ = plugin_parser.add_argument("level", choices=LEVELS)
    _ = plugin_parser.add_argument("--dry-run", action="store_true")
    market_parser = sub.add_parser(
        "marketplace", help="release the marketplace catalog"
    )
    _ = market_parser.add_argument("level", choices=LEVELS)
    _ = market_parser.add_argument("--dry-run", action="store_true")
    notes_parser = sub.add_parser("notes", help="print release notes for a tag")
    _ = notes_parser.add_argument("tag")
    verify_parser = sub.add_parser(
        "verify", help="CI: check a tag against the manifest version"
    )
    _ = verify_parser.add_argument("tag")
    args = parser.parse_args()
    command: str = args.command  # pyright: ignore[reportAny]  # argparse Namespace attributes are Any
    if command in ("notes", "verify"):
        tag: str = args.tag  # pyright: ignore[reportAny]  # argparse Namespace attributes are Any
        return release_notes(tag) if command == "notes" else verify_tag(tag)
    level: str = args.level  # pyright: ignore[reportAny]  # argparse Namespace attributes are Any
    dry_run: bool = args.dry_run  # pyright: ignore[reportAny]  # argparse Namespace attributes are Any
    if command == "plugin":
        name: str = args.name  # pyright: ignore[reportAny]  # argparse Namespace attributes are Any
        return release_plugin(name, level, dry_run)
    return release_marketplace(level, dry_run)


if __name__ == "__main__":
    sys.exit(main())
