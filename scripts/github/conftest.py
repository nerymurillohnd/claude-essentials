"""A recording transport, so every API test runs offline and can assert what was sent."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from typing import TYPE_CHECKING, Final

import pytest

from scripts.common.jsontext import canonical_json
from scripts.github.client import GitHubClient, Response
from scripts.github.labels import LABELS_PATH, REQUIRED_LABELS
from scripts.marketplace.conftest import build_tree, write_file

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

FAKE_CREDENTIAL: Final = "not-a-real-value"
"""What the tests pass where a real run would pass an API token."""


@dataclass(frozen=True, slots=True)
class SentRequest:
    """One request the fake transport was asked to send.

    Attributes:
        method: The HTTP method.
        path: The request path.
        headers: Every header the client set.
        body: The request body, or None.
    """

    method: str
    path: str
    headers: dict[str, str]
    body: str | None


@dataclass(slots=True)
class FakeTransport:
    """Answers from a canned table and records every request.

    Attributes:
        responses: Path mapped to the response to return; a missing path yields `200 []`.
        sent: Every request, in order.
    """

    responses: dict[str, Response] = field(default_factory=dict[str, Response])
    sent: list[SentRequest] = field(default_factory=list[SentRequest])

    def __call__(
        self,
        *,
        method: str,
        path: str,
        headers: Mapping[str, str],
        body: str | None,
    ) -> Response:
        """Record one request and return its canned response.

        Args:
            method: The HTTP method.
            path: The request path.
            headers: Every header to send.
            body: The request body, or None.

        Returns:
            The canned response, or an empty `200`.
        """
        self.sent.append(SentRequest(method=method, path=path, headers=dict(headers), body=body))
        return self.responses.get(path, Response(status=200, headers=(), body="[]"))


def json_response(payload: object, *, link: str | None = None, status: int = 200) -> Response:
    """Build a canned JSON response.

    Args:
        payload: What to serialise into the body.
        link: A `Link` header value, for pagination tests.
        status: The status code.

    Returns:
        The response.
    """
    headers = (("Link", link),) if link is not None else ()
    return Response(status=status, headers=headers, body=json.dumps(payload))


@pytest.fixture
def transport() -> FakeTransport:
    """Build an empty recording transport.

    Returns:
        The transport.
    """
    return FakeTransport()


@pytest.fixture
def client(transport: FakeTransport) -> GitHubClient:
    """Build a read-only client wired to the recording transport.

    Args:
        transport: The recording transport.

    Returns:
        The client, with `apply` false.
    """
    return GitHubClient(repo="owner/repo", token=FAKE_CREDENTIAL, transport=transport)


@pytest.fixture
def tree(tmp_path: Path) -> Path:
    """Build a marketplace with one plugin and a taxonomy that declares every required label.

    Args:
        tmp_path: pytest's per-test temporary directory.

    Returns:
        The fixture repository root.
    """
    root = build_tree(tmp_path)
    write_file(
        root / LABELS_PATH,
        canonical_json(
            [
                {"name": name, "color": "ededed", "description": f"{name} description"}
                for name in REQUIRED_LABELS
            ],
        ),
    )
    return root
