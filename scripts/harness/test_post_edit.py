"""Tests for the post-edit writer: both branches.

An edit that leaves a file unformatted or unsound reaches the gate minutes later, in a
`make check` run whose output is about something else. Repairing it on the spot, and blocking
on what no writer can repair, is what keeps the feedback next to the edit.

The hook has two branches and they are tested differently. The **shell** branch calls shfmt
and ShellCheck directly, so its cases run in a temporary directory. The **text** branch calls
`make -s fix-file`, which needs the `Makefile` and the project environment, so its cases run
against this checkout with scratch files that the fixtures remove: one `.py` under `scripts/`,
and one gitignored file per other kind under `.claude/.cache/hooks/`.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Final

import pytest

from scripts.common.errors import ExitCode
from scripts.common.jsontext import canonical_json
from scripts.harness.conftest import BASH_BINARIES, edit_payload, hook_output, run_hook

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from pathlib import Path

HOOK: Final = "post-edit.sh"
"""The hook under test."""

MISFORMATTED: Final = '#!/usr/bin/env bash\nif true; then\n        echo "over-indented"\nfi\n'
"""Indentation `.editorconfig` says is two spaces, so shfmt rewrites it."""

UNSOUND: Final = "#!/usr/bin/env bash\nset -euo pipefail\n\nrm -rf $1\n"
"""SC2086: a defect no formatter can absorb, so the hook has to block instead."""

CLEAN_MODULE: Final = "scripts/common/plugins.py"
"""A module the gate already accepts; editing it must not interrupt the turn."""

SCRATCH_MODULE: Final = "scripts/harness/_post_edit_probe.py"
"""Where the Python probe lives: under `scripts/`, which is the tree the type policy covers."""

SCRATCH_DIR: Final = ".claude/.cache/hooks"
"""A gitignored directory, so the other probes can never reach `git status`."""

UNFORMATTED_PYTHON: Final = '"""Probe."""\n\nimport os\nx   =  1\n'
"""An unused import and bad spacing: two defects Ruff's safe fixes both repair."""

BIOME_JSON: Final = '{"a":1,"b":[1,2]}\n'
"""JSON as the retired formatter wrote it: compact, arrays on one line."""

CONTROL_MARKDOWN: Final = "line\x07\n"
"""A literal control byte, which no writer may silently delete (L3)."""


def _env(repo: Path) -> dict[str, str]:
    """Run the hook with the locked binaries first on `PATH`.

    Args:
        repo: The checkout whose `.venv` holds them.

    Returns:
        This process's environment with `PATH` prefixed.
    """
    return {**os.environ, "PATH": f"{repo / '.venv' / 'bin'}{os.pathsep}{os.environ['PATH']}"}


def _block_reason(stdout: str) -> str:
    """Read the text a blocking `PostToolUse` hook showed Claude.

    Args:
        stdout: What the hook printed.

    Returns:
        The block's reason, or an empty string when it did not block.
    """
    if not stdout.strip():
        return ""
    text = hook_output(stdout).get("reason")
    return text if isinstance(text, str) else ""


@pytest.mark.slow
@pytest.mark.parametrize("binary", BASH_BINARIES)
def test_an_edited_shell_script_is_formatted_in_place(
    tmp_path: Path, repo: Path, hooks: Path, binary: str
) -> None:
    """Formatting next to the edit is what keeps it out of an unrelated gate run later."""
    script = tmp_path / "hook.sh"
    _ = script.write_text(MISFORMATTED, encoding="utf-8")
    completed = run_hook(
        hooks / HOOK,
        edit_payload(script, tmp_path),
        binary=binary,
        cwd=tmp_path,
        env=_env(repo),
    )
    assert completed.returncode == int(ExitCode.OK)
    assert script.read_text(encoding="utf-8") != MISFORMATTED
    assert "over-indented" in script.read_text(encoding="utf-8")


@pytest.mark.slow
@pytest.mark.parametrize("binary", BASH_BINARIES)
def test_a_shellcheck_finding_blocks(tmp_path: Path, repo: Path, hooks: Path, binary: str) -> None:
    """The hook refuses rather than silently accepting a defect a formatter cannot fix."""
    script = tmp_path / "hook.sh"
    _ = script.write_text(UNSOUND, encoding="utf-8")
    completed = run_hook(
        hooks / HOOK,
        edit_payload(script, tmp_path),
        binary=binary,
        cwd=tmp_path,
        env=_env(repo),
    )
    text = _block_reason(completed.stdout)
    assert "ShellCheck" in text
    assert "SC2086" in text


@pytest.mark.slow
@pytest.mark.parametrize("binary", BASH_BINARIES)
def test_a_clean_shell_script_produces_nothing(
    tmp_path: Path, repo: Path, hooks: Path, binary: str
) -> None:
    """The control: an edit that is already right must not interrupt the turn."""
    script = tmp_path / "hook.sh"
    _ = script.write_text('#!/usr/bin/env bash\nset -euo pipefail\n\necho "ok"\n', encoding="utf-8")
    completed = run_hook(
        hooks / HOOK,
        edit_payload(script, tmp_path),
        binary=binary,
        cwd=tmp_path,
        env=_env(repo),
    )
    assert completed.stdout == ""


