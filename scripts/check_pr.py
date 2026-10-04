# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Release-discipline gate for a pull request (docs/releasing.md).

Usage:
  uv run scripts/check_pr.py --base <sha> --head <sha> --title "<title>" --labels "a,b"

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


def changed_files(base: str, head: str) -> list[str]:
    output = repo.run(["git", "diff", "--name-only", f"{base}...{head}"]).stdout
    return [line for line in output.splitlines() if line]


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


def check(base: str, head: str, title: str, labels: list[str]) -> list[str]:
    problems: list[str] = []
    files = changed_files(base, head)
    plugins = sorted(
        {
            path.split("/")[1]
            for path in files
            if path.startswith("plugins/") and path.count("/") >= 2
        }
    )

    parsed, title_problems = check_commit_msg.parse(title)
    problems.extend(f"title: {problem}" for problem in title_problems)

    semver = [label for label in labels if label in SEMVER_LABELS]
    if plugins and len(semver) != 1:
        problems.append(
            f"pull requests that change plugins need exactly one of {', '.join(SEMVER_LABELS)} (found {semver or 'none'})"
        )
    if len(plugins) == 1 and parsed is not None and parsed.scope != plugins[0]:
        problems.append(
            f'title scope must be the plugin name: "{parsed.type}({plugins[0]}): …"'
        )
    if parsed is not None and parsed.breaking and "semver:major" not in semver:
        problems.append(
            "a breaking change (! or BREAKING CHANGE) needs the semver:major label"
        )

    for plugin in plugins:
        head_log = _changelog_at(head, plugin)
        if head_log is None:
            continue  # plugin removed: marketplace renames are checked by check_repo
        base_log = _changelog_at(base, plugin)
        base_version = _version_at(base, plugin)
        head_version = _version_at(head, plugin)
        if base_log is None:
            # A new plugin: the scaffold writes its first release section.
            continue
        if base_version != head_version:
            released = head_log.releases[0] if head_log.releases else None
            if released is None or released.version != head_version:
                problems.append(
                    f'{plugin}: version changed to "{head_version}" without a matching CHANGELOG release section; use scripts/bump_version.py'
                )
            if head_log.unreleased:
                problems.append(
                    f"{plugin}: a release must move every [Unreleased] note into the release section"
                )
            continue
        if head_log.unreleased == base_log.unreleased or not head_log.unreleased:
            problems.append(
                f"{plugin}: add a user-facing note under ## [Unreleased] in plugins/{plugin}/CHANGELOG.md"
            )
        if "semver:major" in semver and not repo.has_section_content(
            head_log.unreleased, "Migration"
        ):
            problems.append(
                f"{plugin}: semver:major needs a non-empty ### Migration section under [Unreleased]"
            )
    return problems


def main() -> int:
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
        print(f"✘ {problem}")
    if problems:
        return 1
    print("check_pr: release discipline satisfied")
    return 0


if __name__ == "__main__":
    sys.exit(main())
