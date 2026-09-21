"""Tests for the triage rules: every path rule, the form answers, and the bump replacement."""

from __future__ import annotations

import pytest

from scripts.common.plugins import plugin_ids, repo_root
from scripts.github.labels import DEFERRED_LABEL, plugin_label_name, replaced_bump_labels
from scripts.github.triage_rules import (
    CATALOG_ANSWER,
    CATALOG_AREA,
    CI_AREA,
    COMMUNITY_AREA,
    DOCS_AREA,
    NEEDS_INFO,
    NEEDS_TRIAGE,
    PLUGIN_QUESTION,
    PLUGINS_AREA,
    TEMPLATES_AREA,
    TOOLING_AREA,
    UNSURE_ANSWER,
    CommentEvent,
    area_for_path,
    bump_label,
    labels_for_issue,
    labels_for_pr,
    needs_info_reply,
    parse_form_answers,
    plugin_for_path,
    reply_label_changes,
)

PATH_RULES: list[tuple[str, str | None]] = [
    ("plugins/block-no-verify/hooks/hooks.json", PLUGINS_AREA),
    ("plugins/block-no-verify/README.md", PLUGINS_AREA),
    (".claude-plugin/marketplace.json", CATALOG_AREA),
    (".github/workflows/ci.yml", CI_AREA),
    (".github/policy/ruleset.json", CI_AREA),
    (".github/dependabot.yml", CI_AREA),
    (".github/ISSUE_TEMPLATE/bug-report.yml", COMMUNITY_AREA),
    (".github/labels.json", COMMUNITY_AREA),
    (".github/pull_request_template.md", COMMUNITY_AREA),
    (".github/schemas/issue-forms.schema.json", COMMUNITY_AREA),
    ("CODE_OF_CONDUCT.md", COMMUNITY_AREA),
    ("SECURITY.md", COMMUNITY_AREA),
    ("CONTRIBUTING.md", COMMUNITY_AREA),
    ("scripts/github/triage_rules.py", TOOLING_AREA),
    ("Makefile", TOOLING_AREA),
    ("pyproject.toml", TOOLING_AREA),
    ("uv.lock", TOOLING_AREA),
    (".python-version", TOOLING_AREA),
    (".editorconfig", TOOLING_AREA),
    (".claude/rules/plugin-delivery.md", TOOLING_AREA),
    ("templates/plugin-bundle/README.md", TEMPLATES_AREA),
    ("docs/decisions/adr-0004-issue-and-label-protocol.md", DOCS_AREA),
    ("README.md", DOCS_AREA),
    ("CLAUDE.md", DOCS_AREA),
    (".gitignore", None),
    ("LICENSE", None),
]
"""Every path rule of §A11, one row each, including the two that earn no area."""


@pytest.mark.parametrize(("path", "expected"), PATH_RULES)
def test_every_path_rule(path: str, expected: str | None) -> None:
    """The table is the rule; a change to either side must fail here first."""
    assert area_for_path(path) == expected


def test_a_github_file_is_community_before_it_is_ci() -> None:
    """The order matters: both rules match `.github/`, and community is decided first."""
    assert area_for_path(".github/labels.json") == COMMUNITY_AREA


def test_a_root_governance_document_is_community_before_it_is_docs() -> None:
    """All three are root Markdown files, which the docs rule would otherwise claim."""
    assert area_for_path("SECURITY.md") == COMMUNITY_AREA


def test_plugin_for_path_names_the_directory() -> None:
    """A change inside a plugin earns that plugin's label as well as the area."""
    assert plugin_for_path("plugins/ruff-quality/skills/ruff/SKILL.md") == "ruff-quality"


@pytest.mark.parametrize(
    "path",
    ["plugins/README.md", "docs/x.md", "plugins/Not A Name/file.md", "plugins/x"],
)
def test_plugin_for_path_refuses_anything_else(path: str) -> None:
    """An invalid directory name must never become an invalid label (ADR-0004)."""
    assert plugin_for_path(path) is None


def test_labels_for_pr_combines_areas_plugins_and_the_bump() -> None:
    """One pull request, three families of label."""
    labels = labels_for_pr(
        ["plugins/ruff-quality/skills/ruff/SKILL.md", "docs/x.md"],
        {"label": "bump: patch"},
    )
    assert labels == {PLUGINS_AREA, plugin_label_name("ruff-quality"), DOCS_AREA, "bump: patch"}


