"""Tests for the verified Claude Code installer: what it refuses, and what it installs."""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING

import pytest

from scripts.github import install_claude_code
from scripts.github.install_claude_code import (
    FINGERPRINT,
    KEY_PATH,
    RELEASES_PATH,
    UnsupportedRequestError,
    VerificationFailedError,
    artifact_from_manifest,
    install,
    key_fingerprints,
    platform_key,
    signed_by_pinned_key,
    validate_request,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from scripts.github.install_claude_code import Sink

VERSION = "2.1.278"
"""The release the fixtures describe."""

BINARY = b"#!/bin/sh\necho fake claude\n"
"""What the fake bucket serves as the linux-x64 binary."""

OTHER_KEY = "0" * 40
"""A fingerprint that is not the release signing key."""


def manifest(*, version: str = VERSION, binary: bytes = BINARY) -> str:
    """Build a manifest in the shape the bucket publishes.

    Args:
        version: The release it names.
        binary: The bytes whose checksum and size it records.

    Returns:
        The JSON text.
    """
    entry = {
        "binary": "claude",
        "checksum": hashlib.sha256(binary).hexdigest(),
        "size": len(binary),
    }
    return json.dumps({"version": version, "platforms": {"linux-x64": entry}})


def bucket(*, served: bytes = BINARY, channel: str = VERSION) -> dict[str, bytes]:
    """Build the fake bucket's contents.

    Args:
        served: The binary the bucket actually returns.
        channel: What the `latest` file resolves to.

    Returns:
        Request paths mapped to bodies.
    """
    base = f"{RELEASES_PATH}/{VERSION}"
    return {
        f"{RELEASES_PATH}/latest": f"{channel}\n".encode(),
        KEY_PATH: b"key",
        f"{base}/manifest.json": manifest().encode(),
        f"{base}/manifest.json.sig": b"sig",
        f"{base}/linux-x64/claude": served,
    }


def fake_fetch(contents: dict[str, bytes]) -> Callable[[str, Sink], None]:
    """Return a transport that serves a fixed mapping.

    Args:
        contents: Request paths mapped to bodies.

    Returns:
        The transport.
    """

    def fetch(path: str, sink: Sink) -> None:
        _ = sink.write(contents[path])

    return fetch


def _accept_signature(_work: Path, *, key: Path, manifest: Path, signature: Path) -> None:
    """Stand in for gpg: the signature path is covered by the status-line tests below.

    Args:
        _work: Unused.
        key: Unused.
        manifest: Unused.
        signature: Unused.
    """
    del key, manifest, signature


@pytest.fixture
def signed(monkeypatch: pytest.MonkeyPatch) -> None:
    """Treat every manifest as correctly signed, so the binary checks can be exercised."""
    monkeypatch.setattr(install_claude_code, "verify_manifest", _accept_signature)


@pytest.mark.parametrize("value", ["2.1.278", "latest", "stable", " 2.1.278\n"])
def test_an_exact_version_or_a_channel_is_accepted(value: str) -> None:
    """The pinned workflows pass X.Y.Z; the nightly passes `latest`."""
    assert validate_request(value) == value.strip()


@pytest.mark.parametrize("value", ["2.1", "v2.1.278", "2.1.x", "", "../../etc"])
def test_anything_else_is_refused(value: str) -> None:
    """The value becomes part of a URL path, so it is validated before any request."""
    with pytest.raises(UnsupportedRequestError):
        _ = validate_request(value)


def test_the_runner_platform_maps_to_the_manifest_key() -> None:
    """`ubuntu-latest` is Linux x86_64, which the bucket calls `linux-x64`."""
    assert platform_key("Linux", "x86_64") == "linux-x64"


def test_an_unmapped_platform_is_refused() -> None:
    """Guessing a key would download a binary for another machine."""
    with pytest.raises(UnsupportedRequestError):
        _ = platform_key("Windows", "AMD64")


def test_a_manifest_for_another_version_is_refused() -> None:
    """A correctly signed manifest of an older release is still the wrong release."""
    with pytest.raises(VerificationFailedError):
        _ = artifact_from_manifest(
            manifest(version="2.1.1"), version=VERSION, platform_name="linux-x64"
        )


def test_a_manifest_without_the_platform_is_refused() -> None:
    """No entry means no checksum, and nothing may be installed unchecked."""
    with pytest.raises(VerificationFailedError):
        _ = artifact_from_manifest(manifest(), version=VERSION, platform_name="linux-arm64")


def test_the_pinned_primary_key_is_accepted_in_validsig() -> None:
    """`VALIDSIG` ends with the primary key's fingerprint, whichever subkey signed."""
    line = f"[GNUPG:] VALIDSIG {'A' * 40} 2026-09-19 1789781019 0 4 0 1 10 00 {FINGERPRINT}"
    assert signed_by_pinned_key(f"[GNUPG:] NEWSIG\n{line}\n")


def test_a_signature_by_another_key_is_refused() -> None:
    """A good signature by the wrong key is exactly the attack the fingerprint pin stops."""
    line = f"[GNUPG:] VALIDSIG {OTHER_KEY} 2026-09-19 1789781019 0 4 0 1 10 00 {OTHER_KEY}"
    assert not signed_by_pinned_key(line)


def test_no_validsig_line_is_a_refusal() -> None:
    """`BADSIG` or no status at all must never read as success."""
    assert not signed_by_pinned_key(f"[GNUPG:] BADSIG {FINGERPRINT[-16:]} Anthropic\n")


def test_fingerprints_are_read_from_colon_records() -> None:
    """`--with-colons` puts the fingerprint in the tenth field of an `fpr` record."""
    output = (
        f"pub:-:4096:1:BAA929FF1A7ECACE:1:::-:::scESC::::::23::0:\nfpr:::::::::{FINGERPRINT}:\n"
    )
    assert key_fingerprints(output) == [FINGERPRINT]


@pytest.mark.usefixtures("signed")
def test_a_verified_binary_is_installed_executable(tmp_path: Path) -> None:
    """The happy path: the bytes on disk are the bytes the signed manifest names."""
    installed = install(
        VERSION, tmp_path / "bin", fetch=fake_fetch(bucket()), platform_name="linux-x64"
    )
    assert installed.read_bytes() == BINARY
    assert installed.stat().st_mode & 0o111


@pytest.mark.usefixtures("signed")
def test_a_tampered_binary_is_never_installed(tmp_path: Path) -> None:
    """A binary that differs from the manifest is refused and leaves nothing behind."""
    fetch = fake_fetch(bucket(served=BINARY + b"#"))
    with pytest.raises(VerificationFailedError):
        _ = install(VERSION, tmp_path / "bin", fetch=fetch, platform_name="linux-x64")
    assert not (tmp_path / "bin" / "claude").exists()


@pytest.mark.usefixtures("signed")
def test_a_channel_is_resolved_to_its_version(tmp_path: Path) -> None:
    """`latest` reads the channel file, then verifies that release like any other."""
    installed = install(
        "latest", tmp_path / "bin", fetch=fake_fetch(bucket()), platform_name="linux-x64"
    )
    assert installed.read_bytes() == BINARY


@pytest.mark.usefixtures("signed")
def test_a_channel_file_that_is_not_a_version_is_refused(tmp_path: Path) -> None:
    """The channel file is unsigned, so what it says is validated before it is used."""
    fetch = fake_fetch(bucket(channel="../evil"))
    with pytest.raises(UnsupportedRequestError):
        _ = install("latest", tmp_path / "bin", fetch=fetch, platform_name="linux-x64")
