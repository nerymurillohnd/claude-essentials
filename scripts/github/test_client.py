"""Tests for the REST client: headers, pagination, dry-run writes and error handling."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from scripts.common.plugins import repo_root
from scripts.github.client import (
    ACCEPT,
    API_HOST,
    API_VERSION,
    AUTH_ENV_VARIABLE,
    REPOSITORY_VARIABLE,
    GitHubApiError,
    GitHubClient,
    GitHubRepositoryUnknownError,
    GitHubTokenMissingError,
    Response,
    next_path,
    repository_from_env,
    token_from_env,
)
from scripts.github.conftest import FAKE_CREDENTIAL, FakeTransport, json_response

if TYPE_CHECKING:
    from pathlib import Path


def test_every_request_pins_the_media_type_and_the_api_version(
    client: GitHubClient, transport: FakeTransport
) -> None:
    """A future default must never move this client's behaviour under it."""
    _ = client.get("/repos/owner/repo/labels")
    headers = transport.sent[0].headers
    assert headers["Accept"] == ACCEPT
    assert headers["X-GitHub-Api-Version"] == API_VERSION
    assert headers["Authorization"] == f"Bearer {FAKE_CREDENTIAL}"


def test_get_parses_the_body(client: GitHubClient, transport: FakeTransport) -> None:
    """The result is `object`, which the caller narrows."""
    transport.responses["/x"] = json_response({"name": "type: bug"})
    assert client.get("/x") == {"name": "type: bug"}


def test_get_all_follows_the_link_header(client: GitHubClient, transport: FakeTransport) -> None:
    """A taxonomy over one page must not be read as a taxonomy that lost labels."""
    transport.responses["/labels"] = json_response(
        [1], link=f'<https://{API_HOST}/labels?page=2>; rel="next"'
    )
    transport.responses["/labels?page=2"] = json_response([2])
    assert client.get_all("/labels") == [1, 2]


def test_next_path_returns_none_on_the_last_page() -> None:
    """A response with no `Link` ends the walk."""
    assert next_path(Response(status=200, headers=(), body="[]")) is None


def test_next_path_ignores_other_relations() -> None:
    """`rel="prev"` and `rel="last"` are not the next page."""
    link = f'<https://{API_HOST}/labels?page=1>; rel="prev"'
    assert next_path(Response(status=200, headers=(("Link", link),), body="[]")) is None


def test_a_read_only_client_sends_no_write(client: GitHubClient, transport: FakeTransport) -> None:
    """The dry run is enforced in one place, so no caller can forget it."""
    assert client.mutate("POST", "/repos/owner/repo/labels", {"name": "x"}) is False
    assert transport.sent == []


def test_an_applying_client_sends_the_write(transport: FakeTransport) -> None:
    """With `apply`, the same call reaches the API with a JSON body."""
    applying = GitHubClient(
        repo="owner/repo", token=FAKE_CREDENTIAL, transport=transport, apply=True
    )
    assert applying.mutate("POST", "/labels", {"name": "x"}) is True
    assert transport.sent[0].body == '{"name": "x"}'
    assert transport.sent[0].headers["Content-Type"] == "application/json"


def test_an_unexpected_status_raises(client: GitHubClient, transport: FakeTransport) -> None:
    """A 404 must stop the run rather than be read as an empty collection."""
    transport.responses["/missing"] = json_response({"message": "Not Found"}, status=404)
    with pytest.raises(GitHubApiError):
        _ = client.get("/missing")


def test_a_missing_token_names_the_variable() -> None:
    """The error tells a maintainer exactly what to export."""
    with pytest.raises(GitHubTokenMissingError, match=AUTH_ENV_VARIABLE):
        _ = token_from_env({})


def test_the_token_comes_from_the_environment() -> None:
    """The one place the credential is read."""
    assert token_from_env({AUTH_ENV_VARIABLE: FAKE_CREDENTIAL}) == FAKE_CREDENTIAL


def test_the_repository_comes_from_actions_when_it_is_set(tmp_path: Path) -> None:
    """On a runner the slug is given; no git call is needed."""
    assert repository_from_env({REPOSITORY_VARIABLE: "owner/repo"}, tmp_path) == "owner/repo"


@pytest.mark.slow
def test_the_repository_falls_back_to_origin() -> None:
    """On the maintainer's machine the slug comes from the remote."""
    assert repository_from_env({}, repo_root()) == "nerymurillohnd/claude-essentials"


def test_an_unknown_repository_raises(tmp_path: Path) -> None:
    """A tree with no GitHub remote cannot be labelled."""
    with pytest.raises(GitHubRepositoryUnknownError):
        _ = repository_from_env({}, tmp_path)
