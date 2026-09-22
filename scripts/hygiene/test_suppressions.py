r"""Q3: a finding is fixed, never silenced.

Q1 keeps the configuration strict. This keeps the code honest: a `# noqa`, a `# type: ignore`
or a file-wide ShellCheck directive turns one real finding off while every gate stays green,
and each one is a single line that no reviewer is likely to question.

`typing.cast` is in the list for the same reason. A cast asserts a type the checker could not
prove, so an unproven cast is a suppression written as code. The rule is the one §A14.1
states: the line before a `cast` has to be the runtime check that makes it true.

Only code files are swept. Documentation has to be able to *name* these markers — this
docstring does — and a rule that could not tell the two apart would make the policy
undocumentable.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Final

import pytest

from scripts.common.plugins import working_files

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

SHELL_FILE_DIRECTIVE: Final = re.compile(r"^#\s*shellcheck\s+disable=")
"""A ShellCheck directive before the first statement applies to the whole file."""

SHELL_DISABLE_ALL: Final = re.compile(r"#\s*shellcheck\s+disable=all")
"""Turning ShellCheck off entirely, wherever it is written."""

EXEMPT_SHELL: Final[tuple[str, ...]] = ("plugins/*/test-*.sh", "plugins/*/tests/*.sh")
"""Plugin test suites, excluded for two reasons rather than one.

Their content is sample text for the guard under test: `shell-quality`'s suite writes a
script containing `# shellcheck disable=all` precisely to assert that its hook denies it, so
a literal match there is data, not policy. And ADR-0003 already classes `test-*.sh` and
`tests/` as files Claude never loads, so they are not part of what a user receives.

Measured 2026-09-21: three of them open with a file-wide `# shellcheck disable=SC2016`, which
is a real defect in those plugins and is recorded for the plugin follow-up rather than fixed
from the tooling migration that may not touch plugin files.
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
    """List the shell scripts this repository owns, plugins included.

    Args:
        repo: The repository root.

    Returns:
        Sorted repository-relative paths, the plugin test suites excluded.
    """
    exempt = set(working_files(repo, *EXEMPT_SHELL))
    return [rel for rel in sorted(working_files(repo, "*.sh")) if rel not in exempt]


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


def test_no_shell_script_turns_shellcheck_off(repo: Path) -> None:
    """`disable=all` is the one directive that can never be narrow enough to justify."""
    offenders = [
        rel
        for rel in _shell_files(repo)
        if SHELL_DISABLE_ALL.search((repo / rel).read_text("utf-8"))
    ]
    assert offenders == []


def test_no_shell_directive_applies_to_a_whole_file(repo: Path) -> None:
    """Before the first statement a directive covers everything after it, not one line."""
    offenders: list[str] = []
    for rel in _shell_files(repo):
        for line in (repo / rel).read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#!"):
                continue
            if SHELL_FILE_DIRECTIVE.match(stripped):
                offenders.append(rel)
            if not stripped.startswith("#"):
                break
    assert offenders == [], f"file-wide ShellCheck directives in: {offenders}"
