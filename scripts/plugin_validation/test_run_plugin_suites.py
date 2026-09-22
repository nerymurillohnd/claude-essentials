"""Every plugin suite, under every bash that matters, plus the advisory Python smoke run.

The parameter ids carry the interpreter path, so `pytest -m slow -v -k plugin_suites` shows
which bash each suite ran under. That is the evidence the 3.2 floor is actually exercised,
and not merely claimed.
"""

from __future__ import annotations

from pathlib import Path
import sys
from typing import TYPE_CHECKING

import pytest

from scripts.common.plugins import repo_root
from scripts.plugin_validation import run_plugin_suites
from scripts.plugin_validation.run_plugin_suites import (
    FALLBACK_BASH,
    declared_python_floor,
    floor_run,
    interpreters,
    run_suite,
    suites,
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
    """MacOS ships bash 3.2 at `/bin/bash`, which is the floor the plugins target.

    The runner keeps one interpreter per file, so on a merged-/usr system (Ubuntu:
    `/bin/bash` and `/usr/bin/bash` are the same file) the system bash is covered by
    whichever path `bash` resolved to. Compare files, never path strings.
    """
    fallback = Path(FALLBACK_BASH)
    if not fallback.is_file():
        pytest.skip(f"{FALLBACK_BASH} does not exist on this machine")
    assert fallback.resolve() in {Path(interpreter).resolve() for interpreter in INTERPRETERS}


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


def test_the_python_smoke_run_never_installs_an_interpreter() -> None:
    """A gate that installs interpreters mutates the maintainer's machine (2026-09-21: 3.8).

    The module may not ask `uv` for anything, and a plugin that ships Python gets one line
    naming the interpreter it really ran under.
    """
    source = Path(run_plugin_suites.__file__).read_text(encoding="utf-8")
    for forbidden in ("python install", "python find", "only-downloads", '"uv"'):
        assert forbidden not in source, forbidden
    lines = floor_run(repo_root(), "agent-self-knowledge")
    running = f"{sys.version_info.major}.{sys.version_info.minor}"
    assert f"smoke run under Python {running} only" in lines[0]
    assert "which is not exercised" in lines[0]
