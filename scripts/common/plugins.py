"""Repository access: the git root, tracked files, plugin ids and JSON shape narrowing.

One rule shapes the subprocess calls here: Ruff's `S607` rejects a partial executable path
in `argv`, so every call writes a literal absolute path as `argv[0]` and passes the binary
actually resolved from `PATH` through `executable=`. `argv[0]` is therefore a placeholder;
`git` never reads it. (`S603` is ignored repository-wide, see `pyproject.toml`.)
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
import fnmatch
import json
from pathlib import Path
import shutil
import subprocess
from typing import Final, TypeIs

from scripts.common.errors import (
    ExecutableNotFoundError,
    GitCommandFailedError,
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


def working_files(root: Path, *pathspecs: str) -> list[str]:
    """List the paths the working tree holds and the repository would ship.

    `tracked_files` answers from the index alone, which is what a validator wants: it checks
    what a plugin ships. A linter wants the other set — everything a commit could include —
    so this adds the untracked, non-ignored files and drops the tracked paths that have been
    deleted from the working tree. Filtering is the same `fnmatch.fnmatchcase` as
    `tracked_files`, so `*` crosses `/`.

    Args:
        root: Any directory inside the working tree; `git ls-files` runs there.
        *pathspecs: Patterns; a path is kept when it matches at least one.

    Returns:
        Sorted repository-relative paths that exist as files right now.

    Raises:
        GitLsFilesFailedError: If `git ls-files` cannot run or exits non-zero.
    """
    try:
        completed = subprocess.run(
            ["/usr/bin/git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
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
    paths = {entry for entry in completed.stdout.split("\0") if entry}
    kept = [path for path in paths if (root / path).is_file()]
    if not pathspecs:
        return sorted(kept)
    return sorted(
        path for path in kept if any(fnmatch.fnmatchcase(path, spec) for spec in pathspecs)
    )


def git_output(root: Path, args: Sequence[str]) -> str:
    """Run a git command in the working tree and return its standard output.

    This is the general-purpose call the fixed-purpose helpers above do not cover: the
    argument list is built at run time by the caller (a ref, a pathspec, a tag pattern).

    Args:
        root: The directory git runs in.
        args: The arguments after the binary, for example `["tag", "--list", "x--v*"]`.

    Returns:
        Standard output, with no trailing newline stripped beyond what git emits.

    Raises:
        GitCommandFailedError: If git cannot start or exits non-zero.
        ExecutableNotFoundError: If `git` is not on PATH.

    Note:
        The call passes `check=False` and inspects `returncode` itself, because
        `CalledProcessError.stderr` is typed `Any` and reading it would violate `reportAny`.
    """
    try:
        completed = subprocess.run(
            ["/usr/bin/git", *args],
            executable=_git_executable(),
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as error:
        raise GitCommandFailedError(args, str(error)) from error
    if completed.returncode != 0:
        raise GitCommandFailedError(
            args, completed.stderr.strip() or f"exit {completed.returncode}"
        )
    return completed.stdout


def git_output_or_none(root: Path, args: Sequence[str]) -> str | None:
    """Run a git command and return None instead of raising when it exits non-zero.

    Reading a path that does not exist at a given ref is an ordinary outcome, not a failure:
    a renamed or newly added plugin has no file at its predecessor's tag.

    Args:
        root: The directory git runs in.
        args: The arguments after the binary.

    Returns:
        Standard output, or None when git refused the request.

    Raises:
        ExecutableNotFoundError: If `git` is not on PATH.
    """
    try:
        return git_output(root, args)
    except GitCommandFailedError:
        return None


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


def parse_json(text: str, *, path: Path) -> object:
    """Parse JSON text into untyped data the caller must narrow.

    Args:
        text: The document, which may come from a file or from `git show`.
        path: The path named in the error; for a ref, the path the text was read at.

    Returns:
        The parsed document as `object`; never `Any`.

    Raises:
        MalformedJsonError: If the text is not valid JSON.
    """
    try:
        return _loads(text)
    except json.JSONDecodeError as error:
        raise MalformedJsonError(path, str(error)) from error


def load_json(path: Path) -> object:
    """Parse a JSON file into untyped data the caller must narrow.

    Args:
        path: The file to read.

    Returns:
        The parsed document as `object`; never `Any`.

    Raises:
        MalformedJsonError: If the file is not valid JSON.
    """
    return parse_json(path.read_text(encoding="utf-8"), path=path)


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
