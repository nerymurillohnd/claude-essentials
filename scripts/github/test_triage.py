"""Tests for the triage entrypoint: narrowing, the dry run, and the base-checkout rule."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from scripts.common.errors import ExitCode
from scripts.github.client import AUTH_ENV_VARIABLE, REPOSITORY_VARIABLE
from scripts.github.conftest import FakeTransport, json_response
from scripts.github.triage import (
    EVENT_PATH_VARIABLE,
    Options,
    base_ref,
    changed_files,
    comment_event,
    head_sha,
    issue_body,
    load_event,
    main,
    parse_args,
    plan_for_event,
    versions_document,
)
from scripts.github.triage_rules import CATALOG_AREA, DOCS_AREA, NEEDS_INFO, NEEDS_TRIAGE

if TYPE_CHECKING:
    from pathlib import Path

    from scripts.github.client import GitHubClient

COMMENT_EVENT: dict[str, object] = {
    "issue": {
        "number": 7,
        "user": {"login": "reporter"},
        "labels": [{"name": NEEDS_INFO}],
        "body": "",
    },
    "comment": {"user": {"login": "reporter"}},
}
"""An author replying to a request for information."""

PULL_EVENT: dict[str, object] = {
    "pull_request": {
        "number": 12,
        "labels": [{"name": "bump: patch"}],
        "base": {"ref": "main"},
        "head": {"sha": "f" * 40},
        "merge_commit_sha": "e" * 40,
    },
}
"""A pull request whose head this checkout does not contain."""

PULL_NUMBER = 12
"""The number `PULL_EVENT` carries."""


def test_dry_run_is_the_default() -> None:
    """Running with no flags never writes."""
    assert parse_args([]).apply is False


def test_a_supplied_versions_document_is_read(tmp_path: Path) -> None:
    """The workflow can compute the bump elsewhere and hand it in."""
    path = tmp_path / "versions.json"
    _ = path.write_text(json.dumps({"label": "bump: minor"}), encoding="utf-8")
    options = Options(apply=False, versions_json=path)
    assert versions_document(tmp_path, PULL_EVENT, options) == {"label": "bump: minor"}


@pytest.mark.slow
def test_no_bump_is_computed_from_a_base_only_checkout(tmp_path: Path) -> None:
    """`check_versions` compares the working tree, so a base checkout knows nothing."""
    options = Options(apply=False, versions_json=None)
    assert versions_document(tmp_path, PULL_EVENT, options) is None


def test_load_event_returns_none_without_the_variable() -> None:
    """Running outside Actions is not an error; there is simply no event."""
    assert load_event({}) is None


def test_load_event_reads_the_payload(tmp_path: Path) -> None:
    """The payload is data, parsed as `object` and narrowed afterwards."""
    path = tmp_path / "event.json"
    _ = path.write_text(json.dumps({"action": "opened"}), encoding="utf-8")
    assert load_event({EVENT_PATH_VARIABLE: str(path)}) == {"action": "opened"}


def test_comment_event_narrows_the_payload() -> None:
    """Three fields decide the reply rule; nothing else is read."""
    narrowed = comment_event(COMMENT_EVENT)
    assert narrowed is not None
    assert narrowed.issue_author == "reporter"
    assert narrowed.comment_author == "reporter"
    assert narrowed.issue_labels == frozenset({NEEDS_INFO})


def test_comment_event_refuses_a_payload_without_a_comment() -> None:
    """An `issues` event is not a comment."""
    assert comment_event({"issue": {}}) is None


def test_head_sha_collects_both_commits() -> None:
    """A checkout at either one holds the pull request's changes."""
    assert head_sha(PULL_EVENT) == {"f" * 40, "e" * 40}


def test_base_ref_is_qualified_with_the_remote() -> None:
    """`check_versions` compares against a ref git can resolve after a fetch."""
    assert base_ref(PULL_EVENT) == "origin/main"


def test_issue_body_is_read_from_the_issue() -> None:
    """The form answers live there and nowhere else."""
    assert issue_body({"issue": {"body": "### Affected plugin\n\nalpha"}}).startswith("###")


def test_changed_files_are_read_through_the_api(
    client: GitHubClient, transport: FakeTransport
) -> None:
    """`pull_request_target` must never execute the head; the file list is data."""
    path = "/repos/owner/repo/pulls/12/files?per_page=100"
    transport.responses[path] = json_response([{"filename": "docs/x.md"}, {"status": "added"}])
    assert changed_files(client, PULL_NUMBER) == ["docs/x.md"]


def test_an_issue_event_earns_its_dropdown_label(tmp_path: Path, client: GitHubClient) -> None:
    """The catalog answer needs no plugin on disk."""
    event: dict[str, object] = {
        "issue": {
            "number": 3,
            "body": "### Affected plugin\n\nMarketplace catalog / installation\n",
        },
    }
    options = Options(apply=False, versions_json=None)
    number, add, remove = plan_for_event(tmp_path, client, event, options, "issues")
    assert (number, add, remove) == (3, [CATALOG_AREA], [])


def test_a_comment_event_moves_the_issue_back_to_triage(
    tmp_path: Path, client: GitHubClient
) -> None:
    """The label change an author's reply earns."""
    options = Options(apply=False, versions_json=None)
    number, add, remove = plan_for_event(tmp_path, client, COMMENT_EVENT, options, "issue_comment")
    assert (number, add, remove) == (7, [NEEDS_TRIAGE], [NEEDS_INFO])


@pytest.mark.slow
def test_a_pull_request_event_labels_from_the_changed_files(
    tmp_path: Path, client: GitHubClient, transport: FakeTransport
) -> None:
    """No bump is applied from a base checkout, and the stale one is removed."""
    path = "/repos/owner/repo/pulls/12/files?per_page=100"
    transport.responses[path] = json_response([{"filename": "docs/x.md"}])
    options = Options(apply=False, versions_json=None)
    number, add, remove = plan_for_event(
        tmp_path, client, PULL_EVENT, options, "pull_request_target"
    )
    assert number == PULL_NUMBER
    assert add == [DOCS_AREA]
    assert remove == ["bump: patch"]


def test_an_event_with_nothing_to_label_is_a_no_op(tmp_path: Path, client: GitHubClient) -> None:
    """A workflow_dispatch or an unrelated event must not raise."""
    options = Options(apply=False, versions_json=None)
    assert plan_for_event(tmp_path, client, {}, options, "push") == (None, [], [])


@pytest.mark.slow
def test_main_with_an_unreadable_event_is_one_line(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A truncated payload is a usage error, not a `JSONDecodeError` traceback.

    Args:
        tmp_path: pytest's per-test temporary directory.
        capsys: Captures what the entrypoint printed.
        monkeypatch: Points the entrypoint at the broken payload.
    """
    payload = tmp_path / "event.json"
    _ = payload.write_text("{ not json", encoding="utf-8")
    monkeypatch.setenv(EVENT_PATH_VARIABLE, str(payload))
    monkeypatch.setenv(AUTH_ENV_VARIABLE, "not-a-real-value")
    monkeypatch.setenv(REPOSITORY_VARIABLE, "owner/repo")
    assert main([]) == int(ExitCode.USAGE)
    captured = capsys.readouterr()
    assert captured.err.startswith("error: ")
    assert "Traceback" not in captured.err
