"""Repository access: the git root, tracked files, plugin ids and JSON shape narrowing.

Two rules shape the subprocess calls here. Ruff's `S607` demands a literal absolute
executable path in `argv`, and `S603` demands that every element of `argv` be a literal, so
each call spells its whole command out and passes the binary actually resolved from `PATH`
through `executable=`. `argv[0]` is therefore a placeholder; `git` never reads it.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
import fnmatch
import json
from pathlib import Path
import shutil
import subprocess
from typing import Final, TypeIs

from scripts.common.errors import (
    ExecutableNotFoundError,
    GitLsFilesFailedError,
    GitRevParseFailedError,
    MalformedJsonError,
    UnexpectedShapeError,
)

PLUGINS_DIRNAME: Final = "plugins"
MANIFEST_RELATIVE_PATH: Final = Path(".claude-plugin") / "plugin.json"

# json.loads is annotated `-> Any`; this alias is the one place that Any is converted to
# object, so no caller ever handles an Any-typed value.
_loads: Callable[[str], object] = json.loads


def _git_executable() -> str:
    """Resolve the `git` binary from PATH.

    Returns:
        The absolute path of the `git` executable.

    Raises:
        ExecutableNotFoundError: If `git` is not on PATH.
    """
    executable = shutil.which("git")
    if executable is None:
        raise ExecutableNotFoundError("git")
    return executable


def repo_root(start: Path | None = None) -> Path:
    """Return the absolute path of the repository working tree that contains `start`.

    Args:
        start: Directory to ask from; the process working directory by default.

    Returns:
        The absolute path printed by `git rev-parse --show-toplevel`.

    Raises:
        GitRevParseFailedError: If the directory is not inside a git working tree.
    """
    cwd = Path.cwd() if start is None else start
    try:
        completed = subprocess.run(
            ["/usr/bin/git", "rev-parse", "--show-toplevel"],
            executable=_git_executable(),
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as error:
        raise GitRevParseFailedError(str(error)) from error
    except OSError as error:
        raise GitRevParseFailedError(str(error)) from error
    return Path(completed.stdout.strip())


def tracked_files(root: Path, *pathspecs: str) -> list[str]:
    """List the repository-relative paths git tracks, optionally filtered.

    Filtering is `fnmatch.fnmatchcase` over the full relative path, so `*` crosses `/` the
    way a default git pathspec does. Passing no pathspec returns every tracked path.

    Args:
        root: Any directory inside the working tree; `git ls-files` runs there.
        *pathspecs: Patterns; a path is kept when it matches at least one.

    Returns:
        Sorted repository-relative paths.

    Raises:
        GitLsFilesFailedError: If `git ls-files` cannot run or exits non-zero.
    """
    try:
        completed = subprocess.run(
            ["/usr/bin/git", "ls-files", "-z"],
            executable=_git_executable(),
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as error:
        raise GitLsFilesFailedError(str(error)) from error
    except OSError as error:
        raise GitLsFilesFailedError(str(error)) from error
    paths = [entry for entry in completed.stdout.split("\0") if entry]
    if not pathspecs:
        return sorted(paths)
    return sorted(
        path for path in paths if any(fnmatch.fnmatchcase(path, spec) for spec in pathspecs)
    )


def plugin_ids(root: Path) -> list[str]:
    """List the plugin ids this marketplace ships.

    A directory under `plugins/` counts as a plugin exactly when it holds
    `.claude-plugin/plugin.json`, which is also the name its manifest must carry.

    Args:
        root: The repository root.

    Returns:
        Sorted plugin directory names; empty when `plugins/` does not exist.
    """
    plugins_dir = root / PLUGINS_DIRNAME
    if not plugins_dir.is_dir():
        return []
    return sorted(
        entry.name for entry in plugins_dir.iterdir() if (entry / MANIFEST_RELATIVE_PATH).is_file()
    )


def load_json(path: Path) -> object:
    """Parse a JSON file into untyped data the caller must narrow.

    Args:
        path: The file to read.

    Returns:
        The parsed document as `object`; never `Any`.

    Raises:
        MalformedJsonError: If the file is not valid JSON.
    """
    text = path.read_text(encoding="utf-8")
    try:
        return _loads(text)
    except json.JSONDecodeError as error:
        raise MalformedJsonError(path, str(error)) from error


def _is_mapping(value: object) -> TypeIs[Mapping[object, object]]:
    """Report whether a value is a mapping, without ever touching its unknown contents.

    Args:
        value: The value to test.

    Returns:
        True when `value` is a mapping.
    """
    return isinstance(value, Mapping)


def as_mapping(value: object, *, path: Path) -> dict[str, object]:
    """Narrow a parsed JSON value to a string-keyed mapping.

    Args:
        value: The parsed value.
        path: The file it came from, named in the error.

    Returns:
        The same data as a `dict[str, object]`.

    Raises:
        UnexpectedShapeError: If the value is not a mapping, or a key is not a string.
    """
    if not _is_mapping(value):
        raise UnexpectedShapeError(path, "an object", value)
    narrowed: dict[str, object] = {}
    for key, item in value.items():
        if not isinstance(key, str):
            raise UnexpectedShapeError(path, "an object with string keys", key)
        narrowed[key] = item
    return narrowed


def as_str(value: object, *, path: Path) -> str:
    """Narrow a parsed JSON value to a string.

    Args:
        value: The parsed value.
        path: The file it came from, named in the error.

    Returns:
        The same value, typed `str`.

    Raises:
        UnexpectedShapeError: If the value is not a string.
    """
    if not isinstance(value, str):
        raise UnexpectedShapeError(path, "a string", value)
    return value
