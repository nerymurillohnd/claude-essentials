"""Tests for L1: discovery by name or shebang, then the real ShellCheck and shfmt."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from scripts.lint.conftest import write_file
from scripts.lint.shell_files import INVARIANT, check, fix, is_shell_file, select

if TYPE_CHECKING:
    from pathlib import Path

CLEAN = '#!/usr/bin/env bash\nset -euo pipefail\n\necho "ok"\n'
"""A script both tools accept, used as the control in every comparison."""

UNQUOTED = '#!/usr/bin/env bash\nset -euo pipefail\n\nname="$1"\nrm -rf $name\n'
"""SC2086: an unquoted expansion, the defect ShellCheck exists to catch."""

MISFORMATTED = '#!/usr/bin/env bash\nif true; then\n        echo "over-indented"\nfi\n'
"""Indentation `.editorconfig` says is two spaces, so shfmt would rewrite it."""


def test_a_dot_sh_file_is_shell_without_being_read(tree: Path) -> None:
    """The extension decides on its own, so an empty `.sh` file is still checked."""
    write_file(tree / "empty.sh", "")
    assert is_shell_file(tree, "empty.sh")


@pytest.mark.parametrize("shebang", ["#!/usr/bin/env bash", "#!/bin/sh", "#!/usr/bin/env sh"])
def test_a_shebang_makes_a_file_shell_without_an_extension(tree: Path, shebang: str) -> None:
    """A hook installed without an extension is still a hook."""
    write_file(tree / "handler", f"{shebang}\necho hi\n")
    assert is_shell_file(tree, "handler")


def test_another_interpreter_is_not_shell(tree: Path) -> None:
    """Python and JavaScript belong to other gates; misclassifying them would be noise."""
    write_file(tree / "tool", "#!/usr/bin/env python3\nprint('hi')\n")
    assert not is_shell_file(tree, "tool")


def test_a_missing_file_is_not_shell(tree: Path) -> None:
    """A path that vanished between listing and reading is skipped, never an exception."""
    assert not is_shell_file(tree, "gone")


def test_select_keeps_only_the_shell_scripts(tree: Path) -> None:
    """Every checker filters the one candidate list the entrypoint built."""
    write_file(tree / "a.sh", CLEAN)
    write_file(tree / "b.json", "{}\n")
    assert select(tree, ["a.sh", "b.json"]) == ["a.sh"]


@pytest.mark.slow
def test_a_clean_script_passes_both_tools(tree: Path) -> None:
    """The control: nothing is reported for a script that is already right."""
    write_file(tree / "clean.sh", CLEAN)
    assert check(tree, ["clean.sh"]) == []


@pytest.mark.slow
def test_shellcheck_reports_an_unquoted_expansion(tree: Path) -> None:
    """The finding names the file and the line, so the maintainer never has to re-run."""
    write_file(tree / "bad.sh", UNQUOTED)
    findings = check(tree, ["bad.sh"])
    assert [finding.invariant_id for finding in findings] == [INVARIANT] * len(findings)
    assert any("SC2086" in finding.message for finding in findings)
    assert all(finding.path == "bad.sh" for finding in findings)


@pytest.mark.slow
def test_shfmt_reports_a_file_it_would_rewrite(tree: Path) -> None:
    """Formatting is a gate, not a suggestion, so a divergent file fails the build."""
    write_file(tree / "ugly.sh", MISFORMATTED)
    findings = check(tree, ["ugly.sh"])
    assert any("shfmt would reformat it" in finding.message for finding in findings)


@pytest.mark.slow
def test_fix_rewrites_the_file_and_names_it(tree: Path) -> None:
    """`make fix` is the writer; after it, `make lint` has nothing left to say."""
    path = tree / "ugly.sh"
    write_file(path, MISFORMATTED)
    assert fix(tree, ["ugly.sh"]) == ["ugly.sh"]
    assert path.read_text(encoding="utf-8") != MISFORMATTED
    assert check(tree, ["ugly.sh"]) == []


@pytest.mark.slow
def test_a_dry_run_reports_without_writing(tree: Path) -> None:
    """`--fix --dry-run` is what a maintainer runs before letting a writer loose."""
    path = tree / "ugly.sh"
    write_file(path, MISFORMATTED)
    assert fix(tree, ["ugly.sh"], dry_run=True) == ["ugly.sh"]
    assert path.read_text(encoding="utf-8") == MISFORMATTED


@pytest.mark.slow
def test_nothing_runs_when_no_candidate_is_shell(tree: Path) -> None:
    """A JSON-only edit must not pay for two process spawns."""
    write_file(tree / "b.json", "{}\n")
    assert check(tree, ["b.json"]) == []
    assert fix(tree, ["b.json"]) == []
