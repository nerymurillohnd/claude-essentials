"""Shared readers for the repository-wide invariants.

Every check in this area reads the real tree rather than a fixture: the defect it looks for
is a state this repository could fall into, not a state a temporary directory could. The
helpers here are the two readings they all need — the configuration files as parsed TOML, and
the tracked files as a list.
"""

from __future__ import annotations

from pathlib import Path
import tomllib
from typing import TYPE_CHECKING, Final

import pytest

from scripts.common.jsontext import is_json_array, is_json_object
from scripts.common.plugins import repo_root

if TYPE_CHECKING:
    from collections.abc import Mapping

HERE: Final = Path(__file__).resolve().parent
"""This area's directory, so a fixture finds the checkout without using the cwd."""

PYPROJECT: Final = "pyproject.toml"
"""The one configuration file every Python tool in this repository reads."""

SHELLCHECKRC: Final = ".shellcheckrc"
"""ShellCheck reads no `pyproject.toml`, so its policy stays a file of its own."""


def toml_document(path: Path) -> Mapping[str, object]:
    """Parse a TOML file into untyped data the caller narrows.

    Args:
        path: The file to read.

    Returns:
        The parsed document; empty when the file is absent.
    """
    if not path.is_file():
        return {}
    return tomllib.loads(path.read_text(encoding="utf-8"))


def nested(document: Mapping[str, object], *keys: str) -> object:
    """Read a nested value out of a parsed TOML document.

    Args:
        document: The parsed document.
        *keys: The path to follow.

    Returns:
        The value, or None when any step is missing or not a table.
    """
    current: object = document
    for key in keys:
        if not is_json_object(current):
            return None
        current = current.get(key)
    return current


def string_list(value: object) -> list[str]:
    """Narrow a parsed TOML value to a list of strings.

    Args:
        value: The parsed value.

    Returns:
        The strings it holds; empty when it is not a list.
    """
    if not is_json_array(value):
        return []
    return [item for item in value if isinstance(item, str)]


def shellcheck_directives(text: str) -> list[str]:
    """Read the non-comment directives out of a ShellCheck rc file.

    Args:
        text: The file's contents.

    Returns:
        One entry per directive line, in order.
    """
    return [
        line.strip()
        for line in text.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


@pytest.fixture
def repo() -> Path:
    """Locate this checkout.

    Returns:
        The repository root.
    """
    return repo_root(HERE)
