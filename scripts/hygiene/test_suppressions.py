r"""Q3: a finding is fixed, never silenced.

Q1 keeps the configuration strict. This keeps the code honest: a `# noqa`, a `# type: ignore`
or a ShellCheck `disable=` turns one real finding off while every gate stays green, and each
one is a single line that no reviewer is likely to question. Every shell script is swept,
plugin test suites included, because a suppression there hides a defect in the suite that is
supposed to catch defects.

`typing.cast` is in the list for the same reason. A cast asserts a type the checker could not
prove, so an unproven cast is a suppression written as code. The rule is the one §A14.1
states: the line before a `cast` has to be the runtime check that makes it true.

Only code files are swept. Documentation has to be able to *name* these markers — this
docstring does — and a rule that could not tell the two apart would make the policy
undocumentable.
"""

from __future__ import annotations

import re
import subprocess
from typing import TYPE_CHECKING, Final

import pytest

from scripts.common.jsontext import is_json_array, is_json_object
from scripts.common.plugins import parse_json, working_files
from scripts.lint.shell_files import select
from scripts.lint.tools import tool_path

if TYPE_CHECKING:
    from pathlib import Path

PYTHON_PATTERNS: Final[tuple[tuple[str, str], ...]] = (
    (r"#\s*noqa", "Ruff's line suppression"),
    (r"#\s*ruff:\s*noqa", "Ruff's file suppression"),
    (r"#\s*ruff:\s*ignore", "Ruff's rule suppression"),
    (r"#\s*type:\s*ignore", "the type-checker suppression"),
    (r"#\s*pyright:\s*ignore", "pyright's suppression"),
    (r"#\s*basedpyright:\s*ignore", "basedpyright's suppression"),
    (r"#\s*pyright:\s*(basic|strict)\b", "a per-file type-checking mode"),
    (r"#\s*shellcheck\s+(?:[a-z-]+=\S+\s+)*disable=", "a ShellCheck suppression in embedded shell"),
    (r"#\s*shellcheck\s+(?:[a-z-]+=\S+\s+)*source=/dev/null", "ShellCheck told to skip a file"),
)
"""Every marker that makes a Python finding disappear, with what it is for the message."""

CAST_CALL: Final = re.compile(r"\bcast\(")
"""A `typing.cast`, which asserts what the checker could not prove."""

RUNTIME_CHECK: Final = re.compile(r"\b(isinstance|issubclass|assert|if|elif)\b")
"""What the line before a cast has to carry for the cast to be earned."""

RECIPE_FILES: Final[tuple[str, ...]] = (
    "Makefile",
    ".claude/hooks/*.sh",
    ".claude/hooks/*/*.sh",
    ".github/workflows/*.yml",
)
"""Everywhere a baseline could be written from, which is what would make one permanent."""

BASELINE_FLAG: Final = "--writebaseline"
"""The flag that creates the baseline; it may appear in no recipe, hook or workflow."""

SHELL_SUPPRESSION: Final = re.compile(
    r"^\s*shellcheck\s+(?:[a-z-]+=\S+\s+)*(?:disable=|source=/dev/null)"
)
"""A ShellCheck directive that silences a finding, as the text of a real comment.

ShellCheck reads a directive as `shellcheck` followed only by `key=value` pairs, so prose that
merely names one, such as `ShellCheck suppression (# shellcheck disable=...)`, is not matched.

`source=<path>` stays allowed: it tells ShellCheck where a sourced file is, so it checks
more, not less. `source=/dev/null` is the opposite, and is banned with `disable=`.
"""


def _python_files(repo: Path) -> list[str]:
    """List the Python this repository owns.

    Args:
        repo: The repository root.

    Returns:
        Sorted repository-relative paths, this file excluded: it names the markers it bans.
    """
    here = __file__.rsplit("/", 1)[-1]
    return [rel for rel in working_files(repo, "scripts/*.py") if not rel.endswith(here)]


def _shell_files(repo: Path) -> list[str]:
    """List every shell script this repository owns, plugin test suites included.

    Args:
        repo: The repository root.

    Returns:
        Sorted repository-relative paths.
    """
    return select(repo, working_files(repo, "*"))


