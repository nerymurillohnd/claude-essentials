"""Tests for the dropdown generator: byte identity outside the block, and idempotence."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from scripts.common.errors import ExitCode
from scripts.common.plugins import repo_root
from scripts.github.generate_issue_forms import main, render_option, rewrite, write
from scripts.github.issue_forms import (
    dropdown_options,
    expected_options,
    form_paths,
    load_yaml,
)

if TYPE_CHECKING:
    from pathlib import Path

FORM = """name: Bug report
description: Something broke.
labels:
  - "type: bug"
body:
  - type: markdown
    attributes:
      value: |
        Read this first.
  - type: dropdown
    id: plugin
    attributes:
      label: Affected plugin
      description: Pick one.
      options:
        - Marketplace catalog / installation
        - alpha
        - Not sure
    validations:
      required: true
  - type: dropdown
    id: surface
    attributes:
      label: Surface
      options:
        - Claude Code
"""
"""A form with the generated block in the middle and a second dropdown after it."""


def test_nothing_outside_the_block_changes() -> None:
    """The one guarantee a text edit owes: comments, blank lines and wording survive."""
    rewritten = rewrite(FORM, ["Marketplace catalog / installation", "beta", "Not sure"])
    before, _, after = FORM.partition("        - Marketplace catalog / installation\n")
    new_before, _, new_after = rewritten.partition("        - Marketplace catalog / installation\n")
    assert new_before == before
    assert new_after.split("    validations:\n", 1)[1] == after.split("    validations:\n", 1)[1]


def test_the_second_dropdown_is_untouched() -> None:
    """Only the block under `id: plugin` is owned by this generator."""
    rewritten = rewrite(FORM, ["Marketplace catalog / installation", "beta", "Not sure"])
    assert "        - Claude Code\n" in rewritten
    assert "        - alpha\n" not in rewritten
    assert "        - beta\n" in rewritten


def test_rewriting_is_idempotent() -> None:
    """The second run changes nothing, so `make generate` leaves a clean tree."""
    options = ["Marketplace catalog / installation", "beta", "Not sure"]
    once = rewrite(FORM, options)
    assert rewrite(once, options) == once


def test_a_form_without_the_dropdown_is_returned_unchanged() -> None:
    """The documentation form has no plugin dropdown and must not be rewritten."""
    text = "name: Docs\nbody:\n  - type: input\n    id: location\n"
    assert rewrite(text, ["a"]) == text


def test_the_indentation_of_the_existing_block_is_kept() -> None:
    """YAML is whitespace-significant; a changed indent would break the form."""
    rewritten = rewrite(FORM, ["one"])
    assert "        - one\n" in rewritten


def test_an_option_with_a_colon_is_quoted() -> None:
    """A plain scalar containing `: ` is a mapping, not a string."""
    assert render_option("Claude Code: CLI") == '"Claude Code: CLI"'


def test_a_plain_option_is_not_quoted() -> None:
    """The tracked forms write plain scalars; quoting them all would be a diff."""
    assert render_option("agent-self-knowledge") == "agent-self-knowledge"


def test_the_catalog_option_stays_plain() -> None:
    """It contains a slash, which YAML reads as an ordinary character."""
    assert render_option("Marketplace catalog / installation") == (
        "Marketplace catalog / installation"
    )


@pytest.mark.slow
def test_running_it_on_this_tree_produces_no_diff() -> None:
    """The tracked forms are already what the generator writes."""
    assert write(repo_root()) == []


@pytest.mark.slow
def test_every_tracked_dropdown_parses_back_to_the_expected_options() -> None:
    """The text edit and the YAML reader agree on what was written."""
    root = repo_root()
    for path in form_paths(root):
        options = dropdown_options(load_yaml(path))
        if options is not None:
            assert options == expected_options(root)


def test_a_stale_form_is_rewritten(tmp_path: Path) -> None:
    """Adding a plugin reaches the forms through this generator.

    Args:
        tmp_path: pytest's per-test temporary directory.
    """
    directory = tmp_path / ".github" / "ISSUE_TEMPLATE"
    directory.mkdir(parents=True)
    stale = FORM.replace("        - alpha\n", "")
    _ = (directory / "bug-report.yml").write_text(stale, encoding="utf-8")
    (tmp_path / "plugins" / "alpha" / ".claude-plugin").mkdir(parents=True)
    _ = (tmp_path / "plugins" / "alpha" / ".claude-plugin" / "plugin.json").write_text(
        "{}", encoding="utf-8"
    )
    assert write(tmp_path) == [".github/ISSUE_TEMPLATE/bug-report.yml"]
    assert "        - alpha\n" in (directory / "bug-report.yml").read_text(encoding="utf-8")


@pytest.mark.slow
def test_main_outside_a_repository_is_one_line(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Every entrypoint here ends in one `error: …` line rather than a traceback.

    Args:
        tmp_path: pytest's per-test temporary directory.
        capsys: Captures what the entrypoint printed.
        monkeypatch: Moves the process outside any git working tree.
    """
    monkeypatch.chdir(tmp_path)
    assert main([]) == int(ExitCode.USAGE)
    captured = capsys.readouterr()
    assert captured.err.startswith("error: ")
    assert "Traceback" not in captured.err
