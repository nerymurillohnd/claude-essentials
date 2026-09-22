"""`make test-slow`, second half: every plugin's own suite, under every bash that matters.

Two interpreters run each suite, because the plugins target `bash` 3.2 as their floor and
macOS ships exactly that at `/bin/bash` while `bash` on `PATH` is usually 5.x. A suite that
only ever runs under 5.x cannot catch a 3.2 regression, which is the defect this target
exists for.

Then every shipped Python script is smoke-run once, with this repository's own interpreter,
and its plugin's declared Python floor has to be that interpreter's version. Ruff and
basedpyright check `plugins/**/*.py` against the same version (`make lint`, `make types`), so
the floor a README promises is the one every gate exercises. The run never installs or
downloads an interpreter: a gate that wrote to the maintainer's global uv store installed
CPython 3.8 there on 2026-09-21.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import TYPE_CHECKING, Final

from scripts.common.errors import ExitCode, MaintainerError
from scripts.common.plugins import plugin_ids, repo_root, tracked_files
from scripts.plugin_validation.readme_contract import requirement_rows
from scripts.plugin_validation.runtime_boundary import PYTHON_SUFFIX, shipped_scripts
from scripts.plugin_validation.script_env import SHARED_TEST_BASH

if TYPE_CHECKING:
    from collections.abc import Sequence

SUITE_GLOBS: Final[tuple[str, ...]] = (
    "scripts/plugin_validation/suites/*test-*.sh",
    "plugins/*test-*.sh",
)
"""Where plugin suites live; `tracked_files` matches `*` across directory separators.

A suite belongs to the repository (`scripts/plugin_validation/suites/<id>/`), never to the
plugin, because a plugin ships only what users run. The `plugins/` pattern remains for one
exception: `block-no-verify`'s installer runs its own suite at install time, so there the
suite is runtime (ADR-0007).
"""

FALLBACK_BASH: Final = "/bin/bash"
"""The system interpreter macOS ships, which is the 3.2 floor the plugins target."""

SUITE_TIMEOUT: Final = 900
"""Seconds one suite gets under one interpreter before it is abandoned."""

PYTHON_ROW: Final = "python"
"""The Requirements label that carries a plugin's declared Python floor."""


SMOKE_ARGUMENT: Final = "--help"
"""The one argument a shipped script is smoke-tested with; it must not touch the network."""


@dataclass(frozen=True, slots=True)
class SuiteResult:
    """One suite run under one interpreter.

    Attributes:
        suite: The suite's repository-relative path.
        interpreter: The bash binary it ran under.
        ok: Whether it exited zero.
        detail: The last line of its output when it failed.
    """

    suite: str
    interpreter: str
    ok: bool
    detail: str


def interpreters() -> list[str]:
    """List the bash binaries every suite runs under.

    Returns:
        The `bash` on PATH, plus `/bin/bash` when it is a different file.
    """
    primary = shutil.which("bash") or FALLBACK_BASH
    found = [primary]
    fallback = Path(FALLBACK_BASH)
    if fallback.is_file() and fallback.resolve() != Path(primary).resolve():
        found.append(FALLBACK_BASH)
    return found


def suites(root: Path) -> list[str]:
    """List every tracked plugin suite.

    Args:
        root: The repository root.

    Returns:
        Sorted repository-relative paths.
    """
    found = {rel for pattern in SUITE_GLOBS for rel in tracked_files(root, pattern)}
    return sorted(rel for rel in found if "/test-" in rel)


