"""Tests for CHANGELOG parsing and the P3, C1 and C2 checks."""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

import pytest

from scripts.versioning.changelog import (
    UNRELEASED_LABEL,
    announces_deprecation,
    check_entry,
    check_links,
    check_released_bodies,
    parse_changelog,
    read_changelog,
    released_body_at_tag,
    tag_name,
)
from scripts.versioning.conftest import commit_all, git_in, write_file

if TYPE_CHECKING:
    from pathlib import Path

    from scripts.common.errors import Finding

BASE: Final = "https://github.com/nerymurillohnd/claude-essentials"

CORRECT: Final = f"""# Changelog

All notable changes to this plugin are documented here.

## [Unreleased]

### Added

- Nothing yet.

## [0.1.1] - 2026-09-20

### Fixed

- A wording fix in the skill.

## [0.1.0] - 2026-09-18

### Added

- First release.

[Unreleased]: {BASE}/compare/demo--v0.1.1...HEAD
[0.1.1]: {BASE}/compare/demo--v0.1.0...demo--v0.1.1
[0.1.0]: {BASE}/tree/demo--v0.1.0
"""
"""The one style this repository publishes: `tree/` first, `compare/` after."""

SECOND_RELEASE_AS_TREE: Final = CORRECT.replace(
    f"[0.1.1]: {BASE}/compare/demo--v0.1.0...demo--v0.1.1",
    f"[0.1.1]: {BASE}/tree/demo--v0.1.1",
)
"""The defect C1 names: three plugins link a second release to a snapshot, not to a diff."""


def _ids(findings: list[Finding]) -> list[str]:
    """Collect the invariant ids of a finding list.

    Args:
        findings: The findings to read.

    Returns:
        Their ids, in order.
    """
    return [finding.invariant_id for finding in findings]


def test_parse_reads_every_section_in_file_order() -> None:
    """The parser keeps the file's order, so a reader can point at a line number."""
    changelog = parse_changelog(CORRECT)
    assert [section.label for section in changelog.sections] == ["Unreleased", "0.1.1", "0.1.0"]


def test_released_sections_come_back_oldest_first() -> None:
    """C1 builds the footer from the oldest release forward, so the order matters."""
    assert [section.label for section in parse_changelog(CORRECT).released()] == ["0.1.0", "0.1.1"]


def test_parse_reads_the_date_and_the_body() -> None:
    """A section carries its date and everything under it, with blank edges removed."""
    section = parse_changelog(CORRECT).find("0.1.1")
    assert section is not None
    assert section.date == "2026-09-20"
    assert section.body == "### Fixed\n\n- A wording fix in the skill."


def test_the_unreleased_section_has_no_date() -> None:
    """Nothing is released yet, so the heading carries no ` - YYYY-MM-DD`."""
    unreleased = parse_changelog(CORRECT).unreleased()
    assert unreleased is not None
    assert unreleased.date is None


def test_footer_links_are_not_part_of_the_last_section_body() -> None:
    """C2 compares bodies, so a repaired footer link must not look like a rewritten body."""
    section = parse_changelog(CORRECT).find("0.1.0")
    assert section is not None
    assert "[Unreleased]:" not in section.body
    assert [label for label, _ in parse_changelog(CORRECT).links] == [
        "Unreleased",
        "0.1.1",
        "0.1.0",
    ]


def test_a_link_inside_a_section_stays_in_its_body() -> None:
    """Only the trailing block of definitions is the footer."""
    text = "## [0.1.0] - 2026-09-18\n\n[a]: https://example.test/x\n\nText.\n\n[0.1.0]: u\n"
    changelog = parse_changelog(text)
    section = changelog.find("0.1.0")
    assert section is not None
    assert "[a]: https://example.test/x" in section.body
    assert changelog.links == (("0.1.0", "u"),)


def test_read_changelog_reads_a_file(tmp_path: Path) -> None:
    """The file reader and the string parser agree."""
    path = tmp_path / "CHANGELOG.md"
    write_file(path, CORRECT)
    assert read_changelog(path).sections == parse_changelog(CORRECT).sections


def test_announces_deprecation_finds_the_heading() -> None:
    """A removal is only allowed after a release that carried this heading."""
    assert announces_deprecation("### Deprecated\n\n- Gone soon.")
    assert not announces_deprecation("### Added\n\n- Something about deprecated things.")


def test_tag_name_prefers_the_current_name() -> None:
    """A plugin that was never renamed tags under its own name."""
    assert tag_name("0.1.0", names=["demo"], known_tags=()) == "demo--v0.1.0"


def test_tag_name_falls_back_to_a_predecessor() -> None:
    """A renamed plugin keeps the tags it was released under."""
    resolved = tag_name("0.1.0", names=["new", "old"], known_tags={"old--v0.1.0"})
    assert resolved == "old--v0.1.0"


def test_check_entry_accepts_a_dated_section() -> None:
    """P3 is satisfied by a section for the manifest version, carrying a real date."""
    assert check_entry(parse_changelog(CORRECT), version="0.1.1", path="p/CHANGELOG.md") == []


def test_check_entry_reports_a_missing_section() -> None:
    """The defect P3 names: a release that ships with no notes at all."""
    findings = check_entry(parse_changelog(CORRECT), version="0.2.0", path="p/CHANGELOG.md")
    assert _ids(findings) == ["P3"]
    assert "0.2.0" in findings[0].message


def test_check_entry_reports_a_missing_date() -> None:
    """An undated heading gives a user no idea when the version shipped."""
    text = CORRECT.replace("## [0.1.1] - 2026-09-20", "## [0.1.1]")
    findings = check_entry(parse_changelog(text), version="0.1.1", path="p/CHANGELOG.md")
    assert _ids(findings) == ["P3"]
    assert "no ` - YYYY-MM-DD` date" in findings[0].message


