"""Install one Claude Code CLI release on a CI runner, verified against Anthropic's signature.

Every workflow that runs `claude plugin validate`, `claude plugin tag` or `claude plugin eval`
needs the CLI at the version `CLAUDE_CODE_VERSION` pins. A global install of the registry
package would work, but it is an install outside any lockfile (zizmor `adhoc-packages`) and
it verifies nothing the repository pins. This entrypoint follows the "Binary integrity and
code signing" section of https://code.claude.com/docs/en/setup (read 2026-09-21) instead:

1. download the release signing key and refuse it unless its fingerprint is `FINGERPRINT`;
2. download the release's `manifest.json` and its detached `manifest.json.sig`, and refuse the
   manifest unless `gpg` reports a valid signature by that key;
3. download the platform binary and refuse it unless its size and SHA-256 equal the manifest.

`latest` and `stable` are resolved through the bucket's channel files, which is what the
nightly workflow uses; every other workflow passes an exact version. Nothing is installed
into the user's home, so the runner has exactly one `claude`: the one this prints.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import http.client
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from typing import TYPE_CHECKING, Final, Protocol, final

from scripts.common.errors import ExecutableNotFoundError, ExitCode, MaintainerError
from scripts.common.jsontext import is_json_object
from scripts.common.plugins import parse_json

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

HOST: Final = "downloads.claude.ai"
"""The only host this module talks to."""

RELEASES_PATH: Final = "/claude-code-releases"
"""Where every release, and the two channel files, live on `HOST`."""

KEY_PATH: Final = "/keys/claude-code.asc"
"""The release signing key the documentation publishes."""

FINGERPRINT: Final = "31DDDE24DDFAB679F42D7BD2BAA929FF1A7ECACE"
"""The documented fingerprint of the release signing key; the only key this trusts."""

CHANNELS: Final = frozenset({"latest", "stable"})
"""Names the bucket resolves to a version through a one-line file."""

VERSION_RE: Final = re.compile(r"^\d+\.\d+\.\d+$")
"""An exact release, which is what every pinned workflow passes."""

PLATFORMS: Final[dict[tuple[str, str], str]] = {
    ("Linux", "x86_64"): "linux-x64",
    ("Linux", "aarch64"): "linux-arm64",
    ("Darwin", "x86_64"): "darwin-x64",
    ("Darwin", "arm64"): "darwin-arm64",
}
"""`uname` pairs mapped to the manifest's platform keys; glibc Linux and macOS only."""

TIMEOUT_SECONDS: Final = 120.0
"""A stalled download fails the step instead of holding the runner."""

CHUNK_BYTES: Final = 1 << 20
"""How much of the binary is read, hashed and written at a time."""

BINARY_NAME: Final = "claude"
"""The file name the manifest and `PATH` both use."""

FPR_FIELD: Final = 9
"""The zero-based field of a `--with-colons` `fpr` record that holds the fingerprint."""


class DownloadFailedError(MaintainerError):
    """A request to the release bucket did not return `200`."""

    def __init__(self, path: str, status: int) -> None:
        """Record the path and what came back.

        Args:
            path: The request path on `HOST`.
            status: The response status.
        """
        super().__init__(f"https://{HOST}{path} returned {status}")


class VerificationFailedError(MaintainerError):
    """The key, the manifest signature or the binary did not match what is pinned."""

    def __init__(self, detail: str) -> None:
        """Record which check failed.

        Args:
            detail: What did not match, phrased for the job log.
        """
        super().__init__(f"refusing to install Claude Code: {detail}")


class UnsupportedRequestError(MaintainerError):
    """The version or the platform is not one this installer handles."""

    def __init__(self, detail: str) -> None:
        """Record what was asked for.

        Args:
            detail: The request that cannot be served.
        """
        super().__init__(detail)


class Sink(Protocol):
    """Where a download's bytes go; a file or an in-memory buffer."""

    def write(self, data: bytes, /) -> int:
        """Accept one chunk.

        Args:
            data: The bytes.

        Returns:
            How many were written.
        """
        ...


def https_fetch(path: str, sink: Sink) -> None:
    """Stream one resource from `HOST` into a sink.

    Args:
        path: The request path.
        sink: Where the body goes.

    Raises:
        DownloadFailedError: If the status is not 200.
    """
    connection = http.client.HTTPSConnection(HOST, timeout=TIMEOUT_SECONDS)
    try:
        connection.request("GET", path, headers={"User-Agent": "claude-essentials-maintainer"})
        response = connection.getresponse()
        if response.status != http.client.OK:
            raise DownloadFailedError(path, response.status)
        while chunk := response.read(CHUNK_BYTES):
            _ = sink.write(chunk)
    finally:
        connection.close()


@dataclass(frozen=True, slots=True)
class Artifact:
    """What the signed manifest says one platform's binary is.

    Attributes:
        version: The release the manifest describes.
        platform: The manifest's platform key.
        checksum: The binary's SHA-256, lowercase hex.
        size: The binary's size in bytes.
    """

    version: str
    platform: str
    checksum: str
    size: int


