"""Apply the triage rules to one GitHub event, dry run by default (ADR-0004).

The workflow that runs this holds a write token and is triggered by `pull_request_target`, so
the one hard rule is that nothing from the pull request's head is ever executed. Everything
this entrypoint learns about a pull request comes through the API as data: the changed file
list, the current labels, the issue body.

**The `bump:` label and the base checkout.** `check_versions` answers "what does this working
tree owe against this base", so it is only meaningful when the checkout actually contains the
pull request's changes. This entrypoint therefore computes the label only when `HEAD` is the
event's head or merge commit, or when the caller supplies the JSON with `--versions-json`. In
a base-only checkout it applies no `bump:` label at all rather than a confident `bump: none`
that would be wrong on every pull request. The workflow that feeds it is rewired at step 7 of
the migration; until then this is the honest behaviour.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import TYPE_CHECKING, Final
from urllib.parse import quote

from scripts.common.errors import ExitCode, MaintainerError
from scripts.common.jsontext import is_json_array, is_json_object
from scripts.common.plugins import git_output_or_none, parse_json, plugin_ids, repo_root
from scripts.github.client import GitHubClient, repository_from_env, token_from_env
from scripts.github.labels import replaced_bump_labels
from scripts.github.triage_rules import (
    CommentEvent,
    bump_label,
    labels_for_issue,
    labels_for_pr,
    parse_form_answers,
    reply_label_changes,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

EVENT_PATH_VARIABLE: Final = "GITHUB_EVENT_PATH"
"""Where Actions writes the event payload."""

EVENT_NAME_VARIABLE: Final = "GITHUB_EVENT_NAME"
"""Which event fired; the payload alone does not say."""

PER_PAGE: Final = 100
"""The largest page the pull-request files endpoint serves."""

VERSIONS_MODULE: Final = "scripts.versioning.check_versions"
"""The single home of the bump rules; triage never reimplements them."""


@dataclass(frozen=True, slots=True)
class Options:
    """Parsed command line.

    Attributes:
        apply: Send the label changes instead of printing them.
        versions_json: A file holding `check_versions --json` output, or None to compute it.
    """

    apply: bool
    versions_json: Path | None


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
        prog="python -m scripts.github.triage",
        description="Label one GitHub event from the ADR-0004 rules (dry run by default).",
    )
    _ = parser.add_argument("--apply", action="store_true", help="send the label changes")
    _ = parser.add_argument(
        "--versions-json",
        default=None,
        help="read the computed bump from this file instead of running check_versions",
    )
    values: dict[str, object] = vars(parser.parse_args(argv))
    raw = values["versions_json"]
    return Options(
        apply=bool(values["apply"]),
        versions_json=Path(raw) if isinstance(raw, str) else None,
    )


def load_event(env: dict[str, str]) -> object:
    """Read the event payload Actions wrote.

    Args:
        env: The process environment.

    Returns:
        The parsed payload, or None when the variable is unset or the file is missing.
    """
    raw = env.get(EVENT_PATH_VARIABLE)
    if raw is None:
        return None
    path = Path(raw)
    if not path.is_file():
        return None
    return parse_json(path.read_text(encoding="utf-8"), path=path)


def _login(value: object) -> str:
    """Read a `user.login` out of a payload fragment.

    Args:
        value: The fragment holding a `user` object.

    Returns:
        The login, or the empty string when it is absent.
    """
    if not is_json_object(value):
        return ""
    user = value.get("user")
    if not is_json_object(user):
        return ""
    login = user.get("login")
    return login if isinstance(login, str) else ""


def _label_names(value: object) -> frozenset[str]:
    """Read a `labels` array out of a payload fragment.

    Args:
        value: The fragment holding a `labels` array.

    Returns:
        The label names.
    """
    if not is_json_object(value):
        return frozenset()
    labels = value.get("labels")
    if not is_json_array(labels):
        return frozenset()
    names: set[str] = set()
    for item in labels:
        if is_json_object(item):
            name = item.get("name")
            if isinstance(name, str):
                names.add(name)
        elif isinstance(item, str):
            names.add(item)
    return frozenset(names)


def _number(value: object) -> int | None:
    """Read an issue or pull-request number out of a payload fragment.

    Args:
        value: The fragment holding a `number`.

    Returns:
        The number, or None when it is absent.
    """
    if not is_json_object(value):
        return None
    number = value.get("number")
    return number if isinstance(number, int) and not isinstance(number, bool) else None


def comment_event(event: object) -> CommentEvent | None:
    """Narrow an `issue_comment` payload into the fields the reply rule reads.

    Args:
        event: The parsed payload.

    Returns:
        The narrowed event, or None when the payload is not a comment on an issue.
    """
    if not is_json_object(event):
        return None
    issue = event.get("issue")
    comment = event.get("comment")
    if not is_json_object(issue) or not is_json_object(comment):
        return None
    return CommentEvent(
        issue_author=_login(issue),
        comment_author=_login(comment),
        issue_labels=_label_names(issue),
    )


def issue_body(event: object) -> str:
    """Read the body of the issue an event is about.

    Args:
        event: The parsed payload.

    Returns:
        The body text, or the empty string.
    """
    if not is_json_object(event):
        return ""
    issue = event.get("issue")
    if not is_json_object(issue):
        return ""
    body = issue.get("body")
    return body if isinstance(body, str) else ""


def head_sha(event: object) -> set[str]:
    """Return the commits that would make a checkout contain the pull request's changes.

    Args:
        event: The parsed payload.

    Returns:
        The head and merge commit shas the payload carries.
    """
    if not is_json_object(event):
        return set()
    pull = event.get("pull_request")
    if not is_json_object(pull):
        return set()
    shas: set[str] = set()
    head = pull.get("head")
    if is_json_object(head):
        sha = head.get("sha")
        if isinstance(sha, str):
            shas.add(sha)
    merge = pull.get("merge_commit_sha")
    if isinstance(merge, str):
        shas.add(merge)
    return shas


def base_ref(event: object) -> str | None:
    """Return the ref a pull request is measured against.

    Args:
        event: The parsed payload.

    Returns:
        `origin/<base>`, or None when the payload carries no base.
    """
    if not is_json_object(event):
        return None
    pull = event.get("pull_request")
    if not is_json_object(pull):
        return None
    base = pull.get("base")
    if not is_json_object(base):
        return None
    ref = base.get("ref")
    return f"origin/{ref}" if isinstance(ref, str) else None


def changed_files(client: GitHubClient, number: int) -> list[str]:
    """List the files a pull request touches, read through the API as data.

    Args:
        client: The API client.
        number: The pull request number.

    Returns:
        The repository-relative paths.
    """
    items = client.get_all(f"/repos/{client.repo}/pulls/{number}/files?per_page={PER_PAGE}")
    paths: list[str] = []
    for item in items:
        if is_json_object(item):
            filename = item.get("filename")
            if isinstance(filename, str):
                paths.append(filename)
    return paths


def run_check_versions(root: Path, base: str) -> object:
    """Run the version gate in this checkout and return its JSON contract.

    Args:
        root: The repository root.
        base: The ref to measure against.

    Returns:
        The parsed document, or None when the command could not run.
    """
    completed = subprocess.run(
        [sys.executable, "-m", VERSIONS_MODULE, "--base", base, "--json"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if not completed.stdout.strip():
        return None
    return parse_json(completed.stdout, path=root)


def versions_document(root: Path, event: object, options: Options) -> object:
    """Obtain the `check_versions --json` document, or None when it cannot be trusted.

    Args:
        root: The repository root.
        event: The parsed payload.
        options: The command line.

    Returns:
        The parsed document, or None when this checkout does not hold the pull request's
        changes and no document was supplied.
    """
    if options.versions_json is not None:
        return parse_json(
            options.versions_json.read_text(encoding="utf-8"), path=options.versions_json
        )
    base = base_ref(event)
    if base is None:
        return None
    current = git_output_or_none(root, ["rev-parse", "HEAD"])
    if current is None or current.strip() not in head_sha(event):
        return None
    return run_check_versions(root, base)


def _escape(name: str) -> str:
    """Percent-encode a label name for a URL path segment.

    Args:
        name: The label name.

    Returns:
        The encoded segment.
    """
    return quote(name, safe="")


def apply_changes(
    client: GitHubClient,
    number: int,
    *,
    add: Sequence[str],
    remove: Sequence[str],
) -> list[str]:
    """Add and remove labels on one issue or pull request.

    Args:
        client: The API client; every write is a no-op unless it was built with `apply`.
        number: The issue or pull request number.
        add: Labels to add.
        remove: Labels to remove.

    Returns:
        One line per request actually sent.
    """
    sent: list[str] = []
    base = f"/repos/{client.repo}/issues/{number}/labels"
    if add and client.mutate("POST", base, {"labels": list(add)}):
        sent.append(f"added {', '.join(add)}")
    sent.extend(
        f"removed {name}" for name in remove if client.mutate("DELETE", f"{base}/{_escape(name)}")
    )
    return sent


def plan_for_event(
    root: Path,
    client: GitHubClient,
    event: object,
    options: Options,
    event_name: str,
) -> tuple[int | None, list[str], list[str]]:
    """Decide what to change for one event.

    Args:
        root: The repository root.
        client: The API client, used for reads only here.
        event: The parsed payload.
        options: The command line.
        event_name: The Actions event name.

    Returns:
        The issue or pull request number, the labels to add and the labels to remove.
    """
    if event_name == "issue_comment":
        narrowed = comment_event(event)
        if narrowed is None:
            return None, [], []
        add, remove = reply_label_changes(narrowed)
        number = _number(event.get("issue") if is_json_object(event) else None)
        return number, sorted(add), sorted(remove)
    if event_name == "issues":
        number = _number(event.get("issue") if is_json_object(event) else None)
        answers = parse_form_answers(issue_body(event))
        return number, sorted(labels_for_issue(answers, known_plugins=plugin_ids(root))), []
    pull = event.get("pull_request") if is_json_object(event) else None
    number = _number(pull)
    if number is None:
        return None, [], []
    versions = versions_document(root, event, options)
    desired = labels_for_pr(changed_files(client, number), versions)
    current = _label_names(pull)
    remove = replaced_bump_labels(current, bump_label(versions))
    return number, sorted(desired - current), remove


def main(argv: Sequence[str] | None = None) -> int:
    """Label one event.

    Args:
        argv: Arguments without the program name; `sys.argv[1:]` when None.

    Returns:
        0 on a clean run, 2 when the environment or the API refuses.
    """
    options = parse_args(argv)
    env = dict(os.environ)
    try:
        root = repo_root()
        event = load_event(env)
        client = GitHubClient(
            repo=repository_from_env(env, root),
            token=token_from_env(env),
            apply=options.apply,
        )
        number, add, remove = plan_for_event(
            root, client, event, options, env.get(EVENT_NAME_VARIABLE, "")
        )
    except (MaintainerError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return int(ExitCode.USAGE)
    if number is None:
        print("triage: no issue or pull request in this event")
        return int(ExitCode.OK)
    print(json.dumps({"number": number, "add": add, "remove": remove}, indent=2))
    if not options.apply:
        return int(ExitCode.OK)
    try:
        for line in apply_changes(client, number, add=add, remove=remove):
            print(line)
    except (MaintainerError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return int(ExitCode.USAGE)
    return int(ExitCode.OK)


if __name__ == "__main__":
    raise SystemExit(main())
