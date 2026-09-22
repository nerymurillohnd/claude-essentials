"""A temporary tree that owns the same locked binaries and policy files as this repository.

The lint area is a set of wrappers around four real binaries, so stubbing them would test the
stub. Instead each fixture builds a directory that looks like a checkout from the tools' point
of view: a `.venv/bin` of symlinks to the binaries `uv.lock` installed, plus the
`.editorconfig` and `.shellcheckrc` that carry the policy. Defects are then seeded as real
files and the real tools answer.
"""

from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
from typing import Final

import pytest

from scripts.common.plugins import repo_root
from scripts.lint.tools import VENV_BIN

TOOLS: Final[tuple[str, ...]] = ("shellcheck", "shfmt", "actionlint", "zizmor", "ruff")
"""The binaries a fixture tree links, which is every tool this area shells out to."""

POLICY_FILES: Final[tuple[str, ...]] = (".editorconfig", ".shellcheckrc")
"""The configuration the tools read from the tree they run in."""

HERE: Final = Path(__file__).resolve().parent
"""This area's directory, so a fixture finds the real checkout without using the cwd."""


def write_file(path: Path, text: str) -> None:
    """Create a file and every parent directory it needs.

    Args:
        path: The file to write.
        text: Its contents.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text(text, encoding="utf-8")


@pytest.fixture
def tree(tmp_path: Path) -> Path:
    """Build a temporary tree the locked tools can run in.

    Args:
        tmp_path: pytest's per-test temporary directory.

    Returns:
        The tree's root, holding `.venv/bin` symlinks and the policy files.
    """
    source = repo_root(HERE)
    binaries = tmp_path / VENV_BIN
    binaries.mkdir(parents=True)
    for name in TOOLS:
        original = source / VENV_BIN / name
        if original.is_file():
            (binaries / name).symlink_to(original)
    for name in POLICY_FILES:
        write_file(tmp_path / name, (source / name).read_text(encoding="utf-8"))
    return tmp_path


def git_in(root: Path, *args: str) -> str:
    """Run git in a temporary repository.

    Args:
        root: The repository root.
        *args: The arguments after the binary.

    Returns:
        Standard output.
    """
    executable = shutil.which("git")
    assert executable is not None, "git must be on PATH for the maintainer test suite"
    completed = subprocess.run(
        ["/usr/bin/git", *args],
        executable=executable,
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout


@pytest.fixture
def git_tree(tree: Path) -> Path:
    """Turn the fixture tree into a git working tree with `.venv` ignored.

    The entrypoint asks git which files exist and which a commit could include, so its tests
    need a real index rather than a directory listing.

    Args:
        tree: The tree holding the locked binaries and the policy files.

    Returns:
        The same root, now a git repository with everything committed.
    """
    write_file(tree / ".gitignore", f"{VENV_BIN.parts[0]}/\n")
    _ = git_in(tree, "init", "--quiet", "--initial-branch=main")
    _ = git_in(tree, "add", "--all")
    _ = git_in(
        tree,
        "-c",
        "user.email=test@example.test",
        "-c",
        "user.name=Test",
        "commit",
        "--quiet",
        "--message",
        "initial",
    )
    return tree
