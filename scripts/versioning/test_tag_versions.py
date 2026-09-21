"""Tests for the tagging entrypoint, with the official CLI stubbed through `CLAUDE_BIN`."""

from __future__ import annotations

import stat
from typing import TYPE_CHECKING, Final

import pytest

from scripts.common.errors import ExecutableNotFoundError, ExitCode
from scripts.versioning.conftest import manifest_text, write_file
from scripts.versioning.tag_versions import (
    CLAUDE_BIN_ENV,
    NOTHING_PENDING,
    claude_executable,
    main,
    manifest_version,
    pending_tags,
    run_claude_tag,
)

if TYPE_CHECKING:
    from pathlib import Path

ARGV_LOG: Final = "argv.log"
"""Where the stub records how it was invoked."""


def _stub(tmp_path: Path, *, exit_code: int) -> Path:
    """Write a stand-in for `claude` that records its arguments.

    Args:
        tmp_path: The directory to write into.
        exit_code: The status the stub exits with.

    Returns:
        The stub's path.
    """
    stub = tmp_path / "claude-stub"
    write_file(
        stub,
        "#!/usr/bin/env bash\n"
        f'printf "%s\\n" "$*" >> "{tmp_path / ARGV_LOG}"\n'
        'echo "stub said something"\n'
        f"exit {exit_code}\n",
    )
    stub.chmod(stub.stat().st_mode | stat.S_IXUSR)
    return stub


def _bump_alpha(repo: Path, version: str) -> None:
    """Raise alpha's manifest version without tagging it.

    Args:
        repo: The repository root.
        version: The new version.
    """
    write_file(repo / "plugins/alpha/.claude-plugin/plugin.json", manifest_text("alpha", version))


def test_claude_executable_prefers_the_override(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The tests never run the real CLI; the override is how they stay hermetic."""
    monkeypatch.setenv(CLAUDE_BIN_ENV, str(tmp_path / "claude-stub"))
    assert claude_executable() == str(tmp_path / "claude-stub")


def test_claude_executable_reports_a_missing_cli(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A missing CLI says what to install rather than failing inside a subprocess call."""
    monkeypatch.delenv(CLAUDE_BIN_ENV, raising=False)
    monkeypatch.setenv("PATH", str(tmp_path))
    with pytest.raises(ExecutableNotFoundError, match="`claude` is not on PATH"):
        _ = claude_executable()


@pytest.mark.slow
def test_manifest_version_reads_the_declared_version(repo: Path) -> None:
    """The tag name is built from the manifest, never from the catalog."""
    assert manifest_version(repo, "alpha") == "0.1.0"


@pytest.mark.slow
def test_nothing_is_pending_when_every_version_is_tagged(repo: Path) -> None:
    """The workflow is idempotent: a second run has nothing left to do."""
    assert pending_tags(repo) == []


@pytest.mark.slow
def test_a_bumped_version_is_pending(repo: Path) -> None:
    """A version without its tag is exactly what the tagging workflow exists for."""
    _bump_alpha(repo, "0.1.1")
    assert pending_tags(repo) == [("alpha", "0.1.1")]


@pytest.mark.slow
def test_main_says_so_when_nothing_is_pending(
    repo: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The line the gate evidence pins."""
    monkeypatch.chdir(repo)
    assert main(["--dry-run"]) == 0
    assert capsys.readouterr().out.strip() == NOTHING_PENDING


@pytest.mark.slow
def test_dry_run_reports_the_tag_without_creating_it(
    repo: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`--dry-run` must never leave a tag behind; the ruleset makes tags immutable."""
    _bump_alpha(repo, "0.1.1")
    monkeypatch.setenv(CLAUDE_BIN_ENV, str(_stub(tmp_path, exit_code=0)))
    monkeypatch.chdir(repo)
    assert main(["--dry-run"]) == 0
    assert "alpha 0.1.1 would tag alpha--v0.1.1" in capsys.readouterr().out
    assert pending_tags(repo) == [("alpha", "0.1.1")]
    recorded = (tmp_path / ARGV_LOG).read_text(encoding="utf-8")
    assert recorded.strip() == "plugin tag plugins/alpha --dry-run"


@pytest.mark.slow
def test_a_refused_tag_fails_the_run(
    repo: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The CLI owns validation, so its refusal has to surface as a non-zero exit."""
    _bump_alpha(repo, "0.1.1")
    monkeypatch.setenv(CLAUDE_BIN_ENV, str(_stub(tmp_path, exit_code=3)))
    monkeypatch.chdir(repo)
    assert main(["--dry-run"]) == 1
    captured = capsys.readouterr()
    assert "refused alpha--v0.1.1" in captured.out
    assert "stub said something" in captured.err


@pytest.mark.slow
def test_dry_run_and_push_contradict_each_other(
    repo: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Asking to both not tag and push the tag is a usage error, not a silent choice."""
    monkeypatch.chdir(repo)
    assert main(["--dry-run", "--push"]) == int(ExitCode.USAGE)
    assert "contradict" in capsys.readouterr().err


@pytest.mark.slow
def test_run_claude_tag_passes_push_through(
    repo: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The workflow's invocation is `claude plugin tag <path> --push`."""
    _bump_alpha(repo, "0.1.1")
    monkeypatch.setenv(CLAUDE_BIN_ENV, str(_stub(tmp_path, exit_code=0)))
    result = run_claude_tag(repo, "alpha", extra=["--push"])
    assert result.tag == "alpha--v0.1.1"
    assert result.returncode == 0
    assert (tmp_path / ARGV_LOG).read_text(encoding="utf-8").strip() == (
        "plugin tag plugins/alpha --push"
    )
