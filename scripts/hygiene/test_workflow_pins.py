"""G2 on the real tree: every action this repository runs is pinned to a commit.

A `uses:` that names a tag or a branch runs whatever that ref points at on the day the
workflow fires. The ref is controlled by the action's author, not by this repository, so a
compromised or simply changed action runs with this repository's token and nothing here
records that anything moved. DEBT-0004 is the entry for the time that was true here.

The tag stays, in a `# vX.Y.Z` comment: without it the SHA is unreadable and nobody can tell
whether a Dependabot bump is a patch or a major. The module that implements this is shared
with `make validate`; what this adds is that it is asserted against the workflows actually in
the tree, every time the suite runs.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from scripts.common.errors import format_finding
from scripts.github.repo_metadata import check_workflow_pins, workflow_paths

if TYPE_CHECKING:
    from pathlib import Path

WORKFLOW_DIR: Final = ".github/workflows"
"""Where the workflows live."""


def test_this_repository_has_workflows_to_check(repo: Path) -> None:
    """A rule over an empty directory passes for free and says nothing."""
    assert workflow_paths(repo)


def test_every_action_reference_is_a_pinned_commit(repo: Path) -> None:
    """A floating ref runs code this repository never reviewed, with this repository's token."""
    findings = check_workflow_pins(repo)
    assert [format_finding(finding) for finding in findings] == []


def test_the_pin_check_reads_every_workflow(repo: Path) -> None:
    """A path filter that missed a file would leave one workflow unpinned and unreported."""
    listed = {path.name for path in workflow_paths(repo)}
    on_disk = {path.name for path in (repo / WORKFLOW_DIR).glob("*.yml")}
    assert listed == on_disk
