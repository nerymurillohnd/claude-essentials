"""Hook wiring: H1 to H6, including the path H5 deliberately does not resolve."""

from __future__ import annotations

from typing import TYPE_CHECKING

from scripts.common.plugins import repo_root
from scripts.plugin_validation.conftest import PLUGIN_ID, SKILL_ID
from scripts.plugin_validation.hook_contract import (
    DEFAULT_TIMEOUT_AGENT,
    DEFAULT_TIMEOUT_COMMAND,
    DEFAULT_TIMEOUT_PROMPT,
    REDUCED_TIMEOUTS,
    SESSION_END_BUDGET,
    SESSION_END_EVENT,
    MatcherGroup,
    check_commands,
    check_fragment,
    check_handler_types,
    check_hooks_file,
    check_matchers,
    check_structure,
    check_timeouts,
    default_timeout,
    groups_from_hooks_json,
    is_regex_matcher,
)

if TYPE_CHECKING:
    from pathlib import Path

FRAGMENT_REL = f"plugins/{PLUGIN_ID}/skills/{SKILL_ID}/assets/settings-fragment.json"


def ids(findings: list[object]) -> list[str]:
    """Reduce findings to their invariant IDs.

    Args:
        findings: What a check returned.

    Returns:
        The IDs, in order.
    """
    return [getattr(finding, "invariant_id", "") for finding in findings]


def test_the_scratch_hooks_pass(scratch: Path) -> None:
    """The fixture's hook file is the baseline every probe is measured against.

    Args:
        scratch: The scratch repository root.
    """
    assert check_hooks_file(scratch, PLUGIN_ID) == []
    assert check_fragment(scratch, PLUGIN_ID, FRAGMENT_REL) == []


def test_an_undocumented_event_is_only_a_warning() -> None:
    """Upstream adds events, so an unknown name is reported rather than refused."""
    document: dict[str, object] = {"hooks": {"BrandNewEvent": []}}
    _, unknown = groups_from_hooks_json(document)
    findings = check_structure("hooks.json", document, unknown)
    assert [finding.severity for finding in findings] == ["warning"]


def test_an_unknown_handler_type_is_an_error() -> None:
    """A handler whose type is not one of the five documented kinds never runs."""
    group = MatcherGroup("PostToolUse", None, [{"type": "webhook"}])
    assert ids(list(check_handler_types("hooks.json", [group]))) == ["H1"]


def test_an_exact_matcher_is_not_a_regular_expression() -> None:
    """`Edit|Write` stays on the exact-match path; anything else is compiled by V8."""
    assert not is_regex_matcher("Edit|Write")
    assert not is_regex_matcher("code-reviewer")
    assert is_regex_matcher("^Notebook")


def test_an_unknown_exact_name_is_a_warning() -> None:
    """A typo in an exact matcher fires nothing; H3 reports it without blocking."""
    group = MatcherGroup("PostToolUse", "Edti", [])
    findings = check_matchers("hooks.json", [group])
    assert [(finding.invariant_id, finding.severity) for finding in findings] == [("H3", "warning")]


def test_a_regex_matching_no_known_tool_is_a_warning() -> None:
    """A pattern that matches nothing is suspicious but may name a tool added upstream."""
    group = MatcherGroup("PostToolUse", "^Nothing.*Here$", [])
    findings = check_matchers("hooks.json", [group])
    assert [(finding.invariant_id, finding.severity) for finding in findings] == [("H2", "warning")]


def test_default_timeouts_follow_the_documented_table() -> None:
    """The reduced per-event defaults are the ones a long timeout is measured against."""
    assert default_timeout("PostToolUse", "command") == DEFAULT_TIMEOUT_COMMAND
    assert default_timeout("MessageDisplay", "command") == REDUCED_TIMEOUTS["MessageDisplay"]
    assert default_timeout("UserPromptSubmit", "command") == REDUCED_TIMEOUTS["UserPromptSubmit"]
    assert default_timeout("PostToolUse", "prompt") == DEFAULT_TIMEOUT_PROMPT
    assert default_timeout("PostToolUse", "agent") == DEFAULT_TIMEOUT_AGENT
    assert default_timeout(SESSION_END_EVENT, "command") == SESSION_END_BUDGET


def test_a_timeout_above_the_default_is_refused() -> None:
    """Claude Code cancels the hook silently, so the gate refuses the value instead."""
    over = REDUCED_TIMEOUTS["MessageDisplay"] + 1
    group = MatcherGroup("MessageDisplay", None, [{"type": "command", "timeout": over}])
    assert ids(list(check_timeouts("hooks.json", [group]))) == ["H6"]


def test_a_session_end_timeout_within_the_ceiling_is_a_warning() -> None:
    """`SessionEnd` hooks share a budget the documentation allows raising to 60 seconds."""
    raised = SESSION_END_BUDGET + 1
    group = MatcherGroup(SESSION_END_EVENT, None, [{"type": "command", "timeout": raised}])
    findings = check_timeouts("hooks.json", [group])
    assert [(finding.invariant_id, finding.severity) for finding in findings] == [("H6", "warning")]


def test_a_project_dir_command_is_out_of_scope_for_h5(scratch: Path) -> None:
    """`$CLAUDE_PROJECT_DIR/...` names a file the plugin's installer writes later.

    That file cannot exist in this repository, so resolving it would report a dead handler
    that is not dead. `block-no-verify` ships exactly this shape.

    Args:
        scratch: The scratch repository root.
    """
    group = MatcherGroup(
        "PreToolUse",
        "Bash",
        [{"type": "command", "command": 'bash "$CLAUDE_PROJECT_DIR/.claude/hooks/x.sh"'}],
    )
    assert check_commands(scratch, "fragment.json", PLUGIN_ID, [group]) == []


def test_the_shipped_fragment_uses_that_shape() -> None:
    """The exemption is not hypothetical: the published plugin relies on it."""
    text = (
        repo_root() / "plugins/block-no-verify/skills/block-no-verify/assets/settings-fragment.json"
    ).read_text(encoding="utf-8")
    assert "$CLAUDE_PROJECT_DIR" in text
