"""The README contract: the structure, the badges, and the status collapse."""

from __future__ import annotations

from typing import TYPE_CHECKING

from scripts.common.plugins import plugin_ids, repo_root
from scripts.plugin_validation.conftest import PLUGIN_ID
from scripts.plugin_validation.readme_contract import (
    CompatibilityRow,
    check_badges,
    check_catalog,
    check_legal_texts,
    check_network_badge,
    check_no_eval_scores,
    check_requirements,
    check_sections,
    check_skill_commands,
    check_template_shapes,
    check_windows_rule,
    collapse,
    compatibility_rows,
    heading_order,
    readme_rel,
)

if TYPE_CHECKING:
    from pathlib import Path


def ids(findings: list[object]) -> list[str]:
    """Reduce findings to their invariant IDs.

    Args:
        findings: What a check returned.

    Returns:
        The IDs, in order.
    """
    return [getattr(finding, "invariant_id", "") for finding in findings]


def row(surface: str, status: str, verified: str = "—", notes: str = "") -> CompatibilityRow:
    """Build one Compatibility row.

    Args:
        surface: The first cell.
        status: The status emoji.
        verified: The `Last verified` cell.
        notes: The notes cell.

    Returns:
        The record.
    """
    return CompatibilityRow(surface, status, verified, notes)


def test_a_missing_section_is_reported(scratch: Path) -> None:
    """A README that drops a section misleads by omission, which is why R1 is strict.

    Args:
        scratch: The scratch repository root.
    """
    path = scratch / "plugins" / PLUGIN_ID / "README.md"
    text = path.read_text(encoding="utf-8").replace("## 🚧 Limitations", "## Limits")
    assert "R1" in ids(list(check_sections(readme_rel(PLUGIN_ID), text, has_other_components=True)))


def test_an_unearned_other_components_section_is_reported(scratch: Path) -> None:
    """The optional section exists only when the plugin ships such a component.

    Args:
        scratch: The scratch repository root.
    """
    text = (scratch / "plugins" / PLUGIN_ID / "README.md").read_text(encoding="utf-8")
    findings = check_sections(readme_rel(PLUGIN_ID), text, has_other_components=False)
    assert "R1" in ids(list(findings))


def test_every_shipped_readme_has_the_template_headings() -> None:
    """R1 holds on this working tree."""
    root = repo_root()
    for plugin_id in plugin_ids(root):
        headings = heading_order(
            (root / "plugins" / plugin_id / "README.md").read_text(encoding="utf-8")
        )
        assert "🧭 Compatibility" in headings


def test_all_supported_with_a_dated_remote_install_collapses_to_supported() -> None:
    """The only way a catalog row earns a ✅ is a dated install of the published marketplace."""
    rows = [
        row("Claude Code on macOS", "✅", "2026-09-19", "Installed from the remote marketplace")
    ]
    assert collapse(rows, "Claude Code") == "✅"


def test_a_local_checkout_does_not_earn_a_supported_status() -> None:
    """`--plugin-dir` proves the files work, not that the published plugin installs."""
    rows = [row("Claude Code on macOS", "✅", "2026-09-19", "local checkout only")]
    assert collapse(rows, "Claude Code") == "⚠️"


def test_mixed_platform_rows_collapse_to_partial() -> None:
    """One verified platform and one untested platform is not full support."""
    rows = [
        row("Claude Code on macOS", "✅", "2026-09-19", "Installed from the remote marketplace"),
        row("Claude Code on Linux", "🧪"),
    ]
    assert collapse(rows, "Claude Code") == "⚠️"


def test_no_supported_row_collapses_to_not_tested() -> None:
    """A plugin nobody has installed anywhere is 🧪, not ⚠️."""
    rows = [row("Claude Code on macOS", "🧪"), row("Claude Code on Windows without Git Bash", "❌")]
    assert collapse(rows, "Claude Code") == "🧪"


def test_every_unsupported_row_collapses_to_unsupported() -> None:
    """A surface that cannot run the plugin at all is ❌."""
    assert collapse([row("Claude Cowork", "❌")], "Claude Cowork") == "❌"


