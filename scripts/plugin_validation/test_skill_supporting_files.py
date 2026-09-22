"""A skill's supporting files never carry `${CLAUDE_SKILL_DIR}`, which only SKILL.md gets filled in.

Claude Code substitutes the variable in a skill's own markdown and in its `allowed-tools`
rules, and nowhere else: a reference file opened with Read shows it literally, and a shell
expands it to nothing, so `python3 ${CLAUDE_SKILL_DIR}/scripts/x.py` becomes
`python3 /scripts/x.py`. Found in evidence-reader's references by its coherence audit,
2026-09-22.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

import pytest

from scripts.common.plugins import PLUGINS_DIRNAME, repo_root, working_files

if TYPE_CHECKING:
    from pathlib import Path

SKILL_DIR_VARIABLE: Final = "${CLAUDE_SKILL_DIR}"
"""The variable that resolves only inside SKILL.md."""


def _supporting_markdown(root: Path) -> list[str]:
    """List the markdown files a skill ships next to its SKILL.md.

    Args:
        root: The repository root.

    Returns:
        Repository-relative paths.
    """
    return [
        rel
        for rel in working_files(root, f"{PLUGINS_DIRNAME}/*/skills/**/*.md")
        if rel.endswith(".md") and not rel.endswith("/SKILL.md")
    ]


def test_the_plugins_ship_skill_supporting_files() -> None:
    """The parametrized test below has something to check."""
    assert _supporting_markdown(repo_root())


@pytest.mark.parametrize("rel", _supporting_markdown(repo_root()))
def test_a_supporting_file_does_not_use_the_skill_dir_variable(rel: str) -> None:
    """Name the script by file name and let SKILL.md say where it lives.

    Args:
        rel: The supporting file's repository-relative path.
    """
    text = (repo_root() / rel).read_text(encoding="utf-8")
    assert SKILL_DIR_VARIABLE not in text, (
        f"{rel} uses {SKILL_DIR_VARIABLE}, which only SKILL.md resolves"
    )
