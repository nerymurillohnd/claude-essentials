"""Builders for the temporary repositories the versioning tests run against.

Every question this area answers depends on git: `git diff` against a base, `git ls-tree` at
a ref, `git tag --list`, `git show <tag>:<path>`. Stubbing git would test the stub, so the
tests build a real working tree with a real tag instead, and every test that does so carries
`@pytest.mark.slow`.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from typing import TYPE_CHECKING, Final

import pytest

if TYPE_CHECKING:
    from pathlib import Path

TODAY: Final = "2026-09-21"
"""The date the fixture CHANGELOGs are written with."""


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


def write_file(path: Path, text: str) -> None:
    """Create a file and every parent directory it needs.

    Args:
        path: The file to write.
        text: Its contents.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text(text, encoding="utf-8")


def manifest_text(name: str, version: str) -> str:
    """Render a plugin manifest.

    Args:
        name: The plugin id.
        version: The version to declare.

    Returns:
        The manifest as JSON text.
    """
    return (
        json.dumps(
            {
                "name": name,
                "version": version,
                "description": f"{name} for the route table",
                "author": {"name": "Test"},
                "license": "Apache-2.0",
            },
            indent=2,
        )
        + "\n"
    )


def changelog_text(name: str, version: str, *, deprecated: bool = False) -> str:
    """Render a plugin CHANGELOG with one released section.

    Args:
        name: The plugin id, used in the footer links.
        version: The released version.
        deprecated: Whether that release announces a deprecation.

    Returns:
        The CHANGELOG as Markdown.
    """
    if deprecated:
        block = "### Deprecated\n\n- Superseded; it will be removed.\n"
    else:
        block = "### Added\n\n- First release.\n"
    return (
        f"# Changelog\n\n"
        f"## [Unreleased]\n\n"
        f"## [{version}] - {TODAY}\n\n"
        f"{block}\n"
        f"[Unreleased]: https://example.test/compare/{name}--v{version}...HEAD\n"
        f"[{version}]: https://example.test/tree/{name}--v{version}\n"
    )


def make_plugin(root: Path, name: str, version: str) -> None:
    """Create a whole plugin directory: runtime files and exempt files alike.

    Args:
        root: The repository root.
        name: The plugin id.
        version: The version to declare.
    """
    base = root / "plugins" / name
    write_file(base / ".claude-plugin" / "plugin.json", manifest_text(name, version))
    write_file(base / "README.md", f"# {name}\n\n**Kind:** skill-only\n")
    write_file(base / "CHANGELOG.md", changelog_text(name, version))
    write_file(base / "LICENSE", "Apache-2.0\n")
    write_file(base / "skills" / "demo" / "SKILL.md", f"---\nname: {name}\n---\n\nDo the thing.\n")
    write_file(base / "docs" / "notes.md", "Notes.\n")
    write_file(base / "evals" / "cases" / "a.md", "A case.\n")
    write_file(base / "tests" / "run.sh", "#!/usr/bin/env bash\nexit 0\n")


def marketplace_text(renames: dict[str, str | None] | None = None) -> str:
    """Render the marketplace catalog.

    Args:
        renames: The `renames` map to include, or None to omit the key.

    Returns:
        The catalog as JSON text.
    """
    catalog: dict[str, object] = {"name": "test-market", "owner": {"name": "Test"}, "plugins": []}
    if renames is not None:
        catalog["renames"] = renames
    return json.dumps(catalog, indent=2) + "\n"


def commit_all(root: Path, message: str) -> str:
    """Stage everything and commit it.

    Args:
        root: The repository root.
        message: The commit message.

    Returns:
        The new commit's sha.
    """
    _ = git_in(root, "add", "--all")
    _ = git_in(
        root,
        "-c",
        "user.email=test@example.test",
        "-c",
        "user.name=Test",
        "commit",
        "--quiet",
        "--message",
        message,
    )
    return git_in(root, "rev-parse", "HEAD").strip()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """Build a repository with one released plugin, `alpha--v0.1.0`.

    Args:
        tmp_path: pytest's per-test temporary directory.

    Returns:
        The repository root, with `main` at the released state.
    """
    _ = git_in(tmp_path, "init", "--quiet", "--initial-branch=main")
    write_file(tmp_path / ".claude-plugin" / "marketplace.json", marketplace_text())
    write_file(tmp_path / "README.md", "# Test marketplace\n")
    make_plugin(tmp_path, "alpha", "0.1.0")
    _ = commit_all(tmp_path, "initial")
    _ = git_in(tmp_path, "tag", "alpha--v0.1.0")
    return tmp_path
