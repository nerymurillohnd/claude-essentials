"""Create the `{name}--v{version}` tag of every plugin version that has none.

The official CLI owns tagging: `claude plugin tag <path>` validates the plugin, checks that
`plugin.json` agrees with the marketplace entry and only then writes the annotated tag. This
entrypoint decides *which* plugins still need one and hands each to that CLI, so the repo
never invents a tag the CLI would have refused.

Flags confirmed against `claude plugin tag --help` on the pinned CLI (2026-09-21): `--dry-run`
prints what would be tagged without creating it, `--push` pushes the new tag to `--remote`
(`origin` by default), `-f/--force` skips the dirty-tree and already-exists checks, and
`-m/--message` sets the annotation. Only the first two are used here; the repository never
forces a tag, because `*--v*` tags are immutable by ruleset.

Run it without `--dry-run` only in the `Tag plugin versions` workflow, which checks out a
fresh tree whose tags mirror `origin`.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import os
import shutil
import subprocess
import sys
from typing import TYPE_CHECKING, Final

from scripts.common.errors import ExecutableNotFoundError, ExitCode, MaintainerError
from scripts.common.plugins import (
    MANIFEST_RELATIVE_PATH,
    PLUGINS_DIRNAME,
    as_mapping,
    as_str,
    load_json,
    plugin_ids,
    repo_root,
)
from scripts.versioning.version_plan import tag_exists

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

CLAUDE_BIN_ENV: Final = "CLAUDE_BIN"
"""Environment variable that overrides which `claude` binary runs; used by the tests."""

NOTHING_PENDING: Final = "Every plugin version is already tagged."
"""Printed when no plugin version is missing its tag."""


class ClaudeTagFailedError(MaintainerError):
    """`claude plugin tag` refused to tag a plugin."""

    def __init__(self, name: str, detail: str) -> None:
        """Record which plugin the CLI refused and what it said.

        Args:
            name: The plugin directory name.
            detail: The CLI's combined output.
        """
        super().__init__(f"`claude plugin tag` refused {name}: {detail}")


@dataclass(frozen=True, slots=True)
class TagResult:
    """What the CLI did for one plugin.

    Attributes:
        name: The plugin directory name.
        version: The version that was tagged, or would have been.
        tag: The tag name.
        returncode: The CLI's exit status.
        output: Its combined standard output and standard error, stripped.
    """

    name: str
    version: str
    tag: str
    returncode: int
    output: str


def claude_executable() -> str:
    """Resolve the Claude Code CLI.

    Returns:
        The absolute path of the binary, or whatever `CLAUDE_BIN` names.

    Raises:
        ExecutableNotFoundError: If neither the override nor PATH provides one.
    """
    override = os.environ.get(CLAUDE_BIN_ENV)
    if override is not None and override.strip():
        return override
    resolved = shutil.which("claude")
    if resolved is None:
        raise ExecutableNotFoundError("claude")
    return resolved


def manifest_version(root: Path, name: str) -> str:
    """Read a plugin's declared version.

    Args:
        root: The repository root.
        name: The plugin directory name.

    Returns:
        The `version` field exactly as written.

    Raises:
        UnexpectedShapeError: If the manifest has no string `version`.
    """
    path = root / PLUGINS_DIRNAME / name / MANIFEST_RELATIVE_PATH
    manifest = as_mapping(load_json(path), path=path)
    return as_str(manifest.get("version"), path=path)


def pending_tags(root: Path) -> list[tuple[str, str]]:
    """List the plugin versions that carry no tag yet.

    Args:
        root: The repository root.

    Returns:
        Name and version pairs, in plugin order.
    """
    pending: list[tuple[str, str]] = []
    for name in plugin_ids(root):
        version = manifest_version(root, name)
        if not tag_exists(root, f"{name}--v{version}"):
            pending.append((name, version))
    return pending


def run_claude_tag(root: Path, name: str, *, extra: Sequence[str]) -> TagResult:
    """Hand one plugin to `claude plugin tag`.

    Args:
        root: The repository root; the CLI runs there so it sees the marketplace.
        name: The plugin directory name.
        extra: Flags appended after the path, such as `--dry-run` or `--push`.

    Returns:
        What the CLI did.

    Raises:
        ExecutableNotFoundError: If the CLI is not available.
    """
    executable = claude_executable()
    version = manifest_version(root, name)
    argv = [executable, "plugin", "tag", f"{PLUGINS_DIRNAME}/{name}", *extra]
    completed = subprocess.run(
        argv,
        executable=executable,
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    output = f"{completed.stdout}{completed.stderr}".strip()
    return TagResult(
        name=name,
        version=version,
        tag=f"{name}--v{version}",
        returncode=completed.returncode,
        output=output,
    )


@dataclass(frozen=True, slots=True)
class Options:
    """Parsed command line.

    Attributes:
        dry_run: Print what would be tagged without creating anything.
        push: Push each new tag to the remote after creating it.
    """

    dry_run: bool
    push: bool


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
        prog="python -m scripts.versioning.tag_versions",
        description="Tag every plugin version that has no tag yet.",
    )
    _ = parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print what would be tagged without creating a tag",
    )
    _ = parser.add_argument(
        "--push",
        action="store_true",
        help="push each new tag to origin; the tagging workflow only",
    )
    values: dict[str, object] = vars(parser.parse_args(argv))
    return Options(dry_run=bool(values["dry_run"]), push=bool(values["push"]))


def main(argv: Sequence[str] | None = None) -> int:
    """Tag every untagged plugin version.

    Args:
        argv: Arguments without the program name; `sys.argv[1:]` when None.

    Returns:
        0 when every pending version was tagged (or would be), 1 when the CLI refused one,
        2 when the flags contradict each other.
    """
    options = parse_args(argv)
    if options.dry_run and options.push:
        print("--dry-run and --push contradict each other", file=sys.stderr)
        return int(ExitCode.USAGE)
    root = repo_root()
    pending = pending_tags(root)
    if not pending:
        print(NOTHING_PENDING)
        return int(ExitCode.OK)
    extra = ["--dry-run"] if options.dry_run else (["--push"] if options.push else [])
    failed = False
    for name, version in pending:
        result = run_claude_tag(root, name, extra=extra)
        verb = "would tag" if options.dry_run else "tagged"
        status = verb if result.returncode == 0 else "refused"
        print(f"{name} {version} {status} {result.tag}")
        if result.returncode != 0:
            failed = True
            print(str(ClaudeTagFailedError(name, result.output)), file=sys.stderr)
    return int(ExitCode.FINDINGS if failed else ExitCode.OK)


if __name__ == "__main__":
    raise SystemExit(main())
