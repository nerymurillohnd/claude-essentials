"""Skill and subagent frontmatter: S1 to S6."""

from __future__ import annotations

from scripts.plugin_validation.frontmatter import (
    AGENT_KEYS,
    LISTING_LIMIT,
    SKILL_KEYS,
    check_agent_identity,
    check_agent_skills,
    check_description,
    check_known_keys,
    check_parses,
    check_tool_grants,
    parse,
    split_tool_grants,
)

DOCUMENTED_SKILL_KEYS = 20
"""Rows the skills reference listed on the documentation date."""

DOCUMENTED_AGENT_KEYS = 18
"""Rows the subagents reference listed on the documentation date."""

VALID = """---
name: s
description: Check a thing and report what it found.
when_to_use: When a test needs frontmatter that passes.
---

Body.
"""


def ids(findings: list[object]) -> list[str]:
    """Reduce findings to their invariant IDs.

    Args:
        findings: What a check returned.

    Returns:
        The IDs, in order.
    """
    return [getattr(finding, "invariant_id", "") for finding in findings]


def test_valid_frontmatter_parses() -> None:
    """The happy path is the baseline every probe is measured against."""
    block = parse(VALID)
    assert block.error is None
    assert block.data["name"] == "s"


def test_frontmatter_must_start_on_line_one() -> None:
    """Claude Code reads the block only when the opening fence is the first line."""
    block = parse("\n" + VALID)
    assert check_parses("x.md", block)[0].invariant_id == "S1"


def test_a_plain_scalar_with_a_colon_breaks_the_parse() -> None:
    """`description: a: b` is the defect S1 exists for: the CLI accepts it, YAML does not."""
    block = parse(VALID.replace("description: Check", "description: a: b Check"))
    assert check_parses("x.md", block)[0].invariant_id == "S1"


def test_an_unknown_key_is_only_a_warning() -> None:
    """Upstream adds fields between documentation refreshes, so S2 never blocks."""
    block = parse(VALID.replace("name: s", "name: s\nbrand-new-field: 1"))
    findings = check_known_keys("x.md", block, SKILL_KEYS, "S2")
    assert [finding.severity for finding in findings] == ["warning"]


def test_a_missing_when_to_use_is_reported() -> None:
    """Both halves of the listing budget have to be there for S3 to mean anything."""
    block = parse(VALID.replace("when_to_use: When a test needs frontmatter that passes.\n", ""))
    assert "S3" in ids(list(check_description("x.md", block)))


def test_the_listing_budget_is_enforced() -> None:
    """Past 1,536 characters the listing truncates, and the trigger text is what is lost."""
    block = parse(
        VALID.replace("Check a thing and report what it found.", "Check " + "x" * LISTING_LIMIT)
    )
    assert "S3" in ids(list(check_description("x.md", block)))


def test_a_non_imperative_opener_is_reported() -> None:
    """A description that introduces itself instead of instructing Claude is the defect."""
    block = parse(VALID.replace("Check a thing", "Comprehensive helper that does things"))
    assert "S3" in ids(list(check_description("x.md", block)))


def test_the_documented_opener_is_accepted() -> None:
    """The upstream `This skill should be used …` phrasing is not a finding."""
    block = parse(
        VALID.replace(
            "Check a thing and report what it found.", "This skill should be used when x."
        )
    )
    assert check_description("x.md", block) == []


def test_a_grant_pattern_may_contain_spaces_and_commas() -> None:
    """Splitting naively would cut `Bash(curl -sS https://x/*)` into grammar errors."""
    grants = split_tool_grants("Bash(curl -sS https://x/*) WebFetch(domain:x.test) Read")
    assert grants == ["Bash(curl -sS https://x/*)", "WebFetch(domain:x.test)", "Read"]


def test_unbalanced_parentheses_are_an_error() -> None:
    """A grant that does not parse never takes effect, so S4 refuses it."""
    block = parse(VALID.replace("name: s", "name: s\nallowed-tools: Bash(git status"))
    assert [finding.severity for finding in check_tool_grants("x.md", block)] == ["error"]


def test_an_unknown_tool_is_only_a_warning() -> None:
    """A tool this repository has not heard of may still exist upstream."""
    block = parse(VALID.replace("name: s", "name: s\nallowed-tools: Invented(x)"))
    assert [finding.severity for finding in check_tool_grants("x.md", block)] == ["warning"]


def test_an_agent_name_may_not_contain_a_colon() -> None:
    """Claude Code refuses to load such a file and only logs it, so S5 catches it first."""
    block = parse("---\nname: a:b\ndescription: d\n---\n")
    assert [finding.invariant_id for finding in check_agent_identity("x.md", block)] == ["S5"]


def test_an_agent_skill_reference_must_resolve() -> None:
    """A preloaded skill that does not exist leaves the subagent without its instructions."""
    block = parse("---\nname: a\ndescription: d\nskills:\n  - p:missing\n---\n")
    findings = check_agent_skills("x.md", block, ["p:present"])
    assert [finding.invariant_id for finding in findings] == ["S6"]


def test_agent_keys_and_skill_keys_are_the_documented_counts() -> None:
    """The dated key sets match what the reference pages listed on the docs date."""
    assert len(SKILL_KEYS) == DOCUMENTED_SKILL_KEYS
    assert len(AGENT_KEYS) == DOCUMENTED_AGENT_KEYS
