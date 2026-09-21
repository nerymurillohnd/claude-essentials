"""T1: the shape templates under the same README and frontmatter rules, with `{{…}}` allowed.

A template is what the next plugin starts from, so template rot becomes plugin rot. The
placeholders are substituted before the checks run, because `{{Display Name}}` is expected
there and only there.

One family still fires: R9, the eval score table the master template carries. Removing it is
step 11 of the migration (§A10), which owns `templates/`; this step owns
`scripts/plugin_validation/`. The pending set below is that record, and it is exact: a new
finding fails this test, and so does removing one without updating the set.
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

STEP_11_PENDING: Final[frozenset[tuple[str, str]]] = frozenset(
    (rel, "R9") for rel in TEMPLATE_SHAPES
)
"""The findings step 11 closes: the master template's eval score table (§A10).

Each shape fires R9 twice, once for the `Δ` column and once for the table header; the set
below is compared against the distinct (path, invariant) pairs.
"""


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
def test_a_shape_template_only_fires_what_step_eleven_owns(rel: str) -> None:
    """Every finding on a shape template is one the migration has already scheduled.

    Args:
        rel: The template's repository-relative path.
    """
    fired = {(finding.path or rel, finding.invariant_id) for finding in _findings(rel)}
    assert fired == {pair for pair in STEP_11_PENDING if pair[0] == rel}


def test_the_master_template_declares_the_kind_line() -> None:
    """The `**Kind:**` line P1 reads is part of the template, not an author's invention."""
    master = (repo_root() / "templates/plugin-README-reusable-template.md").read_text(
        encoding="utf-8"
    )
    assert "**Kind:**" in master


@pytest.mark.parametrize("rel", sorted(TEMPLATE_SHAPES), ids=sorted(TEMPLATE_SHAPES))
def test_a_shape_template_keeps_the_required_sections(rel: str) -> None:
    """R1 holds on every shape once its placeholders are filled in.

    Args:
        rel: The template's repository-relative path.
    """
    assert [finding.invariant_id for finding in _findings(rel)] == ["R9", "R9"]


def test_frontmatter_parsing_tolerates_a_placeholder() -> None:
    """A skill template's frontmatter has to parse once its placeholders are substituted."""
    template = "---\nname: {{skill-name}}\ndescription: Check {{a thing}}.\n---\n"
    block = parse(PLACEHOLDER.sub(FILLED, template))
    assert block.error is None
    assert block.data["name"] == FILLED
