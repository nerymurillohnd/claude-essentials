"""Hook wiring: the seven invariants H1 to H7, over `hooks.json` and settings fragments.

Both surfaces are checked, because both end up in a user's settings: `hooks/hooks.json`
is registered by installing the plugin, and `**/assets/settings-fragment.json` is the
matcher group a skill's own installer merges into `settings.json`. A dead handler path is
equally invisible either way.

Matchers are judged by V8 (P12), not by Python's `re`: Claude Code compiles a matcher with
`new RegExp` and tests it with `RegExp.prototype.test`, and the two engines disagree on
exactly the patterns a maintainer would get wrong.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import TYPE_CHECKING, Final

from scripts.common.errors import Finding, GitCommandFailedError
from scripts.common.javascript import regex_matches
from scripts.common.jsontext import is_json_array, is_json_object
from scripts.common.plugins import PLUGINS_DIRNAME, git_output, load_json
from scripts.plugin_validation.cli_coverage import KNOWN_TOOLS, is_known_tool

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from pathlib import Path

HOOKS_RELATIVE_PATH: Final = "hooks/hooks.json"
"""Where a plugin declares the hooks installing it registers."""

FRAGMENT_NAME: Final = "settings-fragment.json"
"""The file name a skill's installer merges into a user's `settings.json`."""

HOOK_EVENTS: Final[tuple[str, ...]] = (
    "SessionStart",
    "Setup",
    "InstructionsLoaded",
    "UserPromptSubmit",
    "UserPromptExpansion",
    "MessageDisplay",
    "PreToolUse",
    "PermissionRequest",
    "PostToolUse",
    "PostToolUseFailure",
    "PostToolBatch",
    "PermissionDenied",
    "Notification",
    "SubagentStart",
    "SubagentStop",
    "TaskCreated",
    "TaskCompleted",
    "Stop",
    "StopFailure",
    "TeammateIdle",
    "ConfigChange",
    "CwdChanged",
    "DirectoryAdded",
    "FileChanged",
    "WorktreeCreate",
    "WorktreeRemove",
    "PreCompact",
    "PostCompact",
    "PreModelSwitch",
    "PostModelSwitch",
    "SessionEnd",
    "Elicitation",
    "ElicitationResult",
)
"""The 33 events the hooks reference documents on `cli_coverage.DOCS_DATE`."""

HANDLER_TYPES: Final[frozenset[str]] = frozenset({"command", "http", "mcp_tool", "prompt", "agent"})
"""The handler `type` values the hooks reference documents on `cli_coverage.DOCS_DATE`."""

COMMAND_LIKE_TYPES: Final[frozenset[str]] = frozenset({"command", "http", "mcp_tool"})
"""Handler types that share one default timeout and one per-event reduction."""

DEFAULT_TIMEOUT_COMMAND: Final = 600.0
"""Seconds a `command`, `http` or `mcp_tool` handler gets unless the event lowers it."""

DEFAULT_TIMEOUT_PROMPT: Final = 30.0
"""Seconds a `prompt` handler gets."""

DEFAULT_TIMEOUT_AGENT: Final = 60.0
"""Seconds an `agent` handler gets."""

REDUCED_TIMEOUTS: Final[Mapping[str, float]] = {
    "UserPromptSubmit": 30.0,
    "PreModelSwitch": 30.0,
    "PostModelSwitch": 30.0,
    "MessageDisplay": 10.0,
}
"""Events that lower the `command`, `http` and `mcp_tool` default."""

SESSION_END_EVENT: Final = "SessionEnd"
"""The event whose hooks share one budget rather than each getting a default."""

SESSION_END_BUDGET: Final = 1.5
"""Seconds `SessionEnd` hooks share by default."""

SESSION_END_MAX: Final = 60.0
"""Seconds a longer `SessionEnd` `timeout` may raise that shared budget to."""

EXACT_MATCHER: Final = re.compile(r"^[A-Za-z0-9_, |-]*$")
"""Characters that keep a matcher on the exact-match path instead of the regex path."""

MATCH_ALL: Final[frozenset[str]] = frozenset({"", "*"})
"""Matcher values that fire on every occurrence of the event."""

PLUGIN_ROOT_PATH: Final = re.compile(r"\$\{?CLAUDE_PLUGIN_ROOT\}?/(?P<path>[^\s\"']+)")
"""A shipped file referenced from a `command`, in either the braced or the bare form."""

# `$CLAUDE_PROJECT_DIR/...` is deliberately out of H5's scope: it names a file the plugin's
# own installer writes into the user's project later, so it does not exist in this tree and
# is not a dead handler. `test_hook_contract` pins that behaviour.
PROJECT_DIR_PATH: Final = re.compile(r"\$\{?CLAUDE_PROJECT_DIR\}?/")
"""A path the plugin installs at run time, which this repository cannot resolve."""

EXECUTABLE_MODE: Final = "100755"
"""The git mode a handler script must carry so Claude Code can run it."""

ALLOWED_SHEBANGS: Final[tuple[str, ...]] = ("#!/usr/bin/env bash", "#!/usr/bin/env python3")
"""The only two interpreters a plugin may assume a user has (§2.1)."""


@dataclass(frozen=True, slots=True)
class MatcherGroup:
    """One matcher and the handlers it fires.

    Attributes:
        event: The hook event the group is registered under.
        matcher: The matcher exactly as written, or None when the key is absent.
        handlers: The handler objects, unnarrowed.
    """

    event: str
    matcher: str | None
    handlers: Sequence[object]


def _as_str_or_none(value: object) -> str | None:
    """Narrow a parsed JSON value to a string, treating anything else as absent.

    Args:
        value: The parsed value.

    Returns:
        The string, or None.
    """
    return value if isinstance(value, str) else None


def groups_from_hooks_json(document: object) -> tuple[list[MatcherGroup], list[str]]:
    """Read every matcher group out of a `hooks.json` document.

    Args:
        document: The parsed file.

    Returns:
        The groups, and the event names the file used that are not documented.
    """
    groups: list[MatcherGroup] = []
    unknown: list[str] = []
    if not is_json_object(document):
        return groups, unknown
    events = document.get("hooks")
    if not is_json_object(events):
        return groups, unknown
    for event, value in events.items():
        if event not in HOOK_EVENTS:
            unknown.append(event)
        if not is_json_array(value):
            continue
        groups.extend(_group(event, entry) for entry in value if is_json_object(entry))
    return groups, sorted(unknown)


def _group(event: str, entry: Mapping[str, object]) -> MatcherGroup:
    """Turn one matcher-group object into a record.

    Args:
        event: The event the group sits under.
        entry: The parsed group.

    Returns:
        The record, with an empty handler list when `hooks` is not an array.
    """
    handlers = entry.get("hooks")
    return MatcherGroup(
        event,
        _as_str_or_none(entry.get("matcher")),
        list(handlers) if is_json_array(handlers) else [],
    )


def check_structure(rel: str, document: object, unknown_events: Sequence[str]) -> list[Finding]:
    """Check the document's own shape and its event names (H1).

    Args:
        rel: The file's repository-relative path.
        document: The parsed file.
        unknown_events: Event names the file used that the reference does not list.

    Returns:
        One finding when the shape is wrong, and one warning per undocumented event.
    """
    if not is_json_object(document):
        return [Finding("H1", rel, "the document is not a JSON object")]
    findings: list[Finding] = [
        Finding("H1", rel, f"event {event!r} is not documented on the hooks reference", "warning")
        for event in unknown_events
    ]
    if "hooks" not in document:
        findings.append(Finding("H1", rel, "no `hooks` object"))
    return findings


def check_handler_types(rel: str, groups: Sequence[MatcherGroup]) -> list[Finding]:
    """Check that every handler declares a documented `type` (H1).

    Args:
        rel: The file's repository-relative path.
        groups: The matcher groups read from the file.

    Returns:
        One finding per handler with a missing or unknown type.
    """
    findings: list[Finding] = []
    for group in groups:
        for handler in group.handlers:
            if not is_json_object(handler):
                findings.append(Finding("H1", rel, f"{group.event}: a handler is not an object"))
                continue
            kind = handler.get("type")
            if not isinstance(kind, str) or kind not in HANDLER_TYPES:
                findings.append(
                    Finding("H1", rel, f"{group.event}: handler `type` {kind!r} is not documented")
                )
    return findings


def is_regex_matcher(matcher: str) -> bool:
    """Report whether Claude Code evaluates a matcher as a regular expression.

    Args:
        matcher: The matcher exactly as written.

    Returns:
        True when the value contains a character outside the exact-match set.
    """
    return EXACT_MATCHER.match(matcher) is None


def check_matchers(rel: str, groups: Sequence[MatcherGroup]) -> list[Finding]:
    """Check every matcher under V8 (H2) and every exact name against the tools (H3).

    Args:
        rel: The file's repository-relative path.
        groups: The matcher groups read from the file.

    Returns:
        An error per pattern V8 refuses, and a warning per pattern or name that matches no
        tool this repository has heard of.
    """
    findings: list[Finding] = []
    tools = sorted(KNOWN_TOOLS)
    for group in groups:
        matcher = group.matcher
        if matcher is None or matcher in MATCH_ALL:
            continue
        if is_regex_matcher(matcher):
            findings.extend(_regex_findings(rel, group.event, matcher, tools))
            continue
        findings.extend(_exact_findings(rel, group.event, matcher))
    return findings


def _regex_findings(rel: str, event: str, matcher: str, tools: Sequence[str]) -> list[Finding]:
    """Compile one regex matcher under V8 and report what it matches (H2).

    Args:
        rel: The file's repository-relative path.
        event: The event the matcher sits under.
        matcher: The pattern.
        tools: The known tool names to test it against.

    Returns:
        One error when V8 refuses the pattern, or one warning when it matches no known tool.
    """
    matched, error = regex_matches(matcher, tools)
    if error is not None:
        return [
            Finding("H2", rel, f"{event}: matcher {matcher!r} does not compile under V8: {error}")
        ]
    if not matched:
        return [
            Finding("H2", rel, f"{event}: matcher {matcher!r} matches no known tool", "warning")
        ]
    return []


def _exact_findings(rel: str, event: str, matcher: str) -> list[Finding]:
    """Check the names in an exact-match matcher (H3).

    Args:
        rel: The file's repository-relative path.
        event: The event the matcher sits under.
        matcher: The matcher, a list of names separated by `|` or `,`.

    Returns:
        One warning per name that is neither a documented tool nor an MCP tool.
    """
    names = [name.strip() for name in re.split(r"[|,]", matcher) if name.strip()]
    return [
        Finding("H3", rel, f"{event}: matcher names {name!r}, not a documented tool", "warning")
        for name in names
        if not is_known_tool(name)
    ]


FILE_TOOL_TWINS: Final[Mapping[str, str]] = {"Edit": "Write", "Write": "Edit"}
"""File tools whose `if` rules never match each other, unlike permission rules.

