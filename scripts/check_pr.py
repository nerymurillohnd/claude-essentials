#!/usr/bin/env python3
"""Release-discipline gate for a pull request (docs/releasing.md).

Usage:
  scripts/check_pr.py --base <sha> --head <sha> --title "<title>" --labels "a,b"

Every change inside plugins/<name>/ reaches users only with a new version, so it
ships with its own release in the same pull request:
  * each changed existing plugin's `version` moves by exactly one bump, prepared
    with scripts/bump_version.py: the matching dated CHANGELOG section exists,
    `## [Unreleased]` is empty, and a major release has a non-empty
    `### Migration` section;
  * exactly one `semver:major|minor|patch` label names the highest bump among
    the released plugins, and a breaking title (`!`) needs `semver:major`;
  * a new plugin starts at the version its scaffold wrote and needs no label;
  * a change to .claude-plugin/marketplace.json comes with a note in the dated
    catalog CHANGELOG.md (the catalog has no version);
  * the title is a Conventional Commit whose scope is the plugin name when exactly
    one plugin changes.
"""

from __future__ import annotations

import argparse
import json
import sys

import check_commit_msg
import repo
from repo import JSON

SEMVER_LABELS = ("semver:major", "semver:minor", "semver:patch")
CATALOG_FILE = ".claude-plugin/marketplace.json"
CATALOG_CHANGELOG = "CHANGELOG.md"
# A path inside a plugin has at least two separators: plugins/<name>/<file>.
_PLUGIN_PATH_SEPARATORS = 2


def changed_files(base: str, head: str) -> list[str]:
    """Paths changed between the pull request base and head."""
    output = repo.run(["git", "diff", "--name-only", f"{base}...{head}"]).stdout
    return [line for line in output.splitlines() if line]


def changed_plugins(files: list[str]) -> list[str]:
    """Names of the plugins whose files changed."""
    return sorted(
        {
            path.split("/")[1]
            for path in files
            if path.startswith("plugins/") and path.count("/") >= _PLUGIN_PATH_SEPARATORS
        }
    )


def _version_at(ref: str, plugin: str) -> str | None:
    text = repo.git_show(ref, f"plugins/{plugin}/.claude-plugin/plugin.json")
    if text is None:
        return None
    data: JSON = json.loads(text)  # pyright: ignore[reportAny]  # json.loads decodes only JSON types
    manifest = repo.as_dict(data)
    return repo.as_str(manifest.get("version")) if manifest else None


def _changelog_at(ref: str, plugin: str) -> repo.Changelog | None:
    text = repo.git_show(ref, f"plugins/{plugin}/CHANGELOG.md")
    return repo.parse_changelog(text) if text is not None else None


def title_problems(title: str, plugins: list[str], semver: list[str]) -> list[str]:
    """Conventional Commit title, plugin scope and breaking-change label."""
    parsed, problems = check_commit_msg.parse(title)
    found = [f"title: {problem}" for problem in problems]
    if parsed is None:
        return found
    if len(plugins) == 1 and parsed.scope != plugins[0]:
        found.append(f'title scope must be the plugin name: "{parsed.type}({plugins[0]}): …"')
    if parsed.breaking and "semver:major" not in semver:
        found.append("a breaking change (! or BREAKING CHANGE) needs the semver:major label")
    return found


def release_problems(
    plugin: str,
    versions: tuple[str | None, str | None],
    head_log: repo.Changelog,
) -> list[str]:
    """Problems of an existing plugin changed by the pull request without its release."""
    base_version, head_version = versions
    fix = f"run scripts/bump_version.py plugin {plugin} <level> in this pull request"
    if base_version is None or head_version is None:
        return [f"{plugin}: plugin.json has no version"]
    if base_version == head_version:
        return [f"{plugin}: every change inside plugins/{plugin}/ needs a new version; {fix}"]
    level = repo.bump_level(base_version, head_version)
    if level is None:
        return [f"{plugin}: {base_version} → {head_version} is not a single SemVer bump; {fix}"]
    problems: list[str] = []
    released = head_log.releases[0] if head_log.releases else None
    if released is None or released.version != head_version:
        problems.append(f"{plugin}: no CHANGELOG section for {head_version}; {fix}")
    if head_log.unreleased:
        problems.append(f"{plugin}: move every [Unreleased] note into the release section; {fix}")
    body = released.body if released else ""
    if level == "major" and not repo.has_section_content(body, "Migration"):
        problems.append(f"{plugin}: a major release needs a non-empty ### Migration section")
    return problems


def label_problems(levels: list[str], semver: list[str]) -> list[str]:
    """The single semver: label names the highest bump among the released plugins."""
    found = ", ".join(semver) or "none"
    if not levels:
        if semver:
            return [f"semver: labels apply only to plugin releases (found {found})"]
        return []
    highest = next(level for level in ("major", "minor", "patch") if level in levels)
    if semver != [f"semver:{highest}"]:
        return [f"the highest bump is {highest}: apply exactly semver:{highest} (found {found})"]
    return []


def catalog_problems(files: list[str]) -> list[str]:
    """A catalog change comes with a note in the dated catalog changelog."""
    if CATALOG_FILE in files and CATALOG_CHANGELOG not in files:
        return [f"{CATALOG_FILE} changed: add a dated note to {CATALOG_CHANGELOG}"]
    return []


def check(base: str, head: str, title: str, labels: list[str]) -> list[str]:
    """Return every release-discipline problem of the pull request."""
    files = changed_files(base, head)
    plugins = changed_plugins(files)
    semver = [label for label in labels if label in SEMVER_LABELS]
    problems = title_problems(title, plugins, semver) + catalog_problems(files)
    levels: list[str] = []
    for plugin in plugins:
        versions = (_version_at(base, plugin), _version_at(head, plugin))
        if versions[0] is None or versions[1] is None:
            continue  # a new or removed plugin is not a release
        head_log = _changelog_at(head, plugin) or repo.Changelog()
        problems.extend(release_problems(plugin, versions, head_log))
        level = repo.bump_level(versions[0], versions[1])
        if level is not None:
            levels.append(level)
    return problems + label_problems(levels, semver)


def main() -> int:
    """Parse the command line and report every problem."""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    _ = parser.add_argument("--base", required=True)
    _ = parser.add_argument("--head", required=True)
    _ = parser.add_argument("--title", required=True)
    _ = parser.add_argument("--labels", default="", help="comma-separated label names")
    args = parser.parse_args()
    base: str = args.base  # pyright: ignore[reportAny]  # argparse Namespace attributes are Any
    head: str = args.head  # pyright: ignore[reportAny]  # argparse Namespace attributes are Any
    title: str = args.title  # pyright: ignore[reportAny]  # argparse Namespace attributes are Any
    labels_arg: str = args.labels  # pyright: ignore[reportAny]  # argparse Namespace attributes are Any
    labels = [label.strip() for label in labels_arg.split(",") if label.strip()]
    problems = check(base, head, title, labels)
    for problem in problems:
        repo.emit(f"✘ {problem}")
    if problems:
        return 1
    repo.emit("check_pr: release discipline satisfied")
    return 0


if __name__ == "__main__":
    sys.exit(main())