@pytest.mark.slow
@pytest.mark.parametrize("binary", BASH_BINARIES)
def test_a_file_outside_the_tree_is_skipped(
    tmp_path: Path, repo: Path, hooks: Path, binary: str
) -> None:
    """A hook that formatted files outside the checkout would edit things nobody asked about."""
    outside = tmp_path / "outside" / "hook.sh"
    outside.parent.mkdir()
    _ = outside.write_text(MISFORMATTED, encoding="utf-8")
    inside = tmp_path / "inside"
    inside.mkdir()
    completed = run_hook(
        hooks / HOOK,
        edit_payload(outside, inside),
        binary=binary,
        cwd=inside,
        env=_env(repo),
    )
    assert completed.stdout == ""
    assert outside.read_text(encoding="utf-8") == MISFORMATTED


@pytest.fixture
def scratch_module(repo: Path) -> Iterator[Path]:
    """Put a defective Python module under `scripts/` and remove it afterwards.

    The Python branch only engages for a path under `scripts/`, which is what
    `[tool.basedpyright] include` covers, so this probe cannot live in a temporary directory.

    Args:
        repo: The repository root.

    Yields:
        The scratch module's path.
    """
    path = repo / SCRATCH_MODULE
    _ = path.write_text(UNFORMATTED_PYTHON, encoding="utf-8")
    try:
        yield path
    finally:
        path.unlink(missing_ok=True)


@pytest.fixture
def scratch_file(repo: Path) -> Iterator[Callable[[str, str], Path]]:
    """Write probes into the gitignored cache directory and remove them afterwards.

    Args:
        repo: The repository root.

    Yields:
        A factory taking a file name and its contents, returning the path.
    """
    written: list[Path] = []

    def make(name: str, text: str) -> Path:
        path = repo / SCRATCH_DIR / name
        path.parent.mkdir(parents=True, exist_ok=True)
        _ = path.write_text(text, encoding="utf-8")
        written.append(path)
        return path

    try:
        yield make
    finally:
        for path in written:
            path.unlink(missing_ok=True)


@pytest.mark.slow
@pytest.mark.parametrize("binary", BASH_BINARIES)
def test_an_edit_to_a_clean_module_does_not_block(repo: Path, hooks: Path, binary: str) -> None:
    """The control: the gate already accepts this file, so the turn must not be interrupted."""
    completed = run_hook(
        hooks / HOOK,
        edit_payload(repo / CLEAN_MODULE, repo),
        binary=binary,
        cwd=repo,
        env=_env(repo),
    )
    assert _block_reason(completed.stdout) == ""
    assert completed.returncode == int(ExitCode.OK)


@pytest.mark.slow
@pytest.mark.parametrize("binary", BASH_BINARIES)
def test_an_edited_module_is_fixed_in_place(
    repo: Path, hooks: Path, binary: str, scratch_module: Path
) -> None:
    """Ruff's safe fixes converge in one pass, so the hook repairs rather than reports."""
    completed = run_hook(
        hooks / HOOK,
        edit_payload(scratch_module, repo),
        binary=binary,
        cwd=repo,
        env=_env(repo),
    )
    assert _block_reason(completed.stdout) == ""
    assert scratch_module.read_text(encoding="utf-8") == '"""Probe."""\n\nx = 1\n'


@pytest.mark.slow
@pytest.mark.parametrize("binary", BASH_BINARIES)
def test_an_edited_json_file_is_rewritten_canonical(
    repo: Path, hooks: Path, binary: str, scratch_file: Callable[[str, str], Path]
) -> None:
    """The defect that made this branch urgent: the retired formatter's JSON form."""
    path = scratch_file("_post_edit_probe.json", BIOME_JSON)
    completed = run_hook(
        hooks / HOOK, edit_payload(path, repo), binary=binary, cwd=repo, env=_env(repo)
    )
    assert _block_reason(completed.stdout) == ""
    assert path.read_text(encoding="utf-8") == canonical_json({"a": 1, "b": [1, 2]})


@pytest.mark.slow
@pytest.mark.parametrize("binary", BASH_BINARIES)
def test_a_control_character_blocks_rather_than_being_deleted(
    repo: Path, hooks: Path, binary: str, scratch_file: Callable[[str, str], Path]
) -> None:
    """Deleting the byte would destroy content, so the hook reports and refuses instead."""
    path = scratch_file("_post_edit_probe.md", CONTROL_MARKDOWN)
    completed = run_hook(
        hooks / HOOK, edit_payload(path, repo), binary=binary, cwd=repo, env=_env(repo)
    )
    text = _block_reason(completed.stdout)
    assert "make fix-file" in text
    assert "U+0007" in text
    assert path.read_text(encoding="utf-8") == CONTROL_MARKDOWN


@pytest.mark.slow
@pytest.mark.parametrize("binary", BASH_BINARIES)
def test_a_missing_project_environment_advises_rather_than_blocks(
    tmp_path: Path, hooks: Path, binary: str
) -> None:
    """The edit itself is fine; what the maintainer needs is `make setup`, not a refusal."""
    probe = tmp_path / "notes.md"
    _ = probe.write_text("# notes\n", encoding="utf-8")
    completed = run_hook(hooks / HOOK, edit_payload(probe, tmp_path), binary=binary, cwd=tmp_path)
    assert _block_reason(completed.stdout) == ""
    assert "make setup" in completed.stdout


def test_the_hook_names_no_retired_tooling(hooks: Path) -> None:
    """A hook that still reached for Biome would undo the canonical form after every edit."""
    text = (hooks / HOOK).read_text(encoding="utf-8")
    for term in ("biome", "Biome", "node_modules", "npm "):
        assert term not in text, term
