"""X5: the legal documents are their templates' text, not a paraphrase of it.

`LICENSE` is checked byte for byte because that is what license detection needs: GitHub and
SPDX identify a license by matching the text, and a reformatted copy — a heading added, a
paragraph re-wrapped, the text put in a blockquote — stops being identified at all, so the
repository and every plugin in it silently become "no license".

`SECURITY.md` and `CODE_OF_CONDUCT.md` are checked differently, because they are templates
with placeholders: a filled-in placeholder re-wraps the paragraph around it. So what is
compared is every paragraph the template writes with no placeholder in it. R12 owns the
structure of the same two documents; this owns their wording, which keeps one home per rule.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Final

import pytest

from scripts.common.plugins import plugin_ids, working_files
from scripts.plugin_validation.kind import check_license, license_text
from scripts.plugin_validation.readme_contract import (
    HTML_COMMENT,
    LEGAL_DOCUMENTS,
    PLACEHOLDER,
    template_body,
)

if TYPE_CHECKING:
    from pathlib import Path

WHITESPACE: Final = re.compile(r"\s+")
"""Runs of whitespace, collapsed before comparing so re-wrapping is not drift."""

MIN_PARAGRAPH: Final = 40
"""Paragraphs shorter than this are headings and list markers, not wording."""

COMPARABLE: Final[dict[str, int]] = {
    "CODE_OF_CONDUCT.md": 18,
    "SECURITY.md": 0,
}
"""How many placeholder-free paragraphs each template pins, measured 2026-09-21.

`SECURITY.md` is 0 on purpose and the number is recorded rather than hidden: that template is
written as placeholders throughout, so every paragraph in it is meant to be replaced and there
is no shared wording to hold a copy to. Its structure is covered by R12 instead. If the
template ever gains fixed wording this count changes and the comparison starts applying.
"""


def _license_files(repo: Path) -> list[str]:
    """List every `LICENSE` this repository ships.

    Args:
        repo: The repository root.

    Returns:
        Sorted repository-relative paths, the templates excluded.
    """
    return [
        rel
        for rel in sorted(working_files(repo, "LICENSE", "*/LICENSE", "*/*/LICENSE"))
        if not rel.startswith("templates/")
    ]


def _paragraphs(text: str) -> list[str]:
    """Split a document into comparable paragraphs.

    Args:
        text: The document, instruction comments already removed.

    Returns:
        One normalised paragraph per block, placeholders and short blocks dropped.
    """
    blocks = [WHITESPACE.sub(" ", block).strip() for block in text.split("\n\n")]
    return [
        block
        for block in blocks
        if len(block) >= MIN_PARAGRAPH and PLACEHOLDER.search(block) is None
    ]


def test_this_repository_ships_licenses(repo: Path) -> None:
    """A rule over an empty list passes for free."""
    assert len(_license_files(repo)) > 1


@pytest.mark.parametrize("rel", ["LICENSE"])
def test_the_repository_license_is_the_template_verbatim(repo: Path, rel: str) -> None:
    """Reformatted license text is text SPDX no longer recognises as a license."""
    assert (repo / rel).read_text(encoding="utf-8") == license_text(repo)


def test_every_plugin_license_is_the_template_verbatim(repo: Path) -> None:
    """Each plugin is licensed in its own right, so each carries the same verbatim text."""
    findings = [
        finding for plugin_id in plugin_ids(repo) for finding in check_license(repo, plugin_id)
    ]
    assert [f"{finding.path}: {finding.message}" for finding in findings] == []


@pytest.mark.parametrize(("rel", "template"), sorted(LEGAL_DOCUMENTS.items()))
def test_every_unparameterised_paragraph_survives_the_copy(
    repo: Path, rel: str, template: str
) -> None:
    """Wording that carries no placeholder had no reason to change, so a change is drift."""
    source = _paragraphs(HTML_COMMENT.sub("", template_body(repo / template)))
    copied = WHITESPACE.sub(" ", HTML_COMMENT.sub("", (repo / rel).read_text(encoding="utf-8")))
    missing = [block for block in source if block not in copied]
    assert missing == [], f"{rel} no longer carries: {missing[:2]}"


@pytest.mark.parametrize(("rel", "expected"), sorted(COMPARABLE.items()))
def test_how_much_wording_each_template_actually_pins(repo: Path, rel: str, expected: int) -> None:
    """A check with nothing to compare passes for free, so the count is recorded, not assumed."""
    source = _paragraphs(HTML_COMMENT.sub("", template_body(repo / LEGAL_DOCUMENTS[rel])))
    assert len(source) == expected