def _comment(entry: object) -> tuple[int, str] | None:
    """Read one shfmt comment node.

    Args:
        entry: An element of a node's `Comments` list.

    Returns:
        `(line, text)`, or None when the node is not a comment; an empty `#` has no `Text`.
    """
    if not is_json_object(entry):
        return None
    mark = entry.get("Hash")
    line = mark.get("Line") if is_json_object(mark) else None
    text = entry.get("Text", "")
    if isinstance(line, int) and isinstance(text, str):
        return line, text
    return None


def _comments(node: object, found: list[tuple[int, str]]) -> None:
    """Collect every comment in a shfmt syntax tree, with its line.

    Args:
        node: A node of the tree `shfmt --to-json` printed.
        found: Where each `(line, text)` is appended.
    """
    if is_json_object(node):
        entries = node.get("Comments")
        if is_json_array(entries):
            found.extend(comment for entry in entries if (comment := _comment(entry)))
        for value in node.values():
            _comments(value, found)
    elif is_json_array(node):
        for value in node:
            _comments(value, found)


def _shell_comments(repo: Path, rel: str) -> list[tuple[int, str]]:
    """Parse one script with shfmt and return its real comments.

    A line that only looks like a directive inside a quoted string is data, and the parser
    is what tells the two apart: `shell-quality`'s suite writes `# shellcheck disable=all`
    into fixtures precisely to prove its hook denies it.

    Args:
        repo: The repository root.
        rel: The script's repository-relative path.

    Returns:
        Every comment, as `(line, text)`.
    """
    completed = subprocess.run(
        [str(tool_path(repo, "shfmt")), "--to-json"],
        input=(repo / rel).read_text(encoding="utf-8"),
        capture_output=True,
        text=True,
        check=True,
    )
    tree = parse_json(completed.stdout, path=repo / rel)
    found: list[tuple[int, str]] = []
    _comments(tree, found)
    return found


@pytest.mark.parametrize(("pattern", "what"), PYTHON_PATTERNS)
def test_no_python_suppression_marker_survives(repo: Path, pattern: str, what: str) -> None:
    """A suppression keeps the gate green while the defect it hides stays in the code."""
    expression = re.compile(pattern)
    offenders = [
        f"{rel}:{number}"
        for rel in _python_files(repo)
        for number, line in enumerate((repo / rel).read_text(encoding="utf-8").splitlines(), 1)
        if expression.search(line)
    ]
    assert offenders == [], f"{what} at: {offenders}"


def test_every_cast_is_preceded_by_the_check_that_proves_it(repo: Path) -> None:
    """A bare cast asserts what nothing verified, which is a suppression written as code."""
    offenders: list[str] = []
    for rel in _python_files(repo):
        lines = (repo / rel).read_text(encoding="utf-8").splitlines()
        for number, line in enumerate(lines, 1):
            if CAST_CALL.search(line) is None:
                continue
            previous = [text for text in lines[: number - 1] if text.strip()]
            if not previous or RUNTIME_CHECK.search(previous[-1]) is None:
                offenders.append(f"{rel}:{number}")
    assert offenders == [], f"casts with no runtime check on the previous line: {offenders}"


def test_no_recipe_can_write_a_baseline(repo: Path) -> None:
    """The baseline suppresses every existing error by design and updates itself."""
    offenders = [
        rel
        for rel in sorted(working_files(repo, *RECIPE_FILES))
        if BASELINE_FLAG in (repo / rel).read_text(encoding="utf-8")
    ]
    assert offenders == []


def test_the_shell_policy_disables_nothing_repository_wide(repo: Path) -> None:
    """A directive in the rc file silences a check in every script at once."""
    text = (repo / ".shellcheckrc").read_text(encoding="utf-8")
    assert "disable=" not in text


@pytest.mark.slow
def test_no_shell_script_silences_shellcheck(repo: Path) -> None:
    """A `disable=` hides a real finding; before the first statement it hides a whole file."""
    offenders = [
        f"{rel}:{line}"
        for rel in _shell_files(repo)
        for line, text in _shell_comments(repo, rel)
        if SHELL_SUPPRESSION.search(text)
    ]
    assert offenders == [], f"ShellCheck suppressions at: {offenders}"
