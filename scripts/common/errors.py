"""Findings, exit codes and the exception types every maintainer module shares."""

from __future__ import annotations

from dataclasses import dataclass
import enum
from typing import TYPE_CHECKING, ClassVar, Literal

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

Severity = Literal["error", "warning"]


class ExitCode(enum.IntEnum):
    """Exit status an entrypoint hands back to `make` and to CI."""

    OK = 0
    FINDINGS = 1
    USAGE = 2


@dataclass(frozen=True, slots=True)
class Finding:
    """One violation of one invariant, ready to be printed by a gate.

    Attributes:
        invariant_id: The stable ID of the invariant this violates (P14).
        path: Repository-relative path the violation sits in, or None when repository-wide.
        message: What is wrong, phrased for a maintainer reading gate output.
        severity: Whether the gate refuses (error) or only reports (warning).
    """

    invariant_id: str
    path: str | None
    message: str
    severity: Severity = "error"


def format_finding(finding: Finding) -> str:
    """Render a finding as `<ID> <path>: <message>`.

    A finding with no path renders as `<ID>: <message>`. Every validator message therefore
    starts with its invariant ID, so a reader can look the rule up from the output alone.

    Args:
        finding: The finding to render.

    Returns:
        The single line to print.
    """
    if finding.path is None:
        return f"{finding.invariant_id}: {finding.message}"
    return f"{finding.invariant_id} {finding.path}: {finding.message}"


class MaintainerError(Exception):
    """Base class for every error the maintainer tooling raises on its own behalf."""


class ExecutableNotFoundError(MaintainerError):
    """A binary the tooling depends on is not on PATH."""

    def __init__(self, name: str) -> None:
        """Record which binary is missing.

        Args:
            name: The executable that could not be found.
        """
        super().__init__(f"`{name}` is not on PATH; run `make setup` and check the requirements")


class CommandFailedError(MaintainerError):
    """A subprocess the tooling depends on could not be started or exited non-zero.

    The command line lives on the subclass, so a raise site passes only the detail and
    Ruff's `TRY003` stays satisfied without a suppression.
    """

    command: ClassVar[str] = "<unset>"

    def __init__(self, detail: str) -> None:
        """Record why the subclass's command failed.

        Args:
            detail: What went wrong, taken from the exception or the captured stderr.
        """
        super().__init__(f"`{self.command}` failed: {detail}")


class GitRevParseFailedError(CommandFailedError):
    """`git rev-parse --show-toplevel` did not resolve a working tree."""

    command: ClassVar[str] = "git rev-parse --show-toplevel"


class GitLsFilesFailedError(CommandFailedError):
    """`git ls-files -z` could not list the tracked files."""

    command: ClassVar[str] = "git ls-files -z"


class GitCommandFailedError(MaintainerError):
    """A `git` invocation the tooling depends on could not run or exited non-zero.

    Unlike the fixed-command subclasses above, this one carries the actual argument list, so
    a caller that builds its command at run time still produces a message a maintainer can
    paste into a terminal.
    """

    def __init__(self, args: Sequence[str], detail: str) -> None:
        """Record the command that failed and why.

        Args:
            args: The arguments passed to `git`, without the binary itself.
            detail: What went wrong, taken from the exception or the captured stderr.
        """
        super().__init__(f"`git {' '.join(args)}` failed: {detail}")


class MissingPathError(MaintainerError):
    """A file or directory an entrypoint was pointed at does not exist.

    Raised instead of letting an `OSError` escape, so `--root /nonexistent` and a checkout
    without a catalog both end in one `error: …` line rather than a traceback.
    """

    def __init__(self, path: Path, description: str) -> None:
        """Record what was missing and what it was supposed to be.

        Args:
            path: The path that is not there.
            description: What the entrypoint needed it for ("the repository root").
        """
        super().__init__(f"{path}: {description} does not exist")


class MalformedJsonError(MaintainerError):
    """A JSON file the tooling reads could not be parsed."""

    def __init__(self, path: Path, detail: str) -> None:
        """Record the file and the parser's complaint.

        Args:
            path: The file that could not be parsed.
            detail: The decoder's message.
        """
        super().__init__(f"{path}: invalid JSON: {detail}")


class UnexpectedShapeError(MaintainerError):
    """Parsed data does not have the shape the caller requires."""

    def __init__(self, path: Path, expected: str, found: object) -> None:
        """Record the file, the required shape and what was there instead.

        Args:
            path: The file the value came from.
            expected: The required shape, phrased for a reader ("an object", "a string").
            found: The value that was there instead; only its type is reported.
        """
        super().__init__(f"{path}: expected {expected}, found {type(found).__name__}")
