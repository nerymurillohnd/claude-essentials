"""Where the tooling is running: a maintainer's machine, or a GitHub Actions runner.

Three places need the answer and must agree: `workflows_files` decides whether zizmor may
reach the network, `test_rigor_floor` skips the comparison against `~/.config` when the
global policy files are not there, and CI-only output formats hang off the same question.

**`GITHUB_ACTIONS` alone is not a reliable answer** (measured 2026-09-21): this repository's
maintainer exports `GITHUB_ACTIONS=true` from `~/.zshenv`, so every local shell claims to be
a runner. Reading it alone would silently skip the rigor floor on the one machine that check
exists for. A real runner also sets the run's own identifiers, which no shell profile has a
reason to invent, so both must hold.
"""

from __future__ import annotations

import os
from typing import Final

ACTIONS_FLAG: Final = "GITHUB_ACTIONS"
"""The variable every Actions runner sets, and that a shell profile may also set."""

RUN_MARKERS: Final[tuple[str, ...]] = ("GITHUB_RUN_ID", "GITHUB_WORKFLOW", "GITHUB_EVENT_NAME")
"""Identifiers only an actual workflow run has; any one of them confirms the flag."""


def in_github_actions() -> bool:
    """Report whether this process is running inside a GitHub Actions job.

    Returns:
        True only when the flag is set to `true` and at least one run identifier is present.
    """
    if os.environ.get(ACTIONS_FLAG) != "true":
        return False
    return any(os.environ.get(name) for name in RUN_MARKERS)
