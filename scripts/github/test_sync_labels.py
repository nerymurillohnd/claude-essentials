"""Tests for the label sync entrypoint: what it reads, what it sends, and what it refuses."""

from __future__ import annotations

import pytest

from scripts.common.errors import ExitCode
from scripts.github.client import AUTH_ENV_VARIABLE, GitHubClient
from scripts.github.conftest import FAKE_CREDENTIAL, FakeTransport, json_response
from scripts.github.labels import Label, plan
from scripts.github.sync_labels import apply_plan, main, parse_args, remote_labels


def test_dry_run_is_the_default() -> None:
    """Running with no flags never writes."""
    options = parse_args([])
    assert options.apply is False
    assert options.prune is False


def test_apply_and_prune_are_separate_decisions() -> None:
    """`--apply` never implies `--prune`; deleting a label is always a separate choice."""
    assert parse_args(["--apply"]).prune is False
    assert parse_args(["--prune"]).apply is False


def test_remote_labels_reads_every_page(client: GitHubClient, transport: FakeTransport) -> None:
    """A taxonomy over one page must not look like a taxonomy that lost labels."""
    path = "/repos/owner/repo/labels?per_page=100"
    transport.responses[path] = json_response(
        [{"name": "type: bug", "color": "d73a4a", "description": "x"}],
    )
    assert remote_labels(client) == (Label(name="type: bug", color="d73a4a", description="x"),)


def test_remote_labels_tolerates_a_null_description(
    client: GitHubClient, transport: FakeTransport
) -> None:
    """GitHub returns `null` for a label created without one."""
    path = "/repos/owner/repo/labels?per_page=100"
    transport.responses[path] = json_response([{"name": "x", "color": "ededed"}])
    assert remote_labels(client)[0].description == ""


def test_a_dry_run_sends_nothing(client: GitHubClient, transport: FakeTransport) -> None:
    """The plan is printed; the API is untouched."""
    label_plan = plan([Label(name="bump: removal", color="ededed", description="d")], [])
    assert apply_plan(client, label_plan, prune=False) == []
    assert transport.sent == []


def test_applying_creates_updates_and_renames(transport: FakeTransport) -> None:
    """One request per action, and a rename patches the existing label's name."""
    applying = GitHubClient(
        repo="owner/repo", token=FAKE_CREDENTIAL, transport=transport, apply=True
    )
    label_plan = plan(
        [
            Label(name="bump: removal", color="ededed", description="new"),
            Label(name="type: bug", color="d73a4a", description="changed"),
            Label(name="type: docs", color="0075ca", description="d", aliases=("documentation",)),
        ],
        [
            Label(name="type: bug", color="d73a4a", description="old"),
            Label(name="documentation", color="0075ca", description="d"),
        ],
    )
    lines = apply_plan(applying, label_plan, prune=False)
    assert lines == [
        "created bump: removal",
        "updated type: bug",
        "renamed documentation -> type: docs",
    ]
    methods = [request.method for request in transport.sent]
    assert methods == ["POST", "PATCH", "PATCH"]


def test_pruning_is_opt_in(transport: FakeTransport) -> None:
    """A label the taxonomy dropped is deleted only when a human asked for it."""
    applying = GitHubClient(
        repo="owner/repo", token=FAKE_CREDENTIAL, transport=transport, apply=True
    )
    label_plan = plan([], [Label(name="wontfix", color="ededed", description="")])
    assert apply_plan(applying, label_plan, prune=False) == []
    assert apply_plan(applying, label_plan, prune=True) == ["pruned wontfix"]
    assert transport.sent[0].method == "DELETE"


def test_a_label_name_is_escaped_in_the_path(transport: FakeTransport) -> None:
    """`plugin: block-no-verify` contains a colon and a space."""
    applying = GitHubClient(
        repo="owner/repo", token=FAKE_CREDENTIAL, transport=transport, apply=True
    )
    label_plan = plan(
        [Label(name="plugin: x", color="5319e7", description="new")],
        [Label(name="plugin: x", color="5319e7", description="old")],
    )
    _ = apply_plan(applying, label_plan, prune=False)
    assert transport.sent[0].path.endswith("/plugin%3A%20x")


@pytest.mark.slow
def test_main_without_a_token_is_one_line(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A maintainer who forgot `GITHUB_TOKEN=$(gh auth token)` gets a sentence.

    Args:
        capsys: Captures what the entrypoint printed.
        monkeypatch: Removes the credential from the environment.
    """
    monkeypatch.delenv(AUTH_ENV_VARIABLE, raising=False)
    assert main([]) == int(ExitCode.USAGE)
    captured = capsys.readouterr()
    assert captured.err.startswith(f"error: {AUTH_ENV_VARIABLE} is not set")
    assert "Traceback" not in captured.err
