"""`make validate-cli`: the entrypoint's exit codes and its one-line error."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from scripts.common.errors import ExitCode
from scripts.plugin_validation.validate_claude import main, parse_args

if TYPE_CHECKING:
    from pathlib import Path


def test_root_defaults_to_this_working_tree(tmp_path: Path) -> None:
    """With no `--root`, the gate checks the tree it is run in.

    Args:
        tmp_path: pytest's per-test directory.
    """
    assert parse_args([]) is None
    assert parse_args(["--root", str(tmp_path)]) == tmp_path


def test_a_missing_root_is_a_usage_error(capsys: pytest.CaptureFixture[str]) -> None:
    """Pointing the gate at a tree that is not there ends in one `error:` line.

    Args:
        capsys: pytest's output capture.
    """
    assert main(["--root", "/nonexistent-marketplace"]) == int(ExitCode.USAGE)
    assert capsys.readouterr().err.startswith("error: ")


@pytest.mark.slow
def test_the_gate_passes_on_this_tree(capsys: pytest.CaptureFixture[str]) -> None:
    """The official CLI accepts the marketplace and all five plugins today.

    Args:
        capsys: pytest's output capture.
    """
    status = main([])
    captured = capsys.readouterr().out
    if "is not on PATH" in capsys.readouterr().err:
        pytest.skip("the Claude Code CLI is not installed")
    assert status == int(ExitCode.OK), captured
    assert "FAIL" not in captured