def platform_key(system: str, machine: str) -> str:
    """Map `uname` values to the manifest's platform key.

    Args:
        system: `platform.system()`.
        machine: `platform.machine()`.

    Returns:
        The key, for example `linux-x64`.

    Raises:
        UnsupportedRequestError: If the pair is not in `PLATFORMS`.
    """
    key = PLATFORMS.get((system, machine))
    if key is None:
        detail = f"no Claude Code build is mapped for {system} {machine}"
        raise UnsupportedRequestError(detail)
    return key


def validate_request(requested: str) -> str:
    """Accept an exact version or a channel name, and nothing else.

    Args:
        requested: The value of `CLAUDE_CODE_VERSION`.

    Returns:
        The value, stripped.

    Raises:
        UnsupportedRequestError: If it is neither.
    """
    value = requested.strip()
    if value in CHANNELS or VERSION_RE.match(value) is not None:
        return value
    detail = f"{requested!r} is not X.Y.Z, `latest` or `stable`"
    raise UnsupportedRequestError(detail)


def artifact_from_manifest(text: str, *, version: str, platform_name: str) -> Artifact:
    """Read one platform's entry out of a verified manifest.

    Args:
        text: The manifest, already signature-checked.
        version: The release that was requested, which the manifest must name.
        platform_name: The platform key to read.

    Returns:
        The artifact the binary must match.

    Raises:
        VerificationFailedError: If the manifest names another version or lacks the entry.
    """
    document = parse_json(text, path=Path("manifest.json"))
    if not is_json_object(document) or document.get("version") != version:
        detail = f"the manifest does not describe version {version}"
        raise VerificationFailedError(detail)
    platforms = document.get("platforms")
    entry = platforms.get(platform_name) if is_json_object(platforms) else None
    if not is_json_object(entry):
        detail = f"the manifest has no {platform_name} entry"
        raise VerificationFailedError(detail)
    checksum, size = entry.get("checksum"), entry.get("size")
    if not isinstance(checksum, str) or not isinstance(size, int):
        detail = f"the {platform_name} entry carries no checksum and size"
        raise VerificationFailedError(detail)
    return Artifact(version=version, platform=platform_name, checksum=checksum.lower(), size=size)


def signed_by_pinned_key(status_output: str) -> bool:
    """Read `gpg --status-fd` output for a valid signature by the pinned key.

    `VALIDSIG` carries the signing key's fingerprint first and the primary key's last, so a
    signature by a subkey of the pinned key is accepted and any other key is not.

    Args:
        status_output: What `gpg --status-fd 1 --verify` printed.

    Returns:
        True when one `VALIDSIG` line names `FINGERPRINT` as the primary key.
    """
    for line in status_output.splitlines():
        fields = line.split()
        if fields[:2] == ["[GNUPG:]", "VALIDSIG"] and fields[-1].upper() == FINGERPRINT:
            return True
    return False


def key_fingerprints(colons_output: str) -> list[str]:
    """Read the fingerprints out of `gpg --with-colons --show-keys`.

    Args:
        colons_output: What gpg printed.

    Returns:
        Every `fpr` record's fingerprint, uppercase.
    """
    fingerprints: list[str] = []
    for line in colons_output.splitlines():
        fields = line.split(":")
        if fields[0] == "fpr" and len(fields) > FPR_FIELD:
            fingerprints.append(fields[FPR_FIELD].upper())
    return fingerprints


def _gpg(home: Path, args: Sequence[str]) -> subprocess.CompletedProcess[str]:
    """Run gpg against a throwaway keyring.

    Args:
        home: The `GNUPGHOME` to use.
        args: The arguments after `gpg --batch`.

    Returns:
        The completed process.

    Raises:
        ExecutableNotFoundError: If gpg is not on PATH.
    """
    executable = shutil.which("gpg")
    if executable is None:
        raise ExecutableNotFoundError("gpg")
    return subprocess.run(
        [executable, "--batch", "--homedir", str(home), *args],
        executable=executable,
        check=False,
        capture_output=True,
        text=True,
    )


def verify_manifest(work: Path, *, key: Path, manifest: Path, signature: Path) -> None:
    """Check the key's fingerprint, then the manifest's signature by that key.

    Args:
        work: A private directory for the keyring.
        key: The downloaded signing key.
        manifest: The downloaded manifest.
        signature: Its detached signature.

    Raises:
        VerificationFailedError: If the key is not the pinned one or the signature is bad.
        ExecutableNotFoundError: If gpg is not on PATH.
    """
    home = work / "gnupg"
    home.mkdir(mode=0o700)
    shown = _gpg(home, ["--with-colons", "--show-keys", str(key)])
    if FINGERPRINT not in key_fingerprints(shown.stdout):
        detail = f"the published signing key is not {FINGERPRINT}"
        raise VerificationFailedError(detail)
    _ = _gpg(home, ["--import", str(key)])
    verified = _gpg(home, ["--status-fd", "1", "--verify", str(signature), str(manifest)])
    if verified.returncode != 0 or not signed_by_pinned_key(verified.stdout):
        detail = "manifest.json is not signed by the release signing key"
        raise VerificationFailedError(detail)


