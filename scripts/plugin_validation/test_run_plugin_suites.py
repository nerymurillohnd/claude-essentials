"""Every plugin suite, under every bash that matters, plus the Python smoke run and floor gate.

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
from scripts.plugin_validation.conftest import PLUGIN_ID, SKILL_ID, track
from scripts.plugin_validation.run_plugin_suites import (
    FALLBACK_BASH,
    declared_python_floor,
    floor_problem,
    interpreters,
    main,
    run_suite,
    smoke_run,
    suites,
)
from scripts.plugin_validation.script_env import SHARED_TEST_BASH, SHARED_TEST_PYTHON

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
    assert declared_python_floor(repo_root(), "agent-self-knowledge") == "3.14"
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


def test_a_suite_gets_the_repository_python(tmp_path: Path) -> None:
    """A CI runner's own `python3` is older than the floor; the suite must not fall back to it.

    Args:
        tmp_path: A scratch repository root.
    """
    suite = tmp_path / "test-echo.sh"
    _ = suite.write_text(
        f'#!/usr/bin/env bash\necho "${{{SHARED_TEST_PYTHON}}}"\n', encoding="utf-8"
    )
    suite.chmod(0o755)
    result = run_suite(tmp_path, "test-echo.sh", "bash")
    assert result.ok
    assert result.detail == sys.executable


def test_the_python_smoke_run_never_installs_an_interpreter() -> None:
    """A gate that installs interpreters mutates the maintainer's machine (2026-09-21: 3.8).

    The module may not ask `uv` for anything, and the shipped script passes its smoke run
    under the repository's own interpreter, which is the floor its README declares.
    """
    source = Path(run_plugin_suites.__file__).read_text(encoding="utf-8")
    for forbidden in ("python install", "python find", "only-downloads", '"uv"'):
        assert forbidden not in source, forbidden
    results = smoke_run(repo_root(), "agent-self-knowledge")
    assert results
    assert all(result.ok for result in results), [result.detail for result in results]


def test_a_python_floor_must_be_the_repository_interpreter() -> None:
    """Shipped Python is checked and run only under the repository's Python, so that is the floor.

    A lower floor promises users something no gate exercises; a higher one cannot be run here.
    """
    running = f"{sys.version_info.major}.{sys.version_info.minor}"
    assert floor_problem(running, running) is None
    for other in ("3.9", "3.99", None):
        problem = floor_problem(other, running)
        assert problem is not None
        assert running in problem


@pytest.mark.slow
def test_a_shipped_script_that_fails_its_smoke_run_fails_the_target(scratch: Path) -> None:
    """The smoke run is a gate: a script that exits non-zero fails, one that exits zero passes.

    Args:
        scratch: The scratch repository root.
    """
    scripts = scratch / "plugins" / PLUGIN_ID / "skills" / SKILL_ID / "scripts"
    track(scratch, scripts / "broken.py", "raise SystemExit(3)\n", executable=True)
    track(scratch, scripts / "healthy.py", "raise SystemExit(0)\n", executable=True)
    by_suite = {result.suite: result for result in smoke_run(scratch, PLUGIN_ID)}
    broken = by_suite[f"plugins/{PLUGIN_ID}/skills/{SKILL_ID}/scripts/broken.py"]
    healthy = by_suite[f"plugins/{PLUGIN_ID}/skills/{SKILL_ID}/scripts/healthy.py"]
    assert not broken.ok
    assert broken.detail.startswith("exit 3")
    assert healthy.ok
    assert main(["--root", str(scratch)]) == 1
