"""Tests for the locked-binary helpers: resolution fails closed, PATH is the project's."""

from __future__ import annotations

import os
import re
from typing import TYPE_CHECKING

import pytest

from scripts.common.errors import ExecutableNotFoundError
from scripts.lint.tools import CHUNK, VENV_BIN, chunks, run, tool_path, venv_env

if TYPE_CHECKING:
    from pathlib import Path


def test_a_locked_binary_resolves_inside_the_project_environment(tree: Path) -> None:
    """The gate, the hooks and the editor all have to run the same file."""
    assert tool_path(tree, "shellcheck") == tree / VENV_BIN / "shellcheck"


def test_a_missing_binary_names_the_path_and_the_fix(tmp_path: Path) -> None:
    """A tree without `.venv` fails closed and says `make setup`, never skips the check."""
    with pytest.raises(ExecutableNotFoundError, match=re.escape("make setup")):
        _ = tool_path(tmp_path, "shellcheck")


def test_the_path_the_tools_see_starts_with_the_project_environment(tmp_path: Path) -> None:
    """Basedpyright resolves imports from the first interpreter on PATH."""
    environment = venv_env(tmp_path)
    assert environment["PATH"].startswith(str(tmp_path / VENV_BIN))
    assert os.environ["PATH"] in environment["PATH"]


def test_a_long_file_list_is_split_into_runnable_command_lines() -> None:
    """A repository-wide run must not depend on the shell's argument limit."""
    paths = [f"f{index}.sh" for index in range(CHUNK * 2 + 1)]
    batches = chunks(paths)
    assert [len(batch) for batch in batches] == [CHUNK, CHUNK, 1]
    assert [rel for batch in batches for rel in batch] == paths


def test_an_empty_file_list_runs_nothing() -> None:
    """No candidate means no process spawn, which is what keeps the commit guard fast."""
    assert chunks([]) == []


@pytest.mark.slow
def test_a_non_zero_exit_is_an_answer_rather_than_an_exception(tree: Path) -> None:
    """A linter exits non-zero exactly when it has something to say."""
    bad = tree / "bad.sh"
    _ = bad.write_text("#!/usr/bin/env bash\nrm -rf $1\n", encoding="utf-8")
    completed = run(tool_path(tree, "shellcheck"), ["-f", "gcc", "bad.sh"], cwd=tree)
    assert completed.returncode != 0
    assert "SC2086" in completed.stdout
