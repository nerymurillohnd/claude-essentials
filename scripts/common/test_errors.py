"""Tests for the shared finding, exit-code and exception types."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path
import re

import pytest

from scripts.common.errors import (
    CommandFailedError,
    ExecutableNotFoundError,
    ExitCode,
    Finding,
    GitLsFilesFailedError,
    GitRevParseFailedError,
    MaintainerError,
    MalformedJsonError,
    UnexpectedShapeError,
    format_finding,
)


def test_format_finding_starts_with_the_invariant_id() -> None:
    """P14: a reader can look the rule up from the printed line alone."""
    finding = Finding("R5", "plugins/demo/README.md", "no Requirements table", "error")
    assert format_finding(finding) == "R5 plugins/demo/README.md: no Requirements table"


def test_format_finding_without_a_path_keeps_the_id_first() -> None:
    """A repository-wide finding still leads with its ID."""
    finding = Finding("G3", None, "shfmt pin drifted from the lock", "warning")
    assert format_finding(finding) == "G3: shfmt pin drifted from the lock"


def test_finding_severity_defaults_to_error() -> None:
    """The gate refuses by default; a warning has to be asked for."""
    assert Finding("M1", None, "catalog out of date").severity == "error"


def test_finding_is_immutable_and_hashable() -> None:
    """Findings are records: they can be de-duplicated and never mutated in place."""
    finding = Finding("M1", "plugins/demo", "duplicate id", "error")
    same = Finding("M1", "plugins/demo", "duplicate id", "error")
    assert finding == same
    assert hash(finding) == hash(same)
    attribute = "message"
    with pytest.raises(FrozenInstanceError):
        setattr(finding, attribute, "changed")


def test_finding_has_slots() -> None:
    """slots=True keeps a typo from silently creating a new attribute."""
    assert Finding.__slots__ == ("invariant_id", "path", "message", "severity")


def test_exit_codes_are_the_values_make_and_ci_read() -> None:
    """A gate returns 0, findings return 1, misuse returns 2."""
    assert (ExitCode.OK, ExitCode.FINDINGS, ExitCode.USAGE) == (0, 1, 2)


def test_every_error_type_is_a_maintainer_error() -> None:
    """One `except MaintainerError` at a process boundary catches all of them."""
    for error_type in (
        CommandFailedError,
        ExecutableNotFoundError,
        GitLsFilesFailedError,
        GitRevParseFailedError,
        MalformedJsonError,
        UnexpectedShapeError,
    ):
        assert issubclass(error_type, MaintainerError)


def test_command_failure_names_the_command_from_its_class() -> None:
    """The raise site passes only the detail; the command line lives on the class."""
    assert str(GitRevParseFailedError("exit 128")) == (
        "`git rev-parse --show-toplevel` failed: exit 128"
    )
    assert str(GitLsFilesFailedError("exit 1")) == "`git ls-files -z` failed: exit 1"


def test_executable_not_found_points_at_make_setup() -> None:
    """The reader is told how to repair the environment, not just what is missing."""
    message = str(ExecutableNotFoundError("shfmt"))
    assert message.startswith("`shfmt` is not on PATH")
    assert "make setup" in message


def test_malformed_json_names_the_file() -> None:
    """A parse failure is useless without the path."""
    error = MalformedJsonError(Path("plugins/demo/.claude-plugin/plugin.json"), "line 3 column 1")
    assert str(error) == ("plugins/demo/.claude-plugin/plugin.json: invalid JSON: line 3 column 1")


def test_unexpected_shape_reports_the_type_it_found() -> None:
    """The message names the file, the required shape and the type that was there."""
    error = UnexpectedShapeError(Path("a/b.json"), "an object", [1, 2])
    assert str(error) == "a/b.json: expected an object, found list"


def test_unexpected_shape_message_is_matchable() -> None:
    """Callers of `pytest.raises(match=...)` get a stable, escapable message."""
    with pytest.raises(UnexpectedShapeError, match=re.escape("expected a string, found int")):
        raise UnexpectedShapeError(Path("a/b.json"), "a string", 7)
