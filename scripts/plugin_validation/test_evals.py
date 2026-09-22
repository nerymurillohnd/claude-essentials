"""E1 to E4: a suite that can measure something, and results that stay out of git."""

from __future__ import annotations

import shutil
from typing import TYPE_CHECKING

from scripts.common.plugins import plugin_ids, repo_root
from scripts.plugin_validation.conftest import PLUGIN_ID
from scripts.plugin_validation.evals import (
    MINIMUM_CASES,
    case_dirs,
    check_cases,
    check_readme,
    check_results_ignored,
    check_suite,
    collect,
    is_must_not_fire,
)

if TYPE_CHECKING:
    from pathlib import Path


def ids(findings: list[object]) -> list[str]:
    """Reduce findings to their invariant IDs.

    Args:
        findings: What a check returned.

    Returns:
        The IDs, in order.
    """
    return [getattr(finding, "invariant_id", "") for finding in findings]


def test_every_shipped_suite_passes() -> None:
    """E1 to E4 hold on this working tree, which is the claim the gate makes."""
    root = repo_root()
    assert [finding for plugin_id in plugin_ids(root) for finding in collect(root, plugin_id)] == []


def test_the_scratch_suite_passes(scratch: Path) -> None:
    """The fixture is the baseline the must-not-fire probe is measured against.

    Args:
        scratch: The scratch repository root.
    """
    assert collect(scratch, PLUGIN_ID) == []
    assert len(case_dirs(scratch, PLUGIN_ID)) == MINIMUM_CASES


def test_a_must_not_fire_grader_is_recognised(scratch: Path) -> None:
    """The three keys together are what makes a case measure silence.

    Args:
        scratch: The scratch repository root.
    """
    path = scratch / "plugins" / PLUGIN_ID / "evals" / "90-stays-quiet" / "graders" / "fired.md"
    assert is_must_not_fire(path)


def test_too_few_cases_is_reported(scratch: Path) -> None:
    """Below three cases a delta is noise, so E1 refuses the suite.

    Args:
        scratch: The scratch repository root.
    """
    shutil.rmtree(scratch / "plugins" / PLUGIN_ID / "evals" / "02-fires-again")
    assert "E1" in ids(list(check_suite(scratch, PLUGIN_ID)))


def test_a_case_without_a_prompt_is_reported(scratch: Path) -> None:
    """A case with no prompt cannot run at all.

    Args:
        scratch: The scratch repository root.
    """
    (scratch / "plugins" / PLUGIN_ID / "evals" / "01-fires" / "prompt.md").unlink()
    assert "E2" in ids(list(check_cases(scratch, PLUGIN_ID)))


def test_a_case_without_graders_is_reported(scratch: Path) -> None:
    """A case with no grader cannot fail, which is the vanity-suite defect.

    Args:
        scratch: The scratch repository root.
    """
    shutil.rmtree(scratch / "plugins" / PLUGIN_ID / "evals" / "01-fires" / "graders")
    assert "E2" in ids(list(check_cases(scratch, PLUGIN_ID)))


def test_results_must_be_ignored(scratch: Path) -> None:
    """Without the ignore rule, a run's output lands in the next commit.

    Args:
        scratch: The scratch repository root.
    """
    _ = (scratch / ".gitignore").write_text("nothing\n", encoding="utf-8")
    assert "E3" in ids(list(check_results_ignored(scratch, PLUGIN_ID)))


def test_the_ci_section_must_state_the_policy(scratch: Path) -> None:
    """A suite README that claims to gate a merge contradicts what CI does (D2).

    Args:
        scratch: The scratch repository root.
    """
    path = scratch / "plugins" / PLUGIN_ID / "evals" / "README.md"
    _ = path.write_text(f"# Evals — `{PLUGIN_ID}`\n\nNo policy here.\n", encoding="utf-8")
    assert "E4" in ids(list(check_readme(scratch, PLUGIN_ID)))