def test_a_cloud_row_does_not_decide_the_catalog_status() -> None:
    """A deployment variant is a caveat, not a platform, so it never lifts the status."""
    rows = [row("Claude Code on macOS", "🧪"), row("Claude Code cloud sessions", "⚠️")]
    assert collapse(rows, "Claude Code") == "🧪"


def test_the_catalog_matches_every_shipped_readme() -> None:
    """R8 and R14 hold on this working tree."""
    root = repo_root()
    readme = (root / "README.md").read_text(encoding="utf-8")
    assert check_catalog(root, readme, plugin_ids(root)) == []


def test_the_shipped_compatibility_tables_parse() -> None:
    """Every published README's table is readable by the collapse."""
    root = repo_root()
    for plugin_id in plugin_ids(root):
        text = (root / "plugins" / plugin_id / "README.md").read_text(encoding="utf-8")
        assert compatibility_rows(text)


def test_an_eval_table_is_refused() -> None:
    """R9 is the one firm content rule: a score in a README goes stale silently."""
    text = "| Case | Checks | With | Without | Δ | Last run |\n"
    assert ids(list(check_no_eval_scores("x.md", text))) == ["R9", "R9"]


def test_a_network_badge_claiming_none_is_refused(scratch: Path) -> None:
    """A plugin that fetches a page while its badge says `none` misleads the installer.

    Args:
        scratch: The scratch repository root.
    """
    text = (scratch / "plugins" / PLUGIN_ID / "README.md").read_text(encoding="utf-8")
    assert ids(list(check_network_badge("x.md", text, networked=True))) == ["R4"]
    assert check_network_badge("x.md", text, networked=False) == []


def test_a_badge_outside_the_catalog_is_reported() -> None:
    """A made-up badge reads as a requirement nobody reviewed; the catalog is the list."""
    root = repo_root()
    plugin = "block-no-verify"
    text = (root / "plugins" / plugin / "README.md").read_text(encoding="utf-8")
    assert check_badges(root, plugin, "x.md", text) == []
    invented = text.replace(
        "![Bash](", "![Madeup](https://img.shields.io/badge/madeup-1-555555)\n![Bash](", 1
    )
    assert invented != text
    assert "`Madeup`" in " ".join(
        str(finding) for finding in check_badges(root, plugin, "x.md", invented)
    )


def test_a_missing_requirements_row_is_reported(scratch: Path) -> None:
    """Every binary the shipped files invoke has to be discoverable before installing.

    Args:
        scratch: The scratch repository root.
    """
    path = scratch / "plugins" / PLUGIN_ID / "README.md"
    _ = path.write_text(
        path.read_text(encoding="utf-8").replace(
            "| Bash | 3.2 | `bash --version` | Runs the handler. |\n", ""
        ),
        encoding="utf-8",
    )
    text = path.read_text(encoding="utf-8")
    assert "R5" in ids(list(check_requirements(scratch, PLUGIN_ID, "x.md", text)))


def test_the_windows_rule_applies_only_to_bash_hooks(scratch: Path) -> None:
    """A plugin with no `bash` hook has nothing to say about Git Bash.

    Args:
        scratch: The scratch repository root.
    """
    text = (scratch / "plugins" / PLUGIN_ID / "README.md").read_text(encoding="utf-8")
    assert check_windows_rule("x.md", text, runs_bash=True) == []
    assert check_windows_rule("x.md", "no mention", runs_bash=False) == []
    assert ids(list(check_windows_rule("x.md", "no mention", runs_bash=True))) == ["R10"]


def test_a_dead_slash_command_is_reported(scratch: Path) -> None:
    """A Skills table that names a skill the plugin does not ship is a dead link.

    Args:
        scratch: The scratch repository root.
    """
    text = f"## 🧠 Skills\n\n| x |\n| `/{PLUGIN_ID}:absent` |\n"
    assert ids(list(check_skill_commands(scratch, PLUGIN_ID, "x.md", text))) == ["R11"]


def test_the_shape_templates_and_legal_documents_hold() -> None:
    """R7 and R12 hold on this working tree."""
    root = repo_root()
    assert check_template_shapes(root) == []
    assert check_legal_texts(root) == []
