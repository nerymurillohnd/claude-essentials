"""Kind derivation and the file-level invariants P1, P2, P4 and P5."""

from __future__ import annotations

from typing import TYPE_CHECKING

from scripts.common.plugins import repo_root
from scripts.plugin_validation.conftest import PLUGIN_ID
from scripts.plugin_validation.kind import (
    Kind,
    check_kind,
    check_license,
    check_no_bin,
    check_placeholders,
    derive_kind,
    license_text,
    readme_kind,
)

if TYPE_CHECKING:
    from pathlib import Path


def test_the_shipped_plugins_derive_the_kind_their_readmes_declare() -> None:
    """P1 holds on this working tree, which is the claim the gate makes."""
    root = repo_root()
    for plugin_id in ("agent-self-knowledge", "block-no-verify", "verify-completion"):
        readme = (root / "plugins" / plugin_id / "README.md").read_text(encoding="utf-8")
        assert readme_kind(readme) == str(derive_kind(root, plugin_id))


def test_one_skill_and_nothing_else_is_skill_only(tmp_path: Path) -> None:
    """The shape a plugin takes comes from its files, never from its manifest (ADR-0001).

    Args:
        tmp_path: pytest's per-test directory.
    """
    skill = tmp_path / "plugins" / "p" / "skills" / "s"
    skill.mkdir(parents=True)
    _ = (skill / "SKILL.md").write_text("---\nname: s\n---\n", encoding="utf-8")
    assert derive_kind(tmp_path, "p") == Kind.SKILL_ONLY


def test_one_agent_and_nothing_else_is_agent_only(tmp_path: Path) -> None:
    """A single subagent with no skill is the agent-only shape.

    Args:
        tmp_path: pytest's per-test directory.
    """
    agents = tmp_path / "plugins" / "p" / "agents"
    agents.mkdir(parents=True)
    _ = (agents / "a.md").write_text("---\nname: a\n---\n", encoding="utf-8")
    assert derive_kind(tmp_path, "p") == Kind.AGENT_ONLY


def test_a_second_component_makes_it_a_bundle(tmp_path: Path) -> None:
    """One skill plus hooks is a bundle, whatever the README says.

    Args:
        tmp_path: pytest's per-test directory.
    """
    plugin = tmp_path / "plugins" / "p"
    (plugin / "skills" / "s").mkdir(parents=True)
    _ = (plugin / "skills" / "s" / "SKILL.md").write_text("---\nname: s\n---\n", encoding="utf-8")
    (plugin / "hooks").mkdir()
    assert derive_kind(tmp_path, "p") == Kind.BUNDLE


def test_an_empty_directory_derives_no_kind(tmp_path: Path) -> None:
    """A directory that ships nothing is reported rather than guessed at.

    Args:
        tmp_path: pytest's per-test directory.
    """
    (tmp_path / "plugins" / "p").mkdir(parents=True)
    assert derive_kind(tmp_path, "p") is None


def test_the_license_template_is_the_apache_text(scratch: Path) -> None:
    """P2 compares against the template's own text, not a paraphrase of it.

    Args:
        scratch: The scratch repository root.
    """
    assert license_text(scratch).startswith("\n                                 Apache License")
    assert check_license(scratch, PLUGIN_ID) == []


def test_a_changed_license_is_refused(scratch: Path) -> None:
    """A single edited word breaks SPDX detection, so P2 compares bytes.

    Args:
        scratch: The scratch repository root.
    """
    path = scratch / "plugins" / PLUGIN_ID / "LICENSE"
    _ = path.write_text(path.read_text(encoding="utf-8").replace("Apache License", "A License", 1))
    assert [finding.invariant_id for finding in check_license(scratch, PLUGIN_ID)] == ["P2"]


def test_a_dollar_braced_expression_is_not_a_placeholder(scratch: Path) -> None:
    """`${{ … }}` in a workflow expression must not be read as a template leftover.

    Args:
        scratch: The scratch repository root.
    """
    path = scratch / "plugins" / PLUGIN_ID / "scripts" / "handler.sh"
    _ = path.write_text(path.read_text(encoding="utf-8") + 'echo "${{ matrix.os }}"\n')
    assert check_placeholders(scratch, PLUGIN_ID) == []


def test_a_top_level_bin_is_refused(scratch: Path) -> None:
    """P5 exists because a `bin/` ships a runtime the README never declared.

    Args:
        scratch: The scratch repository root.
    """
    (scratch / "plugins" / PLUGIN_ID / "bin").mkdir()
    assert [finding.invariant_id for finding in check_no_bin(scratch, PLUGIN_ID)] == ["P5"]


def test_a_readme_without_a_kind_line_is_reported(scratch: Path) -> None:
    """A README that declares no kind cannot be compared, so P1 says so.

    Args:
        scratch: The scratch repository root.
    """
    findings = check_kind(scratch, PLUGIN_ID, "# Title\n")
    assert [finding.invariant_id for finding in findings] == ["P1"]
