"""A minimal GitHub REST client: stdlib only, read by default, injectable for tests.

Three constraints shape it. It runs inside `triage.yml`, a workflow that holds a write token
and must never execute third-party code, so it has no dependencies beyond `http.client`. It
is used by a gate that only ever reads unless a human passes `--apply`, so every mutation
goes through one method that refuses silently when `apply` is false. And its tests must not
reach the network, so the transport is a callable the caller supplies.

Nothing here knows what a label or an issue is; that belongs to `labels` and `triage_rules`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import http.client
import json
from pathlib import Path
import re
from typing import TYPE_CHECKING, Final, Protocol

from scripts.common.errors import MaintainerError
from scripts.common.jsontext import is_json_array
from scripts.common.plugins import git_output_or_none, parse_json

if TYPE_CHECKING:
    from collections.abc import Mapping

API_HOST: Final = "api.github.com"
"""The only host this client ever talks to."""

API_VERSION: Final = "2022-11-28"
"""The `X-GitHub-Api-Version` every request pins, so a future default cannot move under us."""

ACCEPT: Final = "application/vnd.github+json"
"""The documented media type for the REST API."""

USER_AGENT: Final = "claude-essentials-maintainer"
"""GitHub rejects requests without one."""

AUTH_ENV_VARIABLE: Final = "GITHUB_TOKEN"
"""The environment variable holding the API token, in CI and on the maintainer's machine."""

REPOSITORY_VARIABLE: Final = "GITHUB_REPOSITORY"
"""`owner/name`, set by Actions; derived from `origin` when it is absent."""

REQUEST_TIMEOUT_SECONDS: Final = 30.0
"""A hung connection must fail the job rather than hold a runner for six hours."""

SUCCESS_STATUSES: Final = frozenset({200, 201, 202, 204})
"""The statuses this client treats as success; anything else raises."""

_NEXT_LINK: Final = re.compile(r'<(?P<url>[^>]+)>;\s*rel="next"')
"""The `Link` header form that carries the next page."""

_REMOTE_URL: Final = re.compile(r"(?:[:/])(?P<owner>[^/:]+)/(?P<name>[^/]+?)(?:\.git)?\s*\Z")
"""`owner/name` at the end of an SSH or HTTPS remote URL."""


class GitHubTokenMissingError(MaintainerError):
    """No API token is available, so nothing can be read or written."""

    def __init__(self) -> None:
        """Name the variable and how to fill it."""
        super().__init__(
            f"{AUTH_ENV_VARIABLE} is not set; run `GITHUB_TOKEN=$(gh auth token) …` locally, or "
            f"pass `secrets.GITHUB_TOKEN` in the workflow step's env",
        )


class GitHubRepositoryUnknownError(MaintainerError):
    """The `owner/name` slug could not be determined."""

    def __init__(self) -> None:
        """Name both ways the slug is normally found."""
        super().__init__(
            f"{REPOSITORY_VARIABLE} is not set and `git remote get-url origin` does not look "
            f"like a GitHub remote",
        )


class GitHubApiError(MaintainerError):
    """A request returned a status this client does not treat as success."""

    def __init__(self, method: str, path: str, status: int, body: str) -> None:
        """Record the request and what came back.

        Args:
            method: The HTTP method.
            path: The request path, without the host.
            status: The response status.
            body: The response body, truncated by the caller if it is large.
        """
        super().__init__(f"{method} {path} returned {status}: {body.strip()[:400]}")


@dataclass(frozen=True, slots=True)
class Response:
    """One HTTP response, reduced to what this client reads.

    Attributes:
        status: The response status code.
        headers: Header names and values, in the order the server sent them.
        body: The decoded response body; the empty string for `204 No Content`.
    """

    status: int
    headers: tuple[tuple[str, str], ...]
    body: str

    def header(self, name: str) -> str | None:
        """Return one header's value, ignoring case.

        Args:
            name: The header to look up.

        Returns:
            The value, or None when the response does not carry that header.
        """
        lowered = name.lower()
        for key, value in self.headers:
            if key.lower() == lowered:
                return value
        return None


class Transport(Protocol):
    """How a request reaches the server; the seam the tests replace."""

    def __call__(
        self,
        *,
        method: str,
        path: str,
        headers: Mapping[str, str],
        body: str | None,
    ) -> Response:
        """Send one request and return its response.

        Args:
            method: The HTTP method.
            path: The request path, without the host.
            headers: Every header to send.
            body: The request body, or None.

        Returns:
            The response.
        """
        ...


