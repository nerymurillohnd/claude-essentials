"""`make test-slow`, second half: every plugin's own suite, under every bash that matters.

Two interpreters run each suite, because the plugins target `bash` 3.2 as their floor and
macOS ships exactly that at `/bin/bash` while `bash` on `PATH` is usually 5.x. A suite that
only ever runs under 5.x cannot catch a 3.2 regression, which is the defect this target
exists for.

The Python floor run is **advisory** until Follow-up PR #1 (`DEBT-0029`): the shipped
`ccdocs.py` is not yet in `make lint` or `make types`, so making its floor run a gate here
would fail the pipeline on work that is deliberately scheduled for that pull request.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import os
from pathlib import Path
import re
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

SUITE_GLOB: Final = "plugins/*test-*.sh"
"""Every tracked plugin suite; `tracked_files` matches `*` across directory separators."""

FALLBACK_BASH: Final = "/bin/bash"
"""The system interpreter macOS ships, which is the 3.2 floor the plugins target."""

SUITE_TIMEOUT: Final = 900
"""Seconds one suite gets under one interpreter before it is abandoned."""

PYTHON_ROW: Final = "python"
"""The Requirements label that carries a plugin's declared Python floor."""

ADVISORY_PREFIX: Final = "DEBT-0029 advisory:"
"""Every line of the Python floor run carries this, so nothing reads it as a gate result."""

DOWNLOADABLE: Final = re.compile(r"cpython-(?P<version>3\.\d+)\.")
"""A version `uv python list --only-downloads` offers, used when the declared floor is gone."""

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
    return [rel for rel in tracked_files(root, SUITE_GLOB) if "/test-" in rel]


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


def uv_binary() -> str | None:
    """Resolve `uv`, which installs the interpreter a plugin's floor names.

    `uv` is maintainer tooling and is never required of a user; the floor run is skipped
    when it is absent.

    Returns:
        Its path, or None.
    """
    found = shutil.which("uv")
    if found is not None:
        return found
    candidate = Path.home() / ".local" / "bin" / "uv"
    return str(candidate) if candidate.is_file() else None


def _uv(binary: str, args: Sequence[str]) -> tuple[int, str, str]:
    """Run `uv` and capture what it said, keeping the two streams apart.

    `uv python find` writes its diagnostics to standard error and only the interpreter path
    to standard output, so a merged capture would hand a warning back as a path.

    Args:
        binary: The resolved `uv` path.
        args: Arguments after the binary.

    Returns:
        Its exit status, its standard output and its standard error, all stripped.
    """
    try:
        completed = subprocess.run(
            ["/usr/bin/uv", *args],
            executable=binary,
            check=False,
            capture_output=True,
            text=True,
            timeout=SUITE_TIMEOUT,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return 1, "", str(error)
    return completed.returncode, completed.stdout.strip(), completed.stderr.strip()


def floor_run(root: Path, plugin_id: str) -> list[str]:
    """Run a plugin's shipped Python under the floor its README declares (advisory).

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
    if floor is None:
        return [f"{ADVISORY_PREFIX} {plugin_id} ships Python but its README declares no floor"]
    binary = uv_binary()
    if binary is None:
        return [
            f"{ADVISORY_PREFIX} {plugin_id}: `uv` is not available, floor {floor} not exercised"
        ]
    return _floor_lines(root, plugin_id, floor, binary, scripts)


def _floor_lines(
    root: Path, plugin_id: str, floor: str, binary: str, scripts: Sequence[str]
) -> list[str]:
    """Install the declared interpreter and smoke every shipped script under it.

    Args:
        root: The repository root.
        plugin_id: The plugin directory name.
        floor: The declared minimum version.
        binary: The resolved `uv` path.
        scripts: The plugin's shipped `.py` files.

    Returns:
        The advisory lines, starting with what `uv python install` reported.
    """
    status, out, err = _uv(binary, ["python", "install", floor])
    said = (err or out).splitlines()[-1] if (err or out) else ""
    lines = [f"{ADVISORY_PREFIX} uv python install {floor} -> exit {status}: {said}"]
    requested = floor
    found_status, found, found_err = _uv(binary, ["python", "find", floor])
    if found_status != 0 or not found:
        lowest = lowest_available(binary)
        if lowest is None:
            lines.append(f"{ADVISORY_PREFIX} {plugin_id}: no interpreter for {floor}: {found_err}")
            return lines
        lines.append(
            f"{ADVISORY_PREFIX} {plugin_id}: {floor} is not downloadable;"
            f" falling back to the lowest uv offers, {lowest}"
        )
        requested = lowest
        _install = _uv(binary, ["python", "install", lowest])
        found_status, found, found_err = _uv(binary, ["python", "find", lowest])
        if found_status != 0 or not found:
            lines.append(f"{ADVISORY_PREFIX} {plugin_id}: no interpreter for {lowest}: {found_err}")
            return lines
    interpreter = found.splitlines()[-1].strip()
    lines.append(f"{ADVISORY_PREFIX} {plugin_id}: interpreter {interpreter} (Python {requested})")
    lines.extend(_smoke_line(root, interpreter, script) for script in scripts)
    return lines


def lowest_available(binary: str) -> str | None:
    """Return the lowest CPython minor version `uv` can still download.

    A plugin may declare a floor older than anything `uv` publishes a build for; running the
    script under the lowest available interpreter is still worth more than not running it.

    Args:
        binary: The resolved `uv` path.

    Returns:
        A `3.x` version, or None when the listing cannot be read.
    """
    status, out, err = _uv(binary, ["python", "list", "--only-downloads"])
    if status != 0:
        return None
    versions = {match.group("version") for match in DOWNLOADABLE.finditer(out + err)}
    if not versions:
        return None
    return min(versions, key=lambda value: int(value.split(".")[1]))


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
