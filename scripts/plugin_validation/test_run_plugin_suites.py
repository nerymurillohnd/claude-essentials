"""Every plugin suite, under every bash that matters, plus the advisory floor run.

The parameter ids carry the interpreter path, so `pytest -m slow -v -k plugin_suites` shows
which bash each suite ran under. That is the evidence the 3.2 floor is actually exercised,
and not merely claimed.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from scripts.common.plugins import repo_root
from scripts.plugin_validation.run_plugin_suites import (
    FALLBACK_BASH,
    declared_python_floor,
    interpreters,
    lowest_available,
    run_suite,
    suites,
    uv_binary,
)
from scripts.plugin_validation.script_env import SHARED_TEST_BASH

if TYPE_CHECKING:
    from collections.abc import Sequence

INTERPRETERS: Sequence[str] = interpreters()
"""Resolved once, so the parameter ids are stable within a run."""


def test_every_plugin_suite_is_found() -> None:
    """A suite that the runner never discovers is a suite nobody runs."""
    found = suites(repo_root())
    assert found
    assert all(rel.endswith(".sh") and "/test-" in rel for rel in found)


def test_the_system_bash_is_included() -> None:
    """MacOS ships bash 3.2 at `/bin/bash`, which is the floor the plugins target."""
    if not Path(FALLBACK_BASH).is_file():
        pytest.skip(f"{FALLBACK_BASH} does not exist on this machine")
    assert FALLBACK_BASH in INTERPRETERS


def test_the_declared_floor_is_read_from_the_readme() -> None:
    """The Requirements table is the contract the floor run is measured against."""
    assert declared_python_floor(repo_root(), "agent-self-knowledge") == "3.7"
    assert declared_python_floor(repo_root(), "verify-completion") is None


@pytest.mark.slow
@pytest.mark.parametrize("interpreter", INTERPRETERS, ids=list(INTERPRETERS))
def test_the_first_suite_runs_under_each_interpreter(interpreter: str) -> None:
    """One suite per interpreter, as the smoke that the runner and the export work.

    The full matrix is `make test-slow`'s `run_plugin_suites` step; repeating it here would
    double a four-minute run for no extra signal.

    Args:
        interpreter: The bash binary to run under.
    """
    root = repo_root()
    result = run_suite(root, suites(root)[0], interpreter)
    assert result.ok, f"{result.suite} failed under {interpreter}: {result.detail}"
    assert result.interpreter == interpreter


def test_the_shared_fallback_is_the_variable_the_suites_read() -> None:
    """Every suite in this marketplace honours the same fallback variable."""
    root = repo_root()
    texts = [(root / rel).read_text(encoding="utf-8") for rel in suites(root)]
    assert all(SHARED_TEST_BASH in text for text in texts)


@pytest.mark.slow
def test_the_floor_fallback_names_a_version_uv_can_install() -> None:
    """When a declared floor predates uv's builds, the run says so and uses the lowest."""
    binary = uv_binary()
    if binary is None:
        pytest.skip("uv is not available")
    lowest = lowest_available(binary)
    assert lowest is not None
    assert lowest.startswith("3.")
