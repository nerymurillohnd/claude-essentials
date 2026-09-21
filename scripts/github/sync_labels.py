"""Reconcile the GitHub label taxonomy with `.github/labels.json`, dry run by default.

The `Labels` workflow runs this with `--apply` after a merge to `main`, and never with
`--prune`: deleting a label strips it from every issue it was ever on, so pruning stays a
manual, previewed step (ADR-0004). Running it with no flags reads the API and prints the
plan, which is what a maintainer does before changing the taxonomy.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import os
import sys
from typing import TYPE_CHECKING
from urllib.parse import quote

from scripts.common.errors import ExitCode, MaintainerError
from scripts.common.jsontext import is_json_object
from scripts.common.plugins import repo_root
from scripts.github.client import (
    GitHubClient,
    repository_from_env,
    token_from_env,
)
from scripts.github.labels import Label, LabelPlan, desired_labels, plan, plan_lines

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

PER_PAGE = 100
"""The largest page the labels endpoint serves."""


@dataclass(frozen=True, slots=True)
class Options:
    """Parsed command line.

    Attributes:
        apply: Send the plan to GitHub instead of printing it.
        prune: Include deletions; only ever combined with `apply` by a human.
    """

    apply: bool
    prune: bool


def parse_args(argv: Sequence[str] | None) -> Options:
    """Parse the command line.

    Args:
        argv: Arguments without the program name; `sys.argv[1:]` when None.

    Returns:
        The options.

    Raises:
        SystemExit: If argparse refuses the arguments.
    """
    parser = argparse.ArgumentParser(
        prog="python -m scripts.github.sync_labels",
        description="Reconcile the GitHub labels with .github/labels.json (dry run by default).",
    )
    _ = parser.add_argument("--apply", action="store_true", help="send the plan to GitHub")
    _ = parser.add_argument(
        "--prune",
        action="store_true",
        help="include deletions of labels the taxonomy no longer declares",
    )
    values: dict[str, object] = vars(parser.parse_args(argv))
    return Options(apply=bool(values["apply"]), prune=bool(values["prune"]))


def remote_labels(client: GitHubClient) -> tuple[Label, ...]:
    """Read every label the repository currently carries.

    Args:
        client: The API client.

    Returns:
        One label per remote label, with no aliases (GitHub does not store them).
    """
    items = client.get_all(f"/repos/{client.repo}/labels?per_page={PER_PAGE}")
    labels: list[Label] = []
    for item in items:
        if not is_json_object(item):
            continue
        name = item.get("name")
        color = item.get("color")
        description = item.get("description")
        if not isinstance(name, str) or not isinstance(color, str):
            continue
        labels.append(
            Label(
                name=name,
                color=color,
                description=description if isinstance(description, str) else "",
            ),
        )
    return tuple(labels)


def _create_lines(client: GitHubClient, base: str, label_plan: LabelPlan) -> list[str]:
    """Send every creation in a plan.

    Args:
        client: The API client.
        base: The labels endpoint of the repository.
        label_plan: What to change.

    Returns:
        One line per request actually sent.
    """
    return [
        f"created {label.name}"
        for label in label_plan.creates
        if client.mutate(
            "POST",
            base,
            {"name": label.name, "color": label.color, "description": label.description},
        )
    ]


def _update_lines(client: GitHubClient, base: str, label_plan: LabelPlan) -> list[str]:
    """Send every color or description change in a plan.

    Args:
        client: The API client.
        base: The labels endpoint of the repository.
        label_plan: What to change.

    Returns:
        One line per request actually sent.
    """
    return [
        f"updated {label.name}"
        for label in label_plan.updates
        if client.mutate(
            "PATCH",
            f"{base}/{_escape(label.name)}",
            {"color": label.color, "description": label.description},
        )
    ]


def _rename_lines(client: GitHubClient, base: str, label_plan: LabelPlan) -> list[str]:
    """Rename every label a taxonomy alias points at, keeping it on its issues.

    Args:
        client: The API client.
        base: The labels endpoint of the repository.
        label_plan: What to change.

    Returns:
        One line per request actually sent.
    """
    return [
        f"renamed {old} -> {label.name}"
        for old, label in label_plan.renames
        if client.mutate(
            "PATCH",
            f"{base}/{_escape(old)}",
            {
                "new_name": label.name,
                "color": label.color,
                "description": label.description,
            },
        )
    ]


def apply_plan(client: GitHubClient, label_plan: LabelPlan, *, prune: bool) -> list[str]:
    """Send a plan to GitHub, one request per action.

    Args:
        client: The API client; it refuses every write unless it was built with `apply`.
        label_plan: What to change.
        prune: Whether deletions are included.

    Returns:
        One line per action actually sent.
    """
    base = f"/repos/{client.repo}/labels"
    sent = [
        *_create_lines(client, base, label_plan),
        *_update_lines(client, base, label_plan),
        *_rename_lines(client, base, label_plan),
    ]
    if prune:
        sent.extend(
            f"pruned {name}"
            for name in label_plan.prunes
            if client.mutate("DELETE", f"{base}/{_escape(name)}")
        )
    return sent


def _escape(name: str) -> str:
    """Percent-encode a label name for a URL path segment.

    Args:
        name: The label name, which normally contains a space and a colon.

    Returns:
        The encoded segment.
    """
    return quote(name, safe="")


def build_client(root: Path, *, apply: bool) -> GitHubClient:
    """Build the API client from the environment.

    Args:
        root: The repository root, used to derive `owner/name` from `origin`.
        apply: Whether this client may send writes.

    Returns:
        The client.

    Raises:
        GitHubTokenMissingError: If no token is available.
        GitHubRepositoryUnknownError: If the slug cannot be determined.
    """
    env = dict(os.environ)
    return GitHubClient(
        repo=repository_from_env(env, root),
        token=token_from_env(env),
        apply=apply,
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Print or apply the label plan.

    Args:
        argv: Arguments without the program name; `sys.argv[1:]` when None.

    Returns:
        0 on a clean run, 2 when the environment or the API refuses.
    """
    options = parse_args(argv)
    try:
        root = repo_root()
        client = build_client(root, apply=options.apply)
        label_plan = plan(desired_labels(root), remote_labels(client))
    except (MaintainerError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return int(ExitCode.USAGE)
    for line in plan_lines(label_plan):
        print(line)
    if not options.apply:
        if label_plan.prunes and not options.prune:
            print(f"({len(label_plan.prunes)} label(s) would be pruned; pruning is manual)")
        return int(ExitCode.OK)
    try:
        for line in apply_plan(client, label_plan, prune=options.prune):
            print(line)
    except (MaintainerError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return int(ExitCode.USAGE)
    return int(ExitCode.OK)


if __name__ == "__main__":
    raise SystemExit(main())
