"""The repo-hygiene plugin's bundled Git corpus and its eval fixture stay internally consistent.

The plugin ships a reference corpus that its skills and agents route through: an index
(`git-command-map.md`), area files and one page per Git command. A link to a page that does not
exist sends Claude to nothing, and a command page without its official URL or safety class
breaks the read-versus-mutate contract the skills rely on. Its eval cases share one fixture
script, copied into each case directory because a case's `scaffold_script` names a file in
that directory; the copies must not drift.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Final

import pytest

from scripts.common.plugins import PLUGINS_DIRNAME, repo_root, working_files

if TYPE_CHECKING:
    from pathlib import Path

PLUGIN: Final = "repo-hygiene"
"""The plugin under test."""

MIN_SCAFFOLD_COPIES: Final = 4
"""Cases 01, 02, 03 and 05 build the fixture."""

MARKDOWN_LINK: Final = re.compile(r"\]\((?P<target>[^)\s]+)\)")
"""An inline Markdown link target."""

CODE: Final = re.compile(r"```.*?```|`[^`\n]*`", re.DOTALL)
"""Fenced blocks and inline code spans, which hold regexes and commands, not links."""

CORPUS_PATH: Final = re.compile(r"`(?P<name>(?:commands|areas|program)/[a-z0-9-]+\.md)`")
"""A corpus file named in backticks, relative to the plugin's `references/` directory."""


def _plugin_markdown(root: Path) -> list[str]:
    """List the plugin's Markdown files.

    Args:
        root: The repository root.

    Returns:
        Repository-relative paths.
    """
    return [
        rel
        for rel in working_files(root, f"{PLUGINS_DIRNAME}/{PLUGIN}/*")
        if rel.endswith(".md") and "/evals/" not in rel
    ]


def _references(root: Path) -> Path:
    """Return the plugin's shared references directory.

    Args:
        root: The repository root.

    Returns:
        The absolute path of `plugins/repo-hygiene/references`.
    """
    return root / PLUGINS_DIRNAME / PLUGIN / "references"


def test_the_plugin_ships_markdown() -> None:
    """The parametrized tests below have something to check."""
    assert _plugin_markdown(repo_root())


@pytest.mark.parametrize("rel", _plugin_markdown(repo_root()))
def test_relative_links_resolve(rel: str) -> None:
    """Every relative Markdown link in the plugin points at an existing file.

    Args:
        rel: The Markdown file's repository-relative path.
    """
    root = repo_root()
    source = root / rel
    broken: list[str] = []
    prose = CODE.sub("", source.read_text(encoding="utf-8"))
    for match in MARKDOWN_LINK.finditer(prose):
        target = match["target"]
        if target.startswith(("http://", "https://", "mailto:", "#")):
            continue
        path = target.split("#", 1)[0]
        if path and not (source.parent / path).exists():
            broken.append(target)
    assert broken == [], f"{rel}: links to missing files: {broken}"


@pytest.mark.parametrize("rel", _plugin_markdown(repo_root()))
def test_named_corpus_files_exist(rel: str) -> None:
    """A corpus file named in backticks exists under `references/`.

    Args:
        rel: The Markdown file's repository-relative path.
    """
    root = repo_root()
    text = (root / rel).read_text(encoding="utf-8")
    missing = sorted(
        {
            match["name"]
            for match in CORPUS_PATH.finditer(text)
            if not (_references(root) / match["name"]).is_file()
        }
    )
    assert missing == [], f"{rel}: names corpus files that do not exist: {missing}"


def _command_pages(root: Path) -> list[str]:
    """List the corpus's command pages.

    Args:
        root: The repository root.

    Returns:
        Repository-relative paths.
    """
    return working_files(root, f"{PLUGINS_DIRNAME}/{PLUGIN}/references/commands/*.md")


def test_the_corpus_has_command_pages() -> None:
    """The parametrized test below has something to check."""
    assert _command_pages(repo_root())


@pytest.mark.parametrize("rel", _command_pages(repo_root()))
def test_a_command_page_states_its_source_and_safety_class(rel: str) -> None:
    """A command page names its official URL and classifies what is safe to run.

    Args:
        rel: The command page's repository-relative path.
    """
    text = (repo_root() / rel).read_text(encoding="utf-8")
    assert re.search(r"^Official: <?https://", text, re.MULTILINE), f"{rel}: no Official URL"
    assert "\n## Safety class\n" in text, f"{rel}: no Safety class section"


def _area_files(root: Path) -> list[str]:
    """List the corpus's area files.

    Args:
        root: The repository root.

    Returns:
        Repository-relative paths.
    """
    return working_files(root, f"{PLUGINS_DIRNAME}/{PLUGIN}/references/areas/*.md")


def test_the_corpus_has_area_files() -> None:
    """The parametrized test below has something to check."""
    assert _area_files(repo_root())


@pytest.mark.parametrize("rel", _area_files(repo_root()))
def test_an_area_file_has_both_depths(rel: str) -> None:
    """Each area gives the routine checks and the deep checks the two skills rely on.

    Args:
        rel: The area file's repository-relative path.
    """
    text = (repo_root() / rel).read_text(encoding="utf-8")
    for heading in ("## Routine checks", "## Deep checks", "## Recommendations and recovery"):
        assert f"\n{heading}" in text, f"{rel}: missing {heading!r}"


def test_eval_scaffold_copies_are_identical() -> None:
    """Every case that builds the fixture builds the same one."""
    root = repo_root()
    copies = working_files(root, f"{PLUGINS_DIRNAME}/{PLUGIN}/evals/*/scaffold.sh")
    assert len(copies) >= MIN_SCAFFOLD_COPIES, f"expected the fixture in each case: {copies}"
    contents = {(root / rel).read_bytes() for rel in copies}
    assert len(contents) == 1, f"the fixture copies differ: {copies}"
