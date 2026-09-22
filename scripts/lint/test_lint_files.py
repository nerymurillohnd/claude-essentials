"""Tests for the lint entrypoint: the registry, the three file sets, and the writer."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from scripts.common.errors import ExitCode, MissingPathError
from scripts.lint.conftest import git_in, write_file
from scripts.lint.lint_files import (
    LINT_INVARIANTS,
    all_paths,
    apply_fixes,
    changed_paths,
    collect,
    fix_python,
    main,
    python_paths,
    registry_lines,
    select_paths,
)

if TYPE_CHECKING:
    from pathlib import Path

    from _pytest.capture import CaptureFixture

COMPACT = '{"a":1}\n'
"""A JSON document that is not in the canonical form."""


def test_every_invariant_has_an_id_a_check_and_a_defect() -> None:
    """P14: a check exists only with the defect it catches recorded next to it."""
    assert len(LINT_INVARIANTS) == len(registry_lines())
    assert [ident for ident, _, _ in LINT_INVARIANTS] == ["L1", "L2", "L3", "L4", "L5", "L6"]
    assert all(check and defect for _, check, defect in LINT_INVARIANTS)


def test_list_prints_the_registry_and_checks_nothing(capsys: CaptureFixture[str]) -> None:
    """`--list` is how a maintainer looks an ID up from gate output alone."""
    assert main(["--list"]) == int(ExitCode.OK)
    printed = capsys.readouterr().out.splitlines()
    assert [line.split(maxsplit=1)[0] for line in printed] == ["L1", "L2", "L3", "L4", "L5", "L6"]


def test_python_paths_keeps_only_the_maintainer_python() -> None:
    """L6 can only answer for the tree `[tool.basedpyright] include` covers."""
    assert python_paths(["scripts/lint/a.py", "plugins/x/b.py", "scripts/c.md"]) == [
        "scripts/lint/a.py"
    ]


@pytest.mark.slow
def test_the_default_set_is_every_tracked_or_new_file(git_tree: Path) -> None:
    """`make lint` answers for the whole tree, not only for what changed."""
    write_file(git_tree / "new.json", COMPACT)
    assert "new.json" in all_paths(git_tree)
    assert ".editorconfig" in all_paths(git_tree)


@pytest.mark.slow
def test_the_staged_set_is_what_a_commit_could_include(git_tree: Path) -> None:
    """A chained `git add … && git commit` has staged nothing yet when the guard runs."""
    write_file(git_tree / "untracked.json", COMPACT)
    write_file(git_tree / ".editorconfig", "root = true\n")
    assert set(changed_paths(git_tree)) == {"untracked.json", ".editorconfig"}


@pytest.mark.slow
def test_the_staged_set_includes_an_already_staged_file(git_tree: Path) -> None:
    """Staged, modified and untracked are three ways into the same commit."""
    write_file(git_tree / "staged.json", COMPACT)
    _ = git_in(git_tree, "add", "staged.json")
    assert "staged.json" in changed_paths(git_tree)


@pytest.mark.slow
def test_a_single_file_is_the_hook_s_file_set(git_tree: Path) -> None:
    """`make fix-file FILE=…` is what the `PostToolUse` hook runs after every edit."""
    write_file(git_tree / "one.json", COMPACT)
    assert select_paths(git_tree, staged=False, single="one.json") == ["one.json"]
    assert select_paths(git_tree, staged=False, single=str(git_tree / "one.json")) == ["one.json"]


@pytest.mark.slow
def test_a_single_file_that_is_not_there_is_a_usage_error(git_tree: Path) -> None:
    """A hook pointed at a deleted path must say so rather than check the whole tree."""
    with pytest.raises(MissingPathError):
        _ = select_paths(git_tree, staged=False, single="gone.json")


@pytest.mark.slow
def test_collect_reports_the_seeded_defect_with_its_id(git_tree: Path) -> None:
    """Every message starts with an ID, so gate output is looked up, not guessed at."""
    write_file(git_tree / "bad.json", COMPACT)
    findings = collect(git_tree, ["bad.json"])
    assert [(finding.invariant_id, finding.path) for finding in findings] == [("L2", "bad.json")]


@pytest.mark.slow
def test_the_writer_is_idempotent(git_tree: Path) -> None:
    """`make fix && make lint` has to converge, or the gate would never be green twice."""
    write_file(git_tree / "bad.json", COMPACT)
    write_file(git_tree / "ugly.sh", '#!/usr/bin/env bash\nif true; then\n        echo "x"\nfi\n')
    paths = ["bad.json", "ugly.sh"]
    assert apply_fixes(git_tree, paths) == paths
    assert apply_fixes(git_tree, paths) == []
    assert collect(git_tree, paths) == []


@pytest.mark.slow
def test_a_dry_run_changes_nothing(git_tree: Path) -> None:
    """The canonical-JSON churn is measured before it becomes a commit."""
    write_file(git_tree / "bad.json", COMPACT)
    assert apply_fixes(git_tree, ["bad.json"], dry_run=True) == ["bad.json"]
    assert (git_tree / "bad.json").read_text(encoding="utf-8") == COMPACT


@pytest.mark.slow
def test_the_entrypoint_fails_on_a_finding(git_tree: Path, capsys: CaptureFixture[str]) -> None:
    """Exit 1 is what makes `make lint` a gate rather than a report."""
    write_file(git_tree / "bad.json", COMPACT)
    assert main(["--root", str(git_tree)]) == int(ExitCode.FINDINGS)
    assert "L2 bad.json" in capsys.readouterr().out


@pytest.mark.slow
def test_the_entrypoint_passes_on_a_clean_tree(git_tree: Path, capsys: CaptureFixture[str]) -> None:
    """The control, and the line a maintainer reads when nothing is wrong."""
    assert main(["--root", str(git_tree)]) == int(ExitCode.OK)
    assert "every file passes" in capsys.readouterr().out


@pytest.mark.slow
def test_an_unusable_root_is_a_usage_error(tmp_path: Path, capsys: CaptureFixture[str]) -> None:
    """One `error:` line, never a traceback, is the entrypoint convention."""
    assert main(["--root", str(tmp_path / "absent")]) == int(ExitCode.USAGE)
    assert capsys.readouterr().err.startswith("error: ")


@pytest.mark.slow
def test_the_python_writers_converge_in_one_pass(git_tree: Path) -> None:
    """Removing an unused import leaves blank lines, so the formatter has to run after it."""
    write_file(git_tree / "scripts" / "probe.py", '"""Probe."""\n\nimport os\nx   =  1\n')
    assert fix_python(git_tree, ["scripts/probe.py"]) == ["scripts/probe.py"]
    assert (git_tree / "scripts" / "probe.py").read_text(encoding="utf-8") == (
        '"""Probe."""\n\nx = 1\n'
    )
    assert fix_python(git_tree, ["scripts/probe.py"]) == []


@pytest.mark.slow
def test_the_single_file_writer_reports_what_it_could_not_repair(
    git_tree: Path, capsys: CaptureFixture[str]
) -> None:
    """The `PostToolUse` hook blocks on this output, so it has to be an exit code too."""
    write_file(git_tree / "notes.md", "line\x07\n")
    assert main(["--root", str(git_tree), "--fix", "--file", "notes.md"]) == int(ExitCode.FINDINGS)
    assert "L3 notes.md" in capsys.readouterr().out


@pytest.mark.slow
def test_the_single_file_writer_is_silent_when_it_repaired_everything(git_tree: Path) -> None:
    """A repaired file must not interrupt the turn; only a leftover defect may."""
    write_file(git_tree / "one.json", COMPACT.replace("\n", ""))
    assert main(["--root", str(git_tree), "--fix", "--file", "one.json"]) == int(ExitCode.OK)


@pytest.mark.slow
def test_the_whole_tree_writer_stays_a_writer(git_tree: Path) -> None:
    """`make fix` is followed by `make lint` everywhere, so it reports nothing itself."""
    write_file(git_tree / "notes.md", "line\x07\n")
    assert main(["--root", str(git_tree), "--fix"]) == int(ExitCode.OK)