@dataclass(frozen=True, slots=True)
class HttpsTransport:
    """The real transport: one TLS connection per request, closed straight away.

    Attributes:
        host: The API host.
        timeout: How long a single request may take.
    """

    host: str = API_HOST
    timeout: float = REQUEST_TIMEOUT_SECONDS

    def __call__(
        self,
        *,
        method: str,
        path: str,
        headers: Mapping[str, str],
        body: str | None,
    ) -> Response:
        """Send one request over HTTPS.

        Args:
            method: The HTTP method.
            path: The request path, without the host.
            headers: Every header to send.
            body: The request body, or None.

        Returns:
            The response.
        """
        connection = http.client.HTTPSConnection(self.host, timeout=self.timeout)
        try:
            connection.request(method, path, body=body, headers=dict(headers))
            raw = connection.getresponse()
            payload = raw.read().decode("utf-8")
            return Response(status=raw.status, headers=tuple(raw.getheaders()), body=payload)
        finally:
            connection.close()


def token_from_env(env: Mapping[str, str]) -> str:
    """Read the API token, with an explicit error when it is absent.

    Args:
        env: The process environment.

    Returns:
        The token.

    Raises:
        GitHubTokenMissingError: If the variable is unset or empty.
    """
    token = env.get(AUTH_ENV_VARIABLE)
    if not token:
        raise GitHubTokenMissingError
    return token


def repository_from_env(env: Mapping[str, str], root: Path) -> str:
    """Determine the `owner/name` slug this run acts on.

    Args:
        env: The process environment; Actions sets `GITHUB_REPOSITORY`.
        root: The repository root, used to read `origin` when the variable is absent.

    Returns:
        The slug.

    Raises:
        GitHubRepositoryUnknownError: If neither source yields one.
    """
    slug = env.get(REPOSITORY_VARIABLE)
    if slug:
        return slug
    url = git_output_or_none(root, ["remote", "get-url", "origin"])
    match = None if url is None else _REMOTE_URL.search(url)
    if match is None:
        raise GitHubRepositoryUnknownError
    return f"{match['owner']}/{match['name']}"


def next_path(response: Response) -> str | None:
    """Return the path of the next page, if the response advertises one.

    Args:
        response: The response to read the `Link` header of.

    Returns:
        The next page's path, without the host, or None on the last page.
    """
    link = response.header("Link")
    match = None if link is None else _NEXT_LINK.search(link)
    if match is None:
        return None
    prefix = f"https://{API_HOST}"
    return match["url"].removeprefix(prefix)


@dataclass(frozen=True, slots=True, kw_only=True)
class GitHubClient:
    """Reads the API, and writes only when the caller asked for it.

    Attributes:
        repo: The `owner/name` slug every path is built from.
        token: The API token.
        transport: How requests reach the server.
        apply: Whether mutations are actually sent; false makes every write a no-op.
    """

    repo: str
    token: str
    transport: Transport = field(default_factory=HttpsTransport)
    apply: bool = False

    def _headers(self, *, with_body: bool) -> dict[str, str]:
        """Build the headers every request carries.

        Args:
            with_body: Whether a JSON body is attached.

        Returns:
            The header map.
        """
        headers = {
            "Accept": ACCEPT,
            "Authorization": f"Bearer {self.token}",
            "X-GitHub-Api-Version": API_VERSION,
            "User-Agent": USER_AGENT,
        }
        if with_body:
            headers["Content-Type"] = "application/json"
        return headers

    def request(self, method: str, path: str, payload: object | None = None) -> Response:
        """Send one request and refuse any status that is not a success.

        Args:
            method: The HTTP method.
            path: The path after the host, starting with `/`.
            payload: A JSON body, or None.

        Returns:
            The response.

        Raises:
            GitHubApiError: If the status is outside `SUCCESS_STATUSES`.
        """
        body = None if payload is None else json.dumps(payload)
        response = self.transport(
            method=method,
            path=path,
            headers=self._headers(with_body=body is not None),
            body=body,
        )
        if response.status not in SUCCESS_STATUSES:
            raise GitHubApiError(method, path, response.status, response.body)
        return response

    def get(self, path: str) -> object:
        """Read one resource.

        Args:
            path: The path after the host, starting with `/`.

        Returns:
            The parsed document as `object`; never `Any`.
        """
        response = self.request("GET", path)
        return parse_json(response.body, path=Path(path))

    def get_all(self, path: str) -> list[object]:
        """Read every page of a collection, following the `Link` header.

        Args:
            path: The first page's path, starting with `/`.

        Returns:
            Every element of every page, in server order.
        """
        items: list[object] = []
        current: str | None = path
        while current is not None:
            response = self.request("GET", current)
            page = parse_json(response.body, path=Path(current))
            if is_json_array(page):
                items.extend(page)
            current = next_path(response)
        return items

    def mutate(self, method: str, path: str, payload: object | None = None) -> bool:
        """Send a write, or do nothing when this client is in dry-run mode.

        Args:
            method: The HTTP method.
            path: The path after the host, starting with `/`.
            payload: A JSON body, or None.

        Returns:
            True when the request was sent, False when it was skipped.
        """
        if not self.apply:
            return False
        _ = self.request(method, path, payload)
        return True
