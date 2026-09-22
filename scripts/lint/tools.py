"""The locked binaries the lint area shells out to, and one way to run them.

Every tool the gate uses lives in `.venv/bin/`, installed from `uv.lock`: ShellCheck, shfmt,
actionlint and zizmor. Resolving them from `PATH` instead would let a Homebrew copy of a
different version answer for the gate, which is the drift `G3` exists to catch, so the path
is built from the repository root and a missing binary is an error rather than a skip
(fail closed, §A4).
"""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
from typing import TYPE_CHECKING, Final

from scripts.common.errors import ExecutableNotFoundError

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

VENV_BIN: Final = Path(".venv") / "bin"
"""Where `make setup` puts every locked binary, relative to the repository root."""

CHUNK: Final = 200
"""How many paths go into one command line, well under any `ARG_MAX` on macOS or Linux."""


def tool_path(root: Path, name: str) -> Path:
    """Resolve one locked binary inside the project environment.

    Args:
        root: The repository root.
        name: The binary's file name, for example `shellcheck`.

    Returns:
        The absolute path of the binary.

    Raises:
        ExecutableNotFoundError: If `.venv` does not hold it, which means `make setup` has
            not run in this tree.
    """
    path = root / VENV_BIN / name
    if not path.is_file():
        raise ExecutableNotFoundError(str(path))
    return path


def venv_env(root: Path) -> dict[str, str]:
    """Build an environment whose `PATH` starts with the project environment.

    basedpyright resolves imports from the interpreter it finds first, so it has to run with
    `.venv/bin` ahead of everything else — the same thing `make types` does.

    Args:
        root: The repository root.

    Returns:
        A copy of this process's environment with `PATH` prefixed.
    """
    environment = dict(os.environ)
    current = environment.get("PATH")
    prefix = str(root / VENV_BIN)
    environment["PATH"] = prefix if current is None else f"{prefix}{os.pathsep}{current}"
    return environment


def run(
    executable: Path,
    args: Sequence[str],
    *,
    cwd: Path,
    env: Mapping[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run a locked binary and capture both streams without raising on findings.

    A linter exits non-zero exactly when it has something to say, so `check=False` is the
    contract here and the caller reads `returncode` itself.

    Args:
        executable: The binary to run.
        args: The arguments after the binary.
        cwd: The directory to run in, so `.shellcheckrc` and `.editorconfig` resolve.
        env: The environment to run under; this process's own when None.

    Returns:
        The completed process, with `stdout` and `stderr` as text.

    Raises:
        ExecutableNotFoundError: If the binary disappeared between resolution and the call.
    """
    try:
        return subprocess.run(
            [str(executable), *args],
            executable=str(executable),
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
            env=None if env is None else dict(env),
        )
    except OSError as error:
        raise ExecutableNotFoundError(str(executable)) from error


def chunks(paths: Sequence[str]) -> list[list[str]]:
    """Split a path list into command lines a single `exec` can carry.

    Args:
        paths: Repository-relative paths, in the order they should be passed.

    Returns:
        One list per command line; empty when there is nothing to run.
    """
    return [list(paths[start : start + CHUNK]) for start in range(0, len(paths), CHUNK)]
