"""T1: the shape templates under the same README and frontmatter rules, with `{{…}}` allowed.

A template is what the next plugin starts from, so template rot becomes plugin rot. The
placeholders are substituted before the checks run, because `{{Display Name}}` is expected
there and only there.

Every shape passes clean, R9 included: the eval score table the templates carried until
2026-09-22 (§A10) is gone, and this test keeps it from coming back.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Final

import pytest

from scripts.common.plugins import repo_root
from scripts.plugin_validation.frontmatter import parse
from scripts.plugin_validation.readme_contract import (
    TEMPLATE_SHAPES,
    check_last_verified,
    check_no_eval_scores,
    check_sections,
)

if TYPE_CHECKING:
    from scripts.common.errors import Finding

PLACEHOLDER: Final = re.compile(r"\{\{[^{}]*\}\}")
"""What a template is expected to carry and a plugin is not (P4)."""

FILLED: Final = "placeholder"
"""What a placeholder is replaced with before the README checks run."""

BUNDLE_SHAPE: Final = "templates/plugin-bundle/README.md"
"""The only shape that legitimately carries an `Other components` section."""


def _findings(rel: str) -> list[Finding]:
    """Run the README structure checks over one shape template.

    Args:
        rel: The template's repository-relative path.

    Returns:
        Every finding, with placeholders already substituted.
    """
    text = PLACEHOLDER.sub(FILLED, (repo_root() / rel).read_text(encoding="utf-8"))
    return [
        *check_sections(rel, text, has_other_components=rel == BUNDLE_SHAPE),
        *check_last_verified(rel, text),
        *check_no_eval_scores(rel, text),
    ]


@pytest.mark.parametrize("rel", sorted(TEMPLATE_SHAPES), ids=sorted(TEMPLATE_SHAPES))
def test_a_shape_template_fires_nothing(rel: str) -> None:
    """A shape template passes the README structure checks (R1 sections, R9 included).

    Args:
        rel: The template's repository-relative path.
    """
    assert _findings(rel) == []


def test_the_master_template_declares_the_kind_line() -> None:
    """The `**Kind:**` line P1 reads is part of the template, not an author's invention."""
    master = (repo_root() / "templates/plugin-README-reusable-template.md").read_text(
        encoding="utf-8"
    )
    assert "**Kind:**" in master


def test_frontmatter_parsing_tolerates_a_placeholder() -> None:
    """A skill template's frontmatter has to parse once its placeholders are substituted."""
    template = "---\nname: {{skill-name}}\ndescription: Check {{a thing}}.\n---\n"
    block = parse(PLACEHOLDER.sub(FILLED, template))
    assert block.error is None
    assert block.data["name"] == FILLED
