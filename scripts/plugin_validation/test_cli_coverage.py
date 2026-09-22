"""The dated tool list, and the nightly diff against the live documentation."""

from __future__ import annotations

import os
from pathlib import Path
import re
from typing import Final

import pytest

from scripts.plugin_validation.cli_coverage import (
    CLI_PROBE_MATRIX,
    DOCS_DATE,
    DOCS_SOURCES,
    KNOWN_TOOLS,
    is_known_tool,
    unknown_tools,
)

DOCS_DIR_VARIABLE: Final = "CLAUDE_CODE_DOCS_DIR"
"""Where a local copy of the live documentation sits; the nightly job sets it."""

TOOL_WORD: Final = re.compile(r"`(?P<name>[A-Z][A-Za-z]{2,24})`")
"""A backticked identifier in the documentation, which may or may not be a tool."""


def test_every_documented_tool_is_a_plain_name() -> None:
    """A tool name is a bare identifier; a grant's pattern is parsed separately."""
    assert all(name.isidentifier() for name in KNOWN_TOOLS)


def test_mcp_tools_are_always_accepted() -> None:
    """An MCP server's tools cannot be enumerated ahead of time, so the prefix is enough."""
    assert is_known_tool("mcp__github__get_me")
    assert not is_known_tool("NotATool")


def test_unknown_tools_reports_only_the_unknown() -> None:
    """The helper that feeds the S4 and H3 warnings names exactly what it does not know."""
    assert unknown_tools(frozenset({"Bash", "mcp__x__y", "Nope"})) == ["Nope"]


def test_the_probe_matrix_justifies_each_overlapping_invariant() -> None:
    """A row the CLI already catches carries no invariant; one it misses names one (P14)."""
    for probe in CLI_PROBE_MATRIX:
        assert (probe.invariant_id is None) == probe.caught, probe.defect


def test_the_constants_are_dated() -> None:
    """A constant read from a living page states when it was read."""
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", DOCS_DATE)
    assert DOCS_SOURCES


@pytest.mark.coverage_matrix
def test_known_tools_against_the_live_documentation() -> None:
    """Diff the dated list against a fetched copy of the reference pages.

    The nightly job points `CLAUDE_CODE_DOCS_DIR` at a fresh fetch; a laptop run of
    `make test-fast` never reaches this test, because it is excluded by its marker.
    """
    location = os.environ.get(DOCS_DIR_VARIABLE)
    if location is None:
        pytest.skip(f"{DOCS_DIR_VARIABLE} is not set")
    directory = Path(location)
    if not directory.is_dir():
        pytest.skip(f"{location} is not a directory")
    text = "\n".join(path.read_text(encoding="utf-8") for path in sorted(directory.glob("*.md")))
    mentioned = {match.group("name") for match in TOOL_WORD.finditer(text)}
    missing = sorted(KNOWN_TOOLS - mentioned)
    assert not missing, f"named in KNOWN_TOOLS but absent from the fetched pages: {missing}"
