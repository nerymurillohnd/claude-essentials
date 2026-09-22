"""P7: the index in `CLAUDE.md` lists exactly what the harness ships, both ways.

This is the check the index rule exists for. An entry that names a file nobody ships sends
Claude to read something that is not there; a file the index never names is one Claude never
learns about, so it might as well not be in the repository.

It cannot run yet: the index tables arrive with the instruction files at step 10 of the
python-toolchain-and-governance migration, and until then `CLAUDE.md` carries prose only, so
the comparison would be between an empty index and a full disk. The skip is deliberate, is
the only one in this suite, and is removed by that step.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from scripts.harness.inventory import agent_files, index_entries, rule_paths

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.skip(reason="enabled at step 10 when the index tables exist")
def test_the_index_and_the_harness_on_disk_match_both_ways(repo: Path) -> None:
    """An index entry with no file, or a file with no entry, is a harness nobody can trust."""
    listed = {entry.name.strip("`") for entry in index_entries(repo)}
    shipped = {rel.rsplit("/", 1)[-1] for rel in (*rule_paths(repo), *agent_files(repo))}
    assert listed >= shipped, f"not in the index: {sorted(shipped - listed)}"
    assert listed <= shipped, f"indexed but not shipped: {sorted(listed - shipped)}"