@final
class _HashingFile:
    """A sink that writes to a file and hashes what it writes."""

    def __init__(self, path: Path) -> None:
        """Open the destination.

        Args:
            path: Where the bytes go.
        """
        self._handle = path.open("wb")
        self.digest = hashlib.sha256()
        self.size = 0

    def write(self, data: bytes, /) -> int:
        """Write and hash one chunk.

        Args:
            data: The bytes.

        Returns:
            How many were written.
        """
        self.digest.update(data)
        self.size += len(data)
        return self._handle.write(data)

    def close(self) -> None:
        """Flush and close the file."""
        self._handle.close()


def _download_text(fetch: Callable[[str, Sink], None], path: str, destination: Path) -> str:
    """Download a small text resource to a file and return its text.

    Args:
        fetch: The transport.
        path: The request path.
        destination: Where the bytes are kept, for gpg to read.

    Returns:
        The decoded text.
    """
    sink = _HashingFile(destination)
    try:
        fetch(path, sink)
    finally:
        sink.close()
    return destination.read_text(encoding="utf-8")


def install(
    requested: str,
    dest: Path,
    *,
    fetch: Callable[[str, Sink], None] = https_fetch,
    platform_name: str | None = None,
) -> Path:
    """Download, verify and install one release.

    Args:
        requested: An exact version, `latest` or `stable`.
        dest: The directory the binary is installed into.
        fetch: The transport; tests pass a fake.
        platform_name: The manifest key; this machine's when None.

    Returns:
        The installed binary.

    Raises:
        MaintainerError: If the request, a download or a verification fails.
    """
    value = validate_request(requested)
    target = platform_name or platform_key(platform.system(), platform.machine())
    with tempfile.TemporaryDirectory() as scratch:
        work = Path(scratch)
        version = value
        if value in CHANNELS:
            version = _download_text(fetch, f"{RELEASES_PATH}/{value}", work / "channel").strip()
            _ = validate_request(version)
        base = f"{RELEASES_PATH}/{version}"
        _ = _download_text(fetch, KEY_PATH, work / "key.asc")
        manifest = _download_text(fetch, f"{base}/manifest.json", work / "manifest.json")
        _ = _download_text(fetch, f"{base}/manifest.json.sig", work / "manifest.json.sig")
        verify_manifest(
            work,
            key=work / "key.asc",
            manifest=work / "manifest.json",
            signature=work / "manifest.json.sig",
        )
        artifact = artifact_from_manifest(manifest, version=version, platform_name=target)
        staged = work / BINARY_NAME
        sink = _HashingFile(staged)
        try:
            fetch(f"{base}/{artifact.platform}/{BINARY_NAME}", sink)
        finally:
            sink.close()
        if sink.size != artifact.size or sink.digest.hexdigest() != artifact.checksum:
            detail = f"the {artifact.platform} binary does not match the signed manifest"
            raise VerificationFailedError(detail)
        dest.mkdir(parents=True, exist_ok=True)
        installed = dest / BINARY_NAME
        _ = shutil.move(staged, installed)
    installed.chmod(0o755)
    return installed


def parse_args(argv: Sequence[str] | None) -> tuple[str, Path]:
    """Parse the command line.

    Args:
        argv: Arguments without the program name; `sys.argv[1:]` when None.

    Returns:
        The requested version and the destination directory.

    Raises:
        SystemExit: If argparse refuses the arguments.
    """
    parser = argparse.ArgumentParser(
        prog="python -m scripts.github.install_claude_code",
        description="Install a signature-verified Claude Code CLI release.",
    )
    _ = parser.add_argument("version", help="X.Y.Z, latest or stable")
    _ = parser.add_argument("--dest", required=True, help="directory to install `claude` into")
    values: dict[str, object] = vars(parser.parse_args(argv))
    version, dest = values["version"], values["dest"]
    return (version if isinstance(version, str) else "", Path(str(dest)))


def main(argv: Sequence[str] | None = None) -> int:
    """Install the requested release and print the binary's path.

    Args:
        argv: Arguments without the program name; `sys.argv[1:]` when None.

    Returns:
        0 when the binary is installed, 2 when anything could not be verified or downloaded.
    """
    requested, dest = parse_args(argv)
    try:
        installed = install(requested, dest)
    except (MaintainerError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return int(ExitCode.USAGE)
    print(os.fspath(installed))
    return int(ExitCode.OK)


if __name__ == "__main__":
    sys.exit(main())
