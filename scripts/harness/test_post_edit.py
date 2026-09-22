"""Tests for the post-edit hook: the plugin version reminder, and nothing else.

Since 2026-09-22 the hook never formats, lints or type-checks (the maintainer's decision):
that belongs to `make lint-staged` in the commit guard and to `make check`. What is left is
the reminder that a plugin's installed users receive a runtime change only after its version
is bumped. These tests prove both halves: every kind of edit leaves the file untouched and
never blocks, and the reminder fires once per session for a runtime change and never for an
exempt one.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Final

import pytest

from scripts.common.errors import ExitCode
from scripts.common.jsontext import is_json_object
from scripts.common.plugins import git_output
from scripts.harness.conftest import BASH_BINARIES, hook_output, payload, run_hook

if TYPE_CHECKING:
    from pathlib import Path

HOOK: Final = "post-edit.sh"
"""The hook under test."""

MISFORMATTED_SHELL: Final = '#!/usr/bin/env bash\nif true; then\n        echo "x"\nfi\nrm -rf $1\n'
"""Over-indented and with an unquoted expansion: shfmt and ShellCheck would both object."""

MISFORMATTED_PYTHON: Final = '"""Probe."""\n\nimport os\nx   =  1\n'
"""An unused import and bad spacing: Ruff would both fix and report."""

NON_CANONICAL_JSON: Final = '{"a":1,"b":[1,2]}\n'
"""Valid JSON that is not in the canonical form."""

PLUGIN: Final = "demo"
"""The scratch plugin the reminder cases edit."""

REMINDER: Final = "has runtime changes since demo--v0.1.0"
"""The part of the reminder that names the plugin and its tag."""

RETIRED_TERMS: Final[tuple[str, ...]] = (
    "shfmt",
    "command -v shellcheck",
    "shellcheck -x",
    "ruff",
    "basedpyright",
    "fix-file",
    "biome",
    "node_modules",
)
"""Tool calls the hook must no longer make. `# shellcheck source=` directives are allowed."""


def _edit(file_path: Path, cwd: Path, session: str) -> str:
    """Render the payload Claude Code sends after an `Edit`.

    Args:
        file_path: The file that was edited.
        cwd: The directory Claude works in.
        session: The session id, which keys the once-per-session reminder.

    Returns:
        The JSON text.
    """
    return payload(
        tool_name="Edit",
        tool_input={"file_path": str(file_path)},
        cwd=str(cwd),
        session_id=session,
    )


def _env(project: Path) -> dict[str, str]:
    """Run the hook with `CLAUDE_PROJECT_DIR` pointing at the scratch checkout.

    Args:
        project: The directory the hook treats as the repository.

    Returns:
        This process's environment with the project directory set.
    """
    return {**os.environ, "CLAUDE_PROJECT_DIR": str(project)}


def _context(stdout: str) -> str:
    """Read the additional context a `PostToolUse` hook gave Claude.

    Args:
        stdout: What the hook printed.

    Returns:
        The context text, or an empty string when the hook printed nothing.
    """
    if not stdout.strip():
        return ""
    output = hook_output(stdout).get("hookSpecificOutput")
    if not is_json_object(output):
        return ""
    text = output.get("additionalContext")
    return text if isinstance(text, str) else ""


@pytest.fixture
def plugin_repo(tmp_path: Path) -> Path:
    """Build a checkout with one tagged plugin, the shape the reminder reads.

    Args:
        tmp_path: pytest's scratch directory.

    Returns:
        The repository root.
    """
    root = tmp_path / "repo"
    manifest = root / "plugins" / PLUGIN / ".claude-plugin" / "plugin.json"
    manifest.parent.mkdir(parents=True)
    _ = manifest.write_text('{\n  "name": "demo",\n  "version": "0.1.0"\n}\n', encoding="utf-8")
    skill = root / "plugins" / PLUGIN / "skills" / PLUGIN / "SKILL.md"
    skill.parent.mkdir(parents=True)
    _ = skill.write_text("# Demo\n", encoding="utf-8")
    _ = (root / "plugins" / PLUGIN / "README.md").write_text("# Demo\n", encoding="utf-8")
    for args in (
        ["init", "--quiet", "--initial-branch=main"],
        ["-c", "user.name=t", "-c", "user.email=t@t", "add", "--all"],
        ["-c", "user.name=t", "-c", "user.email=t@t", "commit", "--quiet", "-m", "init"],
        ["tag", "demo--v0.1.0"],
    ):
        _ = git_output(root, args)
    return root


@pytest.mark.slow
@pytest.mark.parametrize("binary", BASH_BINARIES)
@pytest.mark.parametrize(
    ("name", "content"),
    [
        ("hook.sh", MISFORMATTED_SHELL),
        ("probe.py", MISFORMATTED_PYTHON),
        ("data.json", NON_CANONICAL_JSON),
    ],
)
def test_an_edit_is_never_rewritten_or_blocked(
    tmp_path: Path, hooks: Path, binary: str, name: str, content: str
) -> None:
    """Formatting and linting moved to the commit guard; the hook must not do either.

    Args:
        tmp_path: pytest's scratch directory, used as the project.
        hooks: The repository's `.claude/hooks` directory.
        binary: The bash under test.
        name: The file the edit touched.
        content: A body every retired writer would have changed or refused.
    """
    target = tmp_path / name
    _ = target.write_text(content, encoding="utf-8")
    completed = run_hook(
        hooks / HOOK,
        _edit(target, tmp_path, "s1"),
        binary=binary,
        cwd=tmp_path,
        env=_env(tmp_path),
    )
    assert completed.returncode == int(ExitCode.OK)
    assert completed.stdout == ""
    assert target.read_text(encoding="utf-8") == content


@pytest.mark.slow
@pytest.mark.parametrize("binary", BASH_BINARIES)
def test_a_runtime_edit_reminds_once_per_session(
    plugin_repo: Path, hooks: Path, binary: str
) -> None:
    """The reminder is the hook's one job: say it once, then stay quiet in that session.

    Args:
        plugin_repo: A checkout with the tagged `demo` plugin.
        hooks: The repository's `.claude/hooks` directory.
        binary: The bash under test.
    """
    skill = plugin_repo / "plugins" / PLUGIN / "skills" / PLUGIN / "SKILL.md"
    _ = skill.write_text("# Demo\n\nChanged.\n", encoding="utf-8")

    def run(session: str) -> str:
        return _context(
            run_hook(
                hooks / HOOK,
                _edit(skill, plugin_repo, session),
                binary=binary,
                cwd=plugin_repo,
                env=_env(plugin_repo),
            ).stdout
        )

    first = run("session-a")
    assert REMINDER in first
    assert "skills/demo/SKILL.md" in first
    assert run("session-a") == ""
    assert REMINDER in run("session-b")


@pytest.mark.slow
@pytest.mark.parametrize("binary", BASH_BINARIES)
def test_an_exempt_edit_does_not_remind(plugin_repo: Path, hooks: Path, binary: str) -> None:
    """A README change needs no bump, so a reminder there would teach the wrong rule.

    Args:
        plugin_repo: A checkout with the tagged `demo` plugin.
        hooks: The repository's `.claude/hooks` directory.
        binary: The bash under test.
    """
    readme = plugin_repo / "plugins" / PLUGIN / "README.md"
    _ = readme.write_text("# Demo\n\nMore words.\n", encoding="utf-8")
    completed = run_hook(
        hooks / HOOK,
        _edit(readme, plugin_repo, "session-c"),
        binary=binary,
        cwd=plugin_repo,
        env=_env(plugin_repo),
    )
    assert completed.stdout == ""


@pytest.mark.slow
@pytest.mark.parametrize("binary", BASH_BINARIES)
def test_a_file_outside_the_tree_is_skipped(tmp_path: Path, hooks: Path, binary: str) -> None:
    """A file outside the project is never the project's plugin, so nothing is said.

    Args:
        tmp_path: pytest's scratch directory.
        hooks: The repository's `.claude/hooks` directory.
        binary: The bash under test.
    """
    outside = tmp_path / "outside" / "hook.sh"
    outside.parent.mkdir()
    _ = outside.write_text(MISFORMATTED_SHELL, encoding="utf-8")
    inside = tmp_path / "inside"
    inside.mkdir()
    completed = run_hook(
        hooks / HOOK,
        _edit(outside, inside, "s2"),
        binary=binary,
        cwd=inside,
        env=_env(inside),
    )
    assert completed.stdout == ""
    assert outside.read_text(encoding="utf-8") == MISFORMATTED_SHELL


def test_the_hook_calls_no_lint_format_or_type_tool(hooks: Path) -> None:
    """Pins the decision: re-adding a writer or checker here must fail a test first.

    Args:
        hooks: The repository's `.claude/hooks` directory.
    """
    text = (hooks / HOOK).read_text(encoding="utf-8")
    for term in RETIRED_TERMS:
        assert term not in text, term