def test_labels_for_pr_applies_no_bump_when_none_was_computed() -> None:
    """A wrong `bump: none` is worse than no label at all."""
    assert labels_for_pr(["docs/x.md"], None) == {DOCS_AREA}


@pytest.mark.parametrize("document", [{}, {"label": "area: docs"}, [], "text"])
def test_bump_label_refuses_anything_that_is_not_a_bump(document: object) -> None:
    """The label field is read, never guessed."""
    assert bump_label(document) is None


def test_bump_label_reads_the_contract() -> None:
    """The `label` key of `check_versions --json`."""
    assert bump_label({"route": "pr", "label": "bump: minor"}) == "bump: minor"


def test_the_computed_bump_replaces_the_previous_one() -> None:
    """A pull request carries exactly one computed `bump:` label."""
    assert replaced_bump_labels({"bump: patch", DOCS_AREA}, "bump: minor") == ["bump: patch"]


def test_a_deferred_bump_survives_the_replacement() -> None:
    """It is maintainer-applied and PR-wide; triage must never take it away (§A11)."""
    assert replaced_bump_labels({DEFERRED_LABEL}, "bump: none") == []


def test_parse_form_answers_reads_the_rendered_headings() -> None:
    """Pins the `### Question` format GitHub renders an issue form into (ADR-0004)."""
    body = f"### {PLUGIN_QUESTION}\n\nruff-quality\n\n### Surface\n\nClaude Code\n"
    assert parse_form_answers(body) == {PLUGIN_QUESTION: "ruff-quality", "Surface": "Claude Code"}


def test_parse_form_answers_keeps_a_blank_answer() -> None:
    """An optional field left empty is an answer, not a missing question."""
    assert parse_form_answers("### Notes\n\n_No response_\n") == {"Notes": "_No response_"}


@pytest.mark.slow
def test_an_issue_naming_a_plugin_earns_its_label() -> None:
    """The dropdown is the only input; nothing is inferred from the title."""
    known = plugin_ids(repo_root())
    answers = {PLUGIN_QUESTION: known[0]}
    assert labels_for_issue(answers, known_plugins=known) == {plugin_label_name(known[0])}


def test_an_issue_about_the_catalog_earns_the_catalog_area() -> None:
    """A marketplace-wide problem belongs to no single plugin."""
    assert labels_for_issue({PLUGIN_QUESTION: CATALOG_ANSWER}, known_plugins=[]) == {CATALOG_AREA}


@pytest.mark.parametrize("answer", [UNSURE_ANSWER, "", "something-else"])
def test_an_unknown_answer_earns_nothing(answer: str) -> None:
    """An invented label cannot be filtered on and breaks the taxonomy as code."""
    assert labels_for_issue({PLUGIN_QUESTION: answer}, known_plugins=["alpha"]) == set()


def test_an_author_reply_moves_the_issue_back_to_triage() -> None:
    """The stale bot stops counting as soon as the author answers."""
    event = CommentEvent(
        issue_author="reporter",
        comment_author="reporter",
        issue_labels=frozenset({NEEDS_INFO}),
    )
    assert needs_info_reply(event) is True
    assert reply_label_changes(event) == ({NEEDS_TRIAGE}, {NEEDS_INFO})


def test_a_maintainer_comment_is_not_a_reply() -> None:
    """Only the author can answer the question that was asked of them."""
    event = CommentEvent(
        issue_author="reporter",
        comment_author="maintainer",
        issue_labels=frozenset({NEEDS_INFO}),
    )
    assert needs_info_reply(event) is False
    assert reply_label_changes(event) == (set(), set())


def test_a_reply_on_an_issue_that_is_not_waiting_changes_nothing() -> None:
    """Only `status: needs-info` issues are moved."""
    event = CommentEvent(
        issue_author="reporter",
        comment_author="reporter",
        issue_labels=frozenset({NEEDS_TRIAGE}),
    )
    assert needs_info_reply(event) is False


def test_an_anonymous_comment_is_not_a_reply() -> None:
    """A payload without a login must not match an issue without one."""
    event = CommentEvent(issue_author="", comment_author="", issue_labels=frozenset({NEEDS_INFO}))
    assert needs_info_reply(event) is False
