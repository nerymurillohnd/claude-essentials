"""Tests for repository access: git root, tracked files, plugin ids and JSON narrowing."""

from __future__ import annotations

import re
import shutil
import subprocess
from typing import TYPE_CHECKING

import pytest

from scripts.common.errors import (
    GitCommandFailedError,
    GitRevParseFailedError,
    MalformedJsonError,
    UnexpectedShapeError,
)
from scripts.common.plugins import (
    MANIFEST_RELATIVE_PATH,
    PLUGINS_DIRNAME,
    as_mapping,
    as_str,
    git_output,
    git_output_or_none,
    load_json,
    parse_json,
    plugin_ids,
    repo_root,
    tracked_files,
)

if TYPE_CHECKING:
    from pathlib import Path


def _write(path: Path, text: str) -> None:
    """Create a file and every parent directory it needs.

    Args:
        path: The file to write.
        text: Its contents.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text(text, encoding="utf-8")


def _make_plugin(root: Path, name: str) -> None:
    """Create a plugin directory complete with the manifest that makes it count.

    Args:
        root: The repository root.
        name: The plugin id, which is also its directory name.
    """
    _write(root / PLUGINS_DIRNAME / name / MANIFEST_RELATIVE_PATH, f'{{"name": "{name}"}}\n')


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    """Initialise a real git working tree with two plugins and one stray file.

    Args:
        tmp_path: pytest's per-test temporary directory.

    Returns:
        The repository root.
    """
    executable = shutil.which("git")
    assert executable is not None, "git must be on PATH for the maintainer test suite"
    _make_plugin(tmp_path, "alpha")
    _make_plugin(tmp_path, "beta")
    _write(tmp_path / PLUGINS_DIRNAME / "not-a-plugin" / "README.md", "no manifest here\n")
    _write(tmp_path / "README.md", "root\n")
    _ = subprocess.run(
        ["/usr/bin/git", "init", "--quiet", "--initial-branch=main"],
        executable=executable,
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )
    _ = subprocess.run(
        ["/usr/bin/git", "add", "--all"],
        executable=executable,
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )
    return tmp_path


@pytest.mark.slow
def test_repo_root_resolves_the_working_tree_from_a_subdirectory(git_repo: Path) -> None:
    """Every entrypoint can be run from anywhere inside the tree."""
    inside = git_repo / PLUGINS_DIRNAME / "alpha"
    assert repo_root(inside).resolve() == git_repo.resolve()


@pytest.mark.slow
def test_repo_root_outside_a_repository_names_the_command(tmp_path: Path) -> None:
    """The failure says which command failed, not just that something did."""
    with pytest.raises(GitRevParseFailedError, match=re.escape("git rev-parse --show-toplevel")):
        _ = repo_root(tmp_path)


@pytest.mark.slow
def test_tracked_files_lists_every_tracked_path_sorted(git_repo: Path) -> None:
    """With no pathspec the whole index comes back, in a stable order."""
    assert tracked_files(git_repo) == [
        "README.md",
        "plugins/alpha/.claude-plugin/plugin.json",
        "plugins/beta/.claude-plugin/plugin.json",
        "plugins/not-a-plugin/README.md",
    ]


@pytest.mark.slow
def test_tracked_files_pathspec_wildcard_crosses_directories(git_repo: Path) -> None:
    """`*` spans `/`, matching git's own default pathspec behaviour."""
    assert tracked_files(git_repo, "plugins/*/plugin.json") == [
        "plugins/alpha/.claude-plugin/plugin.json",
        "plugins/beta/.claude-plugin/plugin.json",
    ]


@pytest.mark.slow
def test_tracked_files_keeps_a_path_matching_any_pathspec(git_repo: Path) -> None:
    """Several pathspecs are a union, the way git treats them."""
    assert tracked_files(git_repo, "README.md", "plugins/not-a-plugin/*") == [
        "README.md",
        "plugins/not-a-plugin/README.md",
    ]


@pytest.mark.slow
def test_tracked_files_ignores_an_untracked_file(git_repo: Path) -> None:
    """The index is the source of truth, not the working tree."""
    _write(git_repo / "scratch.txt", "not added\n")
    assert "scratch.txt" not in tracked_files(git_repo)


def test_plugin_ids_needs_the_manifest(tmp_path: Path) -> None:
    """A directory under plugins/ is a plugin only when it ships its manifest."""
    _make_plugin(tmp_path, "beta")
    _make_plugin(tmp_path, "alpha")
    _write(tmp_path / PLUGINS_DIRNAME / "not-a-plugin" / "README.md", "no manifest\n")
    assert plugin_ids(tmp_path) == ["alpha", "beta"]


