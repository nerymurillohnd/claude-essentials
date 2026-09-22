"""L1: ShellCheck and shfmt over every shell file the working tree holds.

The defect this catches: a hook or a plugin test that is only exercised when Claude fires it,
so a quoting bug or an unset variable reaches the maintainer as a hook that silently does
nothing. ShellCheck reads `.shellcheckrc` (the repository policy, Q2's floor) and shfmt reads
`.editorconfig`, so the editor, this gate and CI agree by construction.

Discovery matches `post-edit.sh`: a file counts as shell when its name ends in `.sh` or its
first line is a `sh`/`bash` shebang. Nothing is classified by directory, so a shell script
without an extension inside a plugin is still checked.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Final

from scripts.common.errors import Finding
from scripts.lint.tools import chunks, run, tool_path

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

INVARIANT: Final = "L1"
"""The ID every message in this module starts with."""

SHELL_SUFFIX: Final = ".sh"
"""The extension that makes a file shell without reading it."""

SHEBANG: Final = re.compile(r"^#!.*[/ ](ba)?sh(\s|$)")
"""A `sh` or `bash` shebang, the same shape `post-edit.sh` matches."""

GCC_LINE: Final = re.compile(r"^(?P<path>[^:]+):(?P<line>\d+):(?P<column>\d+):\s*(?P<rest>.+)$")
"""One ShellCheck finding in `gcc` format: path, line, column, then level and message."""

DIFF_HEADER: Final = re.compile(r"^--- (?P<path>.+?)(?:\.orig)?$")
"""The first line of one file's hunk in `shfmt -d` output."""

DIFF_BUDGET: Final = 1200
"""How much of a file's diff a finding carries before it stops being readable."""


def is_shell_file(root: Path, rel: str) -> bool:
    """Report whether one path is a shell script.

    Args:
        root: The repository root.
        rel: The repository-relative path.

    Returns:
        True for a `.sh` file or a file whose first line is a `sh`/`bash` shebang.
    """
    if rel.endswith(SHELL_SUFFIX):
        return True
    try:
        with (root / rel).open(encoding="utf-8", errors="replace") as handle:
            first = handle.readline()
    except OSError:
        return False
    return SHEBANG.match(first) is not None


def select(root: Path, paths: Sequence[str]) -> list[str]:
    """Keep the shell scripts out of a candidate list.

    Args:
        root: The repository root.
        paths: Repository-relative candidate paths.

    Returns:
        The shell scripts among them, in the order they arrived.
    """
    return [rel for rel in paths if is_shell_file(root, rel)]


def _shellcheck(root: Path, paths: Sequence[str]) -> list[Finding]:
    """Run ShellCheck over a path list and turn its output into findings.

    Args:
        root: The repository root, which is also the directory ShellCheck runs in.
        paths: The shell scripts to check.

    Returns:
        One finding per reported line.

    Raises:
        ExecutableNotFoundError: If `.venv/bin/shellcheck` is missing.
    """
    executable = tool_path(root, "shellcheck")
    findings: list[Finding] = []
    for batch in chunks(paths):
        completed = run(executable, ["-x", "-f", "gcc", *batch], cwd=root)
        for line in completed.stdout.splitlines():
            match = GCC_LINE.match(line)
            if match is None:
                continue
            findings.append(
                Finding(INVARIANT, match["path"], f"line {match['line']}: {match['rest']}")
            )
    return findings


def _split_diff(text: str) -> dict[str, str]:
    """Group `shfmt -d` output by the file each hunk belongs to.

    Args:
        text: Everything shfmt printed on standard output.

    Returns:
        A diff per repository-relative path, in the order shfmt printed them.
    """
    diffs: dict[str, list[str]] = {}
    current: list[str] | None = None
    for line in text.splitlines():
        header = DIFF_HEADER.match(line)
        if header is not None:
            current = diffs.setdefault(header["path"], [])
        if current is not None:
            current.append(line)
    return {path: "\n".join(lines) for path, lines in diffs.items()}


def _shfmt(root: Path, paths: Sequence[str]) -> list[Finding]:
    """Run `shfmt -d` over a path list and report every file that would change.

    Args:
        root: The repository root, which is also where `.editorconfig` is read from.
        paths: The shell scripts to check.

    Returns:
        One finding per file shfmt would rewrite.

    Raises:
        ExecutableNotFoundError: If `.venv/bin/shfmt` is missing.
    """
    executable = tool_path(root, "shfmt")
    findings: list[Finding] = []
    for batch in chunks(paths):
        completed = run(executable, ["-d", *batch], cwd=root)
        for path, diff in _split_diff(completed.stdout).items():
            findings.append(
                Finding(
                    INVARIANT,
                    path,
                    f"shfmt would reformat it; run `make fix`:\n{diff[:DIFF_BUDGET]}",
                )
            )
    return findings


def check(root: Path, paths: Sequence[str]) -> list[Finding]:
    """Run both shell checks over the shell scripts in a candidate list.

    Args:
        root: The repository root.
        paths: Repository-relative candidate paths; non-shell files are ignored.

    Returns:
        Every finding, ShellCheck's first.

    Raises:
        ExecutableNotFoundError: If either locked binary is missing.
    """
    selected = select(root, paths)
    if not selected:
        return []
    return [*_shellcheck(root, selected), *_shfmt(root, selected)]


def fix(root: Path, paths: Sequence[str], *, dry_run: bool = False) -> list[str]:
    """Rewrite the shell scripts shfmt would change.

    ShellCheck has no writer: a finding it reports is a defect to fix in code, never
    something a formatter can absorb (the repository forbids blanket directives).

    Args:
        root: The repository root.
        paths: Repository-relative candidate paths; non-shell files are ignored.
        dry_run: When true, report what would change and write nothing.

    Returns:
        The repository-relative paths that were rewritten, or would be.

    Raises:
        ExecutableNotFoundError: If `.venv/bin/shfmt` is missing.
    """
    selected = select(root, paths)
    if not selected:
        return []
    executable = tool_path(root, "shfmt")
    changed: list[str] = []
    for batch in chunks(selected):
        completed = run(executable, ["-l", *batch], cwd=root)
        listed = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
        if listed and not dry_run:
            _ = run(executable, ["-w", *listed], cwd=root)
        changed.extend(listed)
    return changed
