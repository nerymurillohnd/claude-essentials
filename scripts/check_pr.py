#!/usr/bin/env python3
"""Release-discipline gate for a pull request (docs/releasing.md).

Usage:
  python3 scripts/check_pr.py --base <sha> --head <sha> --title "<title>" --labels "a,b"

Rules for every plugin whose files the pull request changes:
  * a feature or fix PR adds notes under `## [Unreleased]` in that plugin's CHANGELOG.md
    and must not change `version` (versions change only in release PRs);
  * a release PR (prepared with scripts/bump_version.py) bumps `version` and adds the matching
    dated CHANGELOG section;
  * exactly one `semver:major|minor|patch` label is applied, `semver:major` requires a
    non-empty `### Migration` section, and a breaking title (`!`) requires `semver:major`;
  * the title is a Conventional Commit whose scope is the plugin name when exactly one
    plugin changes.
"""

from __future__ import annotations

import argparse
import json
import sys

import check_commit_msg
import repo
from repo import JSON

SEMVER_LABELS = ("semver:major", "semver:minor", "semver:patch")
# A path inside a plugin has at least two separators: plugins/<name>/<file>.
_PLUGIN_PATH_SEPARATORS = 2


def changed_files(base: str, head: str) -> list[str]:
    """Paths changed between the pull request base and head."""
    output = repo.run(["git", "diff", "--name-only", f"{base}...{head}"]).stdout
    return [line for line in output.splitlines() if line]


def _changed_plugins(files: list[str]) -> list[str]:
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


def _label_and_title_problems(title: str, plugins: list[str], semver: list[str]) -> list[str]:
    parsed, title_problems = check_commit_msg.parse(title)
    problems = [f"title: {problem}" for problem in title_problems]
    if plugins and len(semver) != 1:
        found = semver or "none"
        options = ", ".join(SEMVER_LABELS)
        problems.append(
            f"pull requests that change plugins need exactly one of {options} (found {found})"
        )
    if parsed is None:
        return problems
    if len(plugins) == 1 and parsed.scope != plugins[0]:
        problems.append(f'title scope must be the plugin name: "{parsed.type}({plugins[0]}): …"')
    if parsed.breaking and "semver:major" not in semver:
        problems.append("a breaking change (! or BREAKING CHANGE) needs the semver:major label")
    return problems


def _release_problems(plugin: str, head_log: repo.Changelog, head_version: str | None) -> list[str]:
    problems: list[str] = []
    released = head_log.releases[0] if head_log.releases else None
    if released is None or released.version != head_version:
        changed = f'version changed to "{head_version}"'
        fix = "use scripts/bump_version.py"
        problems.append(f"{plugin}: {changed} without a matching release section; {fix}")
    if head_log.unreleased:
        problems.append(
            f"{plugin}: a release must move every [Unreleased] note into the release section"
        )
    return problems


def _plugin_problems(plugin: str, base: str, head: str, semver: list[str]) -> list[str]:
    head_log = _changelog_at(head, plugin)
    base_log = _changelog_at(base, plugin)
    if head_log is None or base_log is None:
        # Removed plugin (renames are checked by check_repo) or new plugin (the
        # scaffold writes its first release section).
        return []
    head_version = _version_at(head, plugin)
    if _version_at(base, plugin) != head_version:
        return _release_problems(plugin, head_log, head_version)
    problems: list[str] = []
    if head_log.unreleased == base_log.unreleased or not head_log.unreleased:
        changelog = f"plugins/{plugin}/CHANGELOG.md"
        problems.append(f"{plugin}: add a user-facing note under ## [Unreleased] in {changelog}")
    if "semver:major" in semver and not repo.has_section_content(head_log.unreleased, "Migration"):
        problems.append(
            f"{plugin}: semver:major needs a non-empty ### Migration section under [Unreleased]"
        )
    return problems


def check(base: str, head: str, title: str, labels: list[str]) -> list[str]:
    """Return every release-discipline problem of the pull request."""
    plugins = _changed_plugins(changed_files(base, head))
    semver = [label for label in labels if label in SEMVER_LABELS]
    problems = _label_and_title_problems(title, plugins, semver)
    for plugin in plugins:
        problems.extend(_plugin_problems(plugin, base, head, semver))
    return problems


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
