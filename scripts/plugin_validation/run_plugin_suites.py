"""`make test-slow`, second half: every plugin's own suite, under every bash that matters.

Two interpreters run each suite, because the plugins target `bash` 3.2 as their floor and
macOS ships exactly that at `/bin/bash` while `bash` on `PATH` is usually 5.x. A suite that
only ever runs under 5.x cannot catch a 3.2 regression, which is the defect this target
exists for.

Then every shipped Python script is smoke-run once, with this repository's own interpreter.
That run never installs or downloads an interpreter: a gate that wrote to the maintainer's
global uv store installed CPython 3.8 there on 2026-09-21. The floor a plugin's README
declares is therefore reported, not exercised; the line says so, and the run stays
**advisory** (`DEBT-0029`) because `ccdocs.py` is not yet in `make lint` or `make types`.
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

ADVISORY_PREFIX: Final = "DEBT-0029 advisory:"
"""Every line of the Python smoke run carries this, so nothing reads it as a gate result."""

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


def floor_run(root: Path, plugin_id: str) -> list[str]:
    """Smoke-run a plugin's shipped Python with this repository's interpreter (advisory).

    Nothing is installed: the interpreter is the one running this module. The README's
    declared floor is named so a reader never mistakes this run for a floor check.

    Args:
        root: The repository root.
        plugin_id: The plugin directory name.

    Returns:
        The lines to print; each one is prefixed as advisory.
    """
    scripts = [rel for rel in shipped_scripts(root, plugin_id) if rel.endswith(PYTHON_SUFFIX)]
    if not scripts:
        return []
    floor = declared_python_floor(root, plugin_id)
    running = f"{sys.version_info.major}.{sys.version_info.minor}"
    declared = f"its README declares {floor}" if floor else "its README declares no floor"
    header = (
        f"{ADVISORY_PREFIX} {plugin_id}: smoke run under Python {running} only;"
        f" {declared}, which is not exercised"
    )
    lines = [header]
    lines.extend(_smoke_line(root, sys.executable, script) for script in scripts)
    return lines


def _smoke_line(root: Path, interpreter: str, script: str) -> str:
    """Run one shipped script's smoke command under a given interpreter.

    Args:
        root: The repository root.
        interpreter: The interpreter to run it with.
        script: The script's repository-relative path.

    Returns:
        One advisory line reporting the outcome.
    """
    # CPython derives its prefix from argv[0], so the interpreter is passed as argv[0]
    # itself rather than through `executable=`; a placeholder makes it fail to start.
    try:
        completed = subprocess.run(
            [interpreter, str(root / script), SMOKE_ARGUMENT],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
            timeout=SUITE_TIMEOUT,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return f"{ADVISORY_PREFIX} {script} {SMOKE_ARGUMENT} -> could not run: {error}"
    return f"{ADVISORY_PREFIX} {script} {SMOKE_ARGUMENT} -> exit {completed.returncode}"


def main(argv: Sequence[str] | None = None) -> int:
    """Run every plugin suite, then the advisory Python floor run.

    Args:
        argv: Arguments without the program name; `sys.argv[1:]` when None.

    Returns:
        0 when every suite passed, 1 when one failed, 2 when the tree is unusable. The
        floor run never changes the status.
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
        advisories = [line for plugin_id in plugin_ids(root) for line in floor_run(root, plugin_id)]
    except (MaintainerError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return int(ExitCode.USAGE)
    for result in results:
        status = "pass" if result.ok else "FAIL"
        print(f"{status}  {result.suite}  [{result.interpreter}]  {result.detail}")
    for line in advisories:
        print(line)
    return int(ExitCode.FINDINGS if any(not result.ok for result in results) else ExitCode.OK)


if __name__ == "__main__":
    raise SystemExit(main())