def test_check_entry_reports_an_impossible_date() -> None:
    """`2026-02-30` parses as a heading but is not a day anyone released on."""
    text = CORRECT.replace("## [0.1.1] - 2026-09-20", "## [0.1.1] - 2026-02-30")
    findings = check_entry(parse_changelog(text), version="0.1.1", path="p/CHANGELOG.md")
    assert _ids(findings) == ["P3"]
    assert "real calendar date" in findings[0].message


def test_check_links_accepts_the_house_style() -> None:
    """The first release links to a tree, every later one to a compare, Unreleased to HEAD."""
    assert check_links(parse_changelog(CORRECT), path="p/CHANGELOG.md", names=["demo"]) == []


def test_check_links_rejects_a_second_release_linked_as_a_tree() -> None:
    """The mixed style measured in the 2026-09 review.

    A reader who clicks the second release's link asks for a diff and gets a snapshot.
    """
    findings = check_links(
        parse_changelog(SECOND_RELEASE_AS_TREE),
        path="p/CHANGELOG.md",
        names=["demo"],
    )
    assert _ids(findings) == ["C1"]
    assert "compare/demo--v0.1.0...demo--v0.1.1" in findings[0].message


def test_check_links_reports_a_missing_definition() -> None:
    """A section with no footer link renders as literal brackets on GitHub."""
    text = CORRECT.replace(f"[0.1.0]: {BASE}/tree/demo--v0.1.0\n", "")
    findings = check_links(parse_changelog(text), path="p/CHANGELOG.md", names=["demo"])
    assert _ids(findings) == ["C1"]
    assert "[0.1.0]" in findings[0].message


def test_check_links_reports_two_base_urls() -> None:
    """One style everywhere: a second base means one link points at another repository."""
    text = CORRECT.replace(f"[0.1.0]: {BASE}/tree/", "[0.1.0]: https://example.test/tree/")
    findings = check_links(parse_changelog(text), path="p/CHANGELOG.md", names=["demo"])
    assert "several bases" in " ".join(finding.message for finding in findings)


def test_check_links_reports_an_unrecognised_shape() -> None:
    """A link that is neither a tree nor a compare cannot be checked at all."""
    text = CORRECT.replace(f"[0.1.0]: {BASE}/tree/demo--v0.1.0", "[0.1.0]: https://example.test/x")
    findings = check_links(parse_changelog(text), path="p/CHANGELOG.md", names=["demo"])
    assert "neither a `tree/` nor a `compare/` link" in findings[0].message


def test_check_links_follows_a_rename(tmp_path: Path) -> None:
    """A renamed plugin's older versions keep linking to the tags they were published under."""
    text = CORRECT.replace("demo--v0.1.0", "old--v0.1.0").replace("demo--v0.1.1", "new--v0.1.1")
    _ = tmp_path
    findings = check_links(
        parse_changelog(text),
        path="p/CHANGELOG.md",
        names=["new", "old"],
        known_tags={"old--v0.1.0", "new--v0.1.1"},
    )
    assert findings == []


@pytest.mark.slow
def test_released_body_at_tag_reads_the_published_text(repo: Path) -> None:
    """C2 needs the text as it was at the tag, not as it is now."""
    body = released_body_at_tag(repo, "alpha", "0.1.0")
    assert body is not None
    assert "First release." in body


@pytest.mark.slow
def test_released_body_at_tag_returns_none_without_a_tag(repo: Path) -> None:
    """A version that was never published has nothing frozen to compare against."""
    assert released_body_at_tag(repo, "alpha", "9.9.9") is None


@pytest.mark.slow
def test_check_released_bodies_passes_on_an_untouched_changelog(repo: Path) -> None:
    """Nothing was rewritten, so C2 has nothing to say."""
    path = repo / "plugins" / "alpha" / "CHANGELOG.md"
    findings = check_released_bodies(
        repo,
        read_changelog(path),
        path="plugins/alpha/CHANGELOG.md",
        names=["alpha"],
        known_tags={"alpha--v0.1.0"},
    )
    assert findings == []


@pytest.mark.slow
def test_check_released_bodies_catches_a_rewritten_release(repo: Path) -> None:
    """DEBT-0009: the notes a user reads for 0.1.0 must be the notes that shipped with it."""
    path = repo / "plugins" / "alpha" / "CHANGELOG.md"
    write_file(path, path.read_text(encoding="utf-8").replace("First release.", "Rewritten."))
    findings = check_released_bodies(
        repo,
        read_changelog(path),
        path="plugins/alpha/CHANGELOG.md",
        names=["alpha"],
        known_tags={"alpha--v0.1.0"},
    )
    assert _ids(findings) == ["C2"]
    assert UNRELEASED_LABEL in findings[0].message
    assert "### Errata" in findings[0].message


@pytest.mark.slow
def test_a_correction_under_unreleased_is_allowed(repo: Path) -> None:
    """The sanctioned way to correct a released note leaves the released body alone."""
    path = repo / "plugins" / "alpha" / "CHANGELOG.md"
    text = path.read_text(encoding="utf-8").replace(
        "## [Unreleased]\n",
        "## [Unreleased]\n\n### Errata\n\n- 0.1.0 said 'first'; it was the first public one.\n",
    )
    write_file(path, text)
    _ = commit_all(repo, "errata")
    _ = git_in(repo, "status", "--short")
    findings = check_released_bodies(
        repo,
        read_changelog(path),
        path="plugins/alpha/CHANGELOG.md",
        names=["alpha"],
        known_tags={"alpha--v0.1.0"},
    )
    assert findings == []
