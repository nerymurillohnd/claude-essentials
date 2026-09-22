"""Shipped Python parses on an old interpreter, so its version check can speak.

A plugin script that needs Python 3.14 checks `sys.version_info` and exits with a message
naming the requirement. That check only runs if the whole file parses first: one walrus or
`match` statement, and an old `python3` stops with a SyntaxError before the message. Ruff's
`per-file-target-version` keeps the syntax at 3.9 for the interpreter macOS ships; this test
holds it to 3.7, the oldest grammar `ast` accepts, which is what the scripts' comments promise.
Measured 2026-09-22: a walrus in `ccdocs.py` broke the promise for 3.7 while every gate passed.
"""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING, Final

import pytest

from scripts.common.plugins import PLUGINS_DIRNAME, repo_root, working_files

if TYPE_CHECKING:
    from pathlib import Path

OLDEST_GRAMMAR: Final = (3, 7)
"""The oldest grammar `ast.parse(feature_version=...)` accepts on the repository's Python."""


def _shipped_python(root: Path) -> list[str]:
    """List the Python files the plugins ship.

    Args:
        root: The repository root.

    Returns:
        Repository-relative paths.
    """
    return [rel for rel in working_files(root, f"{PLUGINS_DIRNAME}/**/*.py") if rel.endswith(".py")]


def test_the_plugins_ship_python() -> None:
    """The parametrized test below has something to check."""
    assert _shipped_python(repo_root())


@pytest.mark.parametrize("rel", _shipped_python(repo_root()))
def test_shipped_python_parses_on_the_oldest_grammar(rel: str) -> None:
    """Each shipped script parses as Python 3.7, so its version check runs before any error.

    Args:
        rel: The script's repository-relative path.
    """
    source = (repo_root() / rel).read_text(encoding="utf-8")
    _ = ast.parse(source, filename=rel, feature_version=OLDEST_GRAMMAR)


def test_a_walrus_is_refused_at_the_oldest_grammar() -> None:
    """The check fails on the construct that broke it, so a pass means something."""
    with pytest.raises(SyntaxError):
        _ = ast.parse("if (x := 1):\n    pass\n", feature_version=OLDEST_GRAMMAR)