def run_suite(root: Path, suite: str, interpreter: str) -> SuiteResult:
    """Run one suite by path, with the interpreter exported for the handler under test.

    The suite is executed by its own path rather than through `bash <path>`, so the shebang
    and the exec bit are exercised the way a user's machine exercises them.

    Args:
        root: The repository root.
        suite: The suite's repository-relative path.
        interpreter: The bash binary the suite should run the handler with.

    Returns:
        The outcome.
    """
    environment = dict(os.environ)
    environment[SHARED_TEST_BASH] = interpreter
    try:
        completed = subprocess.run(
            [str(root / suite)],
            cwd=root,
            env=environment,
            check=False,
            capture_output=True,
            text=True,
            timeout=SUITE_TIMEOUT,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return SuiteResult(suite, interpreter, ok=False, detail=str(error))
    output = (completed.stdout + completed.stderr).strip().splitlines()
    return SuiteResult(
        suite, interpreter, ok=completed.returncode == 0, detail=output[-1] if output else ""
    )


def run_all(root: Path) -> list[SuiteResult]:
    """Run every suite under every interpreter.

    Args:
        root: The repository root.

    Returns:
        One result per pair, suites in path order.
    """
    return [
        run_suite(root, suite, interpreter)
        for suite in suites(root)
        for interpreter in interpreters()
    ]


def declared_python_floor(root: Path, plugin_id: str) -> str | None:
    """Read the Python floor a plugin's README declares.

    Args:
        root: The repository root.
        plugin_id: The plugin directory name.

    Returns:
        The minimum version, or None when the README has no Python row.
    """
    readme = root / "plugins" / plugin_id / "README.md"
    if not readme.is_file():
        return None
    for cells in requirement_rows(readme.read_text(encoding="utf-8")):
        if cells[0].strip("`").strip().lower().startswith(PYTHON_ROW):
            floor = cells[1].strip("` ")
            return floor or None
    return None


def floor_problem(floor: str | None, running: str) -> str | None:
    """Say what is wrong with a plugin's declared Python floor, if anything.

    Args:
        floor: The minimum its README declares, or None.
        running: This repository's interpreter version, `major.minor`.

    Returns:
        None when the floor is the repository's Python, else the reason it is not.
    """
    if floor is None:
        return (
            f"its README declares no Python floor; declare {running}, "
            "the Python every gate checks it with"
        )
    if floor != running:
        return (
            f"its README declares Python {floor}, but it is linted, type-checked and run only "
            f"with {running}; declare {running}"
        )
    return None


def smoke_run(root: Path, plugin_id: str) -> list[SuiteResult]:
    """Check a plugin's Python floor and smoke-run its shipped Python with this interpreter.

    Nothing is installed: the interpreter is the one running this module.

    Args:
        root: The repository root.
        plugin_id: The plugin directory name.

    Returns:
        One result for the floor and one per shipped script; empty when it ships no Python.
    """
    scripts = [rel for rel in shipped_scripts(root, plugin_id) if rel.endswith(PYTHON_SUFFIX)]
    if not scripts:
        return []
    running = f"{sys.version_info.major}.{sys.version_info.minor}"
    readme = f"plugins/{plugin_id}/README.md"
    problem = floor_problem(declared_python_floor(root, plugin_id), running)
    results = [
        SuiteResult(readme, f"Python floor {running}", ok=problem is None, detail=problem or "ok")
    ]
    results.extend(_smoke(root, script) for script in scripts)
    return results


def _smoke(root: Path, script: str) -> SuiteResult:
    """Run one shipped script's smoke command under this interpreter.

    Args:
        root: The repository root.
        script: The script's repository-relative path.

    Returns:
        Its result; a script that cannot start or exits non-zero fails.
    """
    label = f"{sys.executable} {SMOKE_ARGUMENT}"
    # CPython derives its prefix from argv[0], so the interpreter is passed as argv[0]
    # itself rather than through `executable=`; a placeholder makes it fail to start.
    try:
        completed = subprocess.run(
            [sys.executable, str(root / script), SMOKE_ARGUMENT],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
            timeout=SUITE_TIMEOUT,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return SuiteResult(script, label, ok=False, detail=f"could not run: {error}")
    ok = completed.returncode == 0
    detail = "ok" if ok else f"exit {completed.returncode}: {completed.stderr.strip()[-300:]}"
    return SuiteResult(script, label, ok=ok, detail=detail)


def main(argv: Sequence[str] | None = None) -> int:
    """Run every plugin suite, then the Python floor check and smoke run.

    Args:
        argv: Arguments without the program name; `sys.argv[1:]` when None.

    Returns:
        0 when every suite, floor and smoke run passed, 1 when one failed, 2 when the tree
        is unusable.
    """
    parser = argparse.ArgumentParser(
        prog="python -m scripts.plugin_validation.run_plugin_suites",
        description="Run every plugin test suite under each bash, then smoke its Python floor.",
    )
    _ = parser.add_argument(
        "--root", default=None, help="run against this tree instead of this one"
    )
    values: dict[str, object] = vars(parser.parse_args(argv))
    raw = values["root"]
    try:
        root = Path(raw) if isinstance(raw, str) else repo_root()
        results = run_all(root)
        results.extend(
            result for plugin_id in plugin_ids(root) for result in smoke_run(root, plugin_id)
        )
    except (MaintainerError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return int(ExitCode.USAGE)
    for result in results:
        status = "pass" if result.ok else "FAIL"
        print(f"{status}  {result.suite}  [{result.interpreter}]  {result.detail}")
    return int(ExitCode.FINDINGS if any(not result.ok for result in results) else ExitCode.OK)


if __name__ == "__main__":
    raise SystemExit(main())