Measured on Claude Code 2.1.278 (2026-09-22): in a hook `if`, `Edit(*.py)` fired for the
Edit tool only and `Write(*.py)` for the Write tool only, in PreToolUse and PostToolUse.
"""

CONDITION: Final = re.compile(r"^(?P<tool>[A-Za-z]+)\((?P<pattern>.*)\)$")
"""A permission rule as a hook `if` writes it: `Tool(pattern)`."""


def _fires_on(matcher: str | None, tool: str) -> bool:
    """Report whether a group's matcher fires for one tool.

    Args:
        matcher: The matcher exactly as written, or None when absent.
        tool: The tool name.

    Returns:
        True when the group runs its handlers for that tool.
    """
    if matcher is None or matcher in MATCH_ALL:
        return True
    if is_regex_matcher(matcher):
        matched, _ = regex_matches(matcher, [tool])
        return bool(matched)
    return tool in {name.strip() for name in re.split(r"[|,]", matcher)}


def _twin_message(event: str, tool: str, pattern: str) -> str:
    """Describe one missing twin condition (H7).

    Args:
        event: The event the handler sits under.
        tool: The tool whose condition is missing.
        pattern: The path pattern both conditions share.

    Returns:
        The finding's message.
    """
    have = f"{FILE_TOOL_TWINS[tool]}({pattern})"
    need = f"{tool}({pattern})"
    why = "a hook `if` rule matches one tool only"
    return f"{event}: `{have}` has no `{need}` twin running the same command ({why})"


def check_file_tool_conditions(rel: str, groups: Sequence[MatcherGroup]) -> list[Finding]:
    """Check that an `Edit(...)` or `Write(...)` condition has its twin (H7).

    A handler filtered by `Edit(P)` in a group that also fires on Write never runs for a
    written file, so the same group needs a `Write(P)` handler running the same command,
    and the reverse.

    Args:
        rel: The file's repository-relative path.
        groups: The matcher groups read from the file.

    Returns:
        One error per handler whose twin is missing.
    """
    findings: list[Finding] = []
    for group in groups:
        present: set[tuple[str, str, str]] = set()
        wanted: list[tuple[str, str, str]] = []
        for handler in group.handlers:
            if not is_json_object(handler):
                continue
            match = CONDITION.match(_as_str_or_none(handler.get("if")) or "")
            if match is None or match["tool"] not in FILE_TOOL_TWINS:
                continue
            command = _as_str_or_none(handler.get("command")) or ""
            present.add((match["tool"], match["pattern"], command))
            wanted.append((FILE_TOOL_TWINS[match["tool"]], match["pattern"], command))
        findings.extend(
            Finding("H7", rel, _twin_message(group.event, tool, pattern))
            for tool, pattern, command in wanted
            if _fires_on(group.matcher, tool) and (tool, pattern, command) not in present
        )
    return findings


def default_timeout(event: str, handler_type: str) -> float:
    """Return the timeout the reference documents for an event and handler type (H6).

    Args:
        event: The hook event.
        handler_type: The handler's `type`.

    Returns:
        Seconds, as the hooks reference records them on `cli_coverage.DOCS_DATE`.
    """
    if event == SESSION_END_EVENT:
        return SESSION_END_BUDGET
    if handler_type == "prompt":
        return DEFAULT_TIMEOUT_PROMPT
    if handler_type == "agent":
        return DEFAULT_TIMEOUT_AGENT
    return REDUCED_TIMEOUTS.get(event, DEFAULT_TIMEOUT_COMMAND)


def check_timeouts(rel: str, groups: Sequence[MatcherGroup]) -> list[Finding]:
    """Check that every `timeout` is a number within the documented default (H6).

    Args:
        rel: The file's repository-relative path.
        groups: The matcher groups read from the file.

    Returns:
        One finding per handler whose timeout is not numeric or exceeds its default.
        A `SessionEnd` handler above the shared budget is a warning up to the documented
        ceiling the budget can be raised to, and an error above it.
    """
    findings: list[Finding] = []
    for group in groups:
        for handler in group.handlers:
            if not is_json_object(handler):
                continue
            findings.extend(_timeout_findings(rel, group.event, handler))
    return findings


def _timeout_findings(rel: str, event: str, handler: Mapping[str, object]) -> list[Finding]:
    """Check one handler's `timeout`.

    Args:
        rel: The file's repository-relative path.
        event: The event the handler sits under.
        handler: The parsed handler.

    Returns:
        One finding when the value is not numeric or is above what the event allows.
    """
    raw = handler.get("timeout")
    if raw is None:
        return []
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        return [Finding("H6", rel, f"{event}: `timeout` is {raw!r}, not a number")]
    kind = handler.get("type")
    allowed = default_timeout(event, kind if isinstance(kind, str) else "command")
    if raw <= allowed:
        return []
    if event == SESSION_END_EVENT and raw <= SESSION_END_MAX:
        return [
            Finding(
                "H6",
                rel,
                f"{event}: `timeout` {raw} raises the shared {allowed}s budget",
                "warning",
            ),
        ]
    return [
        Finding(
            "H6", rel, f"{event}: `timeout` {raw} is above the documented default of {allowed}s"
        )
    ]


def check_commands(
    root: Path, rel: str, plugin_id: str, groups: Sequence[MatcherGroup]
) -> list[Finding]:
    """Check that every `command` is non-empty (H4) and resolves to a runnable file (H5).

    Args:
        root: The repository root.
        rel: The file's repository-relative path.
        plugin_id: The plugin the file belongs to, which `${CLAUDE_PLUGIN_ROOT}` resolves to.
        groups: The matcher groups read from the file.

    Returns:
        One finding per empty command and per referenced file that is missing, not
        executable, or carries an interpreter a user may not have.
    """
    findings: list[Finding] = []
    for group in groups:
        for handler in group.handlers:
            if not is_json_object(handler) or handler.get("type") != "command":
                continue
            command = handler.get("command")
            if not isinstance(command, str) or not command.strip():
                findings.append(Finding("H4", rel, f"{group.event}: `command` is missing or empty"))
                continue
            findings.extend(_referenced_file_findings(root, rel, plugin_id, group.event, command))
    return findings


def _referenced_file_findings(
    root: Path, rel: str, plugin_id: str, event: str, command: str
) -> list[Finding]:
    """Resolve every `${CLAUDE_PLUGIN_ROOT}` path in a command and check the file (H5).

    Args:
        root: The repository root.
        rel: The file's repository-relative path.
        plugin_id: The plugin the command ships with.
        event: The event the handler sits under.
        command: The command line.

    Returns:
        One finding per referenced file that cannot run as written.
    """
    findings: list[Finding] = []
    for match in PLUGIN_ROOT_PATH.finditer(command):
        target = f"{PLUGINS_DIRNAME}/{plugin_id}/{match.group('path')}"
        findings.extend(_runnable_findings(root, rel, event, target))
    return findings


def _runnable_findings(root: Path, rel: str, event: str, target: str) -> list[Finding]:
    """Check that one shipped file exists, is executable and declares a portable shebang.

    Args:
        root: The repository root.
        rel: The file the command was read from.
        event: The event the handler sits under.
        target: The repository-relative path the command names.

    Returns:
        One finding per rule broken.
    """
    path = root / target
    if not path.is_file():
        return [Finding("H5", rel, f"{event}: the command names `{target}`, which does not exist")]
    findings: list[Finding] = []
    if git_mode(root, target) != EXECUTABLE_MODE:
        findings.append(
            Finding(
                "H5",
                rel,
                f"{event}: `{target}` is not tracked with the exec bit ({EXECUTABLE_MODE})",
            )
        )
    shebang = path.read_text(encoding="utf-8").splitlines()[:1]
    if not shebang or shebang[0] not in ALLOWED_SHEBANGS:
        findings.append(
            Finding("H5", rel, f"{event}: `{target}` does not start with a bash or python3 shebang")
        )
    return findings


def git_mode(root: Path, rel: str) -> str | None:
    """Return the file mode git records for a tracked path.

    Args:
        root: The repository root.
        rel: The repository-relative path.

    Returns:
        The six-digit mode, or None when git does not track the path.
    """
    try:
        output = git_output(root, ["ls-files", "-s", "--", rel])
    except GitCommandFailedError:
        return None
    line = output.strip()
    return line.split(maxsplit=1)[0] if line else None


def fragment_groups(document: object) -> list[MatcherGroup]:
    """Read the single matcher group a settings fragment carries.

    A fragment is merged under an event the installer chooses, so the event is unknown
    here and recorded as `settings fragment`; H1's event check does not apply to it.

    Args:
        document: The parsed fragment.

    Returns:
        A one-element list, or an empty list when the shape is wrong.
    """
    if not is_json_object(document):
        return []
    return [_group("settings fragment", document)]


def check_hooks_file(root: Path, plugin_id: str) -> list[Finding]:
    """Run H1 to H7 over a plugin's `hooks/hooks.json`.

    Args:
        root: The repository root.
        plugin_id: The plugin directory name.

    Returns:
        Every finding; an empty list when the plugin registers no hooks.
    """
    rel = f"{PLUGINS_DIRNAME}/{plugin_id}/{HOOKS_RELATIVE_PATH}"
    path = root / rel
    if not path.is_file():
        return []
    document = load_json(path)
    groups, unknown = groups_from_hooks_json(document)
    return [
        *check_structure(rel, document, unknown),
        *check_handler_types(rel, groups),
        *check_matchers(rel, groups),
        *check_timeouts(rel, groups),
        *check_file_tool_conditions(rel, groups),
        *check_commands(root, rel, plugin_id, groups),
    ]


def check_fragment(root: Path, plugin_id: str, rel: str) -> list[Finding]:
    """Run H1 to H7 over one `assets/settings-fragment.json`.

    Args:
        root: The repository root.
        plugin_id: The plugin the fragment ships with.
        rel: The fragment's repository-relative path.

    Returns:
        Every finding.
    """
    document = load_json(root / rel)
    groups = fragment_groups(document)
    if not groups:
        return [Finding("H1", rel, "the document is not a JSON object")]
    return [
        *check_handler_types(rel, groups),
        *check_matchers(rel, groups),
        *check_timeouts(rel, groups),
        *check_file_tool_conditions(rel, groups),
        *check_commands(root, rel, plugin_id, groups),
    ]