def test_plugin_ids_without_a_plugins_directory(tmp_path: Path) -> None:
    """An empty answer, never an exception, so callers can run anywhere."""
    assert plugin_ids(tmp_path) == []


def test_load_json_returns_untyped_data(tmp_path: Path) -> None:
    """The parsed document arrives as `object` and has to be narrowed before use."""
    path = tmp_path / "plugin.json"
    _write(path, '{"name": "alpha", "version": "1.2.3"}\n')
    parsed = load_json(path)
    assert as_str(as_mapping(parsed, path=path)["name"], path=path) == "alpha"


def test_load_json_names_the_file_it_could_not_parse(tmp_path: Path) -> None:
    """A parse failure without the path is useless in a repository-wide gate."""
    path = tmp_path / "broken.json"
    _write(path, "{not json}\n")
    with pytest.raises(MalformedJsonError, match=re.escape(str(path))):
        _ = load_json(path)


def test_load_json_propagates_a_missing_file(tmp_path: Path) -> None:
    """A missing file is an OSError, distinct from a file that parses badly."""
    with pytest.raises(FileNotFoundError):
        _ = load_json(tmp_path / "absent.json")


def test_as_mapping_rejects_a_list(tmp_path: Path) -> None:
    """The message names the file, the required shape and the type found."""
    path = tmp_path / "plugin.json"
    with pytest.raises(UnexpectedShapeError, match=re.escape("expected an object, found list")):
        _ = as_mapping([1, 2], path=path)


def test_as_mapping_rejects_non_string_keys(tmp_path: Path) -> None:
    """JSON objects always have string keys; anything else came from elsewhere."""
    path = tmp_path / "plugin.json"
    with pytest.raises(UnexpectedShapeError, match=re.escape("an object with string keys")):
        _ = as_mapping({1: "one"}, path=path)


def test_as_str_rejects_a_number(tmp_path: Path) -> None:
    """A version written as a number is a manifest defect, not a string."""
    path = tmp_path / "plugin.json"
    with pytest.raises(UnexpectedShapeError, match=re.escape("expected a string, found int")):
        _ = as_str(1, path=path)


def test_as_str_passes_a_string_through(tmp_path: Path) -> None:
    """The narrowing helpers return the same value, never a copy or a coercion."""
    assert as_str("alpha", path=tmp_path / "plugin.json") == "alpha"


@pytest.mark.slow
def test_git_output_returns_standard_output(git_repo: Path) -> None:
    """The general-purpose call is what the versioning area builds its refs and tags with."""
    assert git_output(git_repo, ["rev-parse", "--is-inside-work-tree"]).strip() == "true"


@pytest.mark.slow
def test_git_output_names_the_arguments_that_failed(git_repo: Path) -> None:
    """A gate line that only says "git failed" sends the reader back to the terminal."""
    with pytest.raises(GitCommandFailedError, match=re.escape("`git rev-parse --verify absent`")):
        _ = git_output(git_repo, ["rev-parse", "--verify", "absent"])


@pytest.mark.slow
def test_git_output_or_none_treats_a_refusal_as_an_answer(git_repo: Path) -> None:
    """Reading a path that does not exist at a ref is ordinary, not a failure."""
    assert git_output_or_none(git_repo, ["show", "absent:README.md"]) is None


@pytest.mark.slow
def test_git_output_or_none_still_returns_output_on_success(git_repo: Path) -> None:
    """The forgiving wrapper is the same call when the command works."""
    assert git_output_or_none(git_repo, ["rev-parse", "--is-inside-work-tree"]) is not None


def test_parse_json_narrows_text_the_same_way_as_a_file(tmp_path: Path) -> None:
    """Text from `git show` has to be parsed with the same narrowing as a file on disk."""
    path = tmp_path / "plugin.json"
    parsed = parse_json('{"name": "alpha"}', path=path)
    assert as_str(as_mapping(parsed, path=path)["name"], path=path) == "alpha"


def test_parse_json_names_the_path_it_was_told_about(tmp_path: Path) -> None:
    """The path is the caller's label for the text, so a ref read still points somewhere."""
    path = tmp_path / "plugin.json"
    with pytest.raises(MalformedJsonError, match=re.escape(str(path))):
        _ = parse_json("{nope}", path=path)
