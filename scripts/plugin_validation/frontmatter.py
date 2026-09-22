"""Skill and subagent frontmatter: the six invariants S1 to S6.

The documented key sets are dated constants read on `cli_coverage.DOCS_DATE`. An unknown
key is a **warning**, not an error: upstream adds fields between refreshes, and a gate that
refused a field Claude Code already honours would be worse than one that reports a name it
has not heard of.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import TYPE_CHECKING, Final

import yaml

from scripts.common.errors import Finding
from scripts.common.jsontext import is_json_array, is_json_object
from scripts.plugin_validation.cli_coverage import is_known_tool

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence
    from pathlib import Path

# yaml.safe_load is annotated `-> Any`; this alias is the one place that Any becomes object.
_safe_load: Callable[[str], object] = yaml.safe_load

FRONTMATTER_FENCE: Final = "---"
"""The delimiter that opens and closes a YAML frontmatter block."""

SKILL_KEYS: Final[frozenset[str]] = frozenset(
    {
        "agent",
        "allowed-tools",
        "argument-hint",
        "arguments",
        "background",
        "compatibility",
        "context",
        "description",
        "disable-model-invocation",
        "disallowed-tools",
        "effort",
        "hooks",
        "license",
        "metadata",
        "model",
        "name",
        "paths",
        "shell",
        "user-invocable",
        "when_to_use",
    }
)
"""The 20 skill frontmatter fields documented on `DOCS_DATE` (skills reference)."""

AGENT_KEYS: Final[frozenset[str]] = frozenset(
    {
        "background",
        "color",
        "description",
        "disallowedTools",
        "effort",
        "experimental",
        "hooks",
        "initialPrompt",
        "isolation",
        "maxTurns",
        "mcpServers",
        "memory",
        "model",
        "name",
        "omitClaudeMd",
        "permissionMode",
        "skills",
        "tools",
    }
)
"""The 18 subagent frontmatter fields documented on `DOCS_DATE` (subagents reference)."""

LISTING_LIMIT: Final = 1536
"""Characters of `description` plus `when_to_use` the skill listing keeps before truncating."""

IMPERATIVE_OPENERS: Final[frozenset[str]] = frozenset(
    {
        "add",
        "answer",
        "apply",
        "audit",
        "build",
        "check",
        "choose",
        "configure",
        "convert",
        "create",
        "decide",
        "deliver",
        "derive",
        "design",
        "detect",
        "diagnose",
        "enforce",
        "ensure",
        "explain",
        "extract",
        "fetch",
        "find",
        "fix",
        "generate",
        "guide",
        "handle",
        "identify",
        "inspect",
        "install",
        "keep",
        "lint",
        "list",
        "load",
        "maintain",
        "make",
        "manage",
        "map",
        "measure",
        "migrate",
        "prove",
        "publish",
        "read",
        "refactor",
        "report",
        "retrieve",
        "review",
        "run",
        "scan",
        "set",
        "show",
        "stop",
        "summarize",
        "test",
        "trace",
        "track",
        "translate",
        "turn",
        "update",
        "use",
        "validate",
        "verify",
        "write",
    }
)
"""Base-form verbs a skill `description` may open with, recorded on `DOCS_DATE`."""

DOCUMENTED_OPENER: Final = "this skill should be used"
"""The alternative opener the upstream skill-authoring guidance uses."""

TOOL_GRANT: Final = re.compile(
    r"^(?P<tool>[A-Za-z][A-Za-z0-9_]*)(?:\((?P<pattern>.*)\))?$", re.DOTALL
)
"""An `allowed-tools` entry: a tool name, optionally followed by one parenthesised pattern."""

PLAIN_SCALAR_COLON: Final = ": "
"""A colon and a space inside an unquoted YAML value turn it into a mapping and break parsing."""

AGENT_SKILL_REF: Final = re.compile(r"^(?P<plugin>[a-z0-9-]+):(?P<skill>[a-z0-9-]+)$")
"""The `<plugin>:<skill>` form a subagent's `skills:` entry must take."""


@dataclass(frozen=True, slots=True)
class Frontmatter:
    """One parsed frontmatter block.

    Attributes:
        data: The mapping YAML produced, empty when the block could not be parsed.
        raw: The block's text, without the fences.
        error: The parser's complaint, or None when the block parsed.
    """

    data: Mapping[str, object]
    raw: str
    error: str | None


def parse(text: str) -> Frontmatter:
    """Split a Markdown file into its frontmatter block and parse it.

    Args:
        text: The whole file.

    Returns:
        The parsed block; `error` says why when it is not usable.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != FRONTMATTER_FENCE:
        return Frontmatter({}, "", "no YAML frontmatter on line 1")
    for index in range(1, len(lines)):
        if lines[index].strip() == FRONTMATTER_FENCE:
            return _parse_block("\n".join(lines[1:index]))
    return Frontmatter({}, "", "the frontmatter block is never closed")


def _parse_block(raw: str) -> Frontmatter:
    """Parse the text between the fences.

    Args:
        raw: The block's text.

    Returns:
        The parsed block; `error` says why when YAML refused it or it is not a mapping.
    """
    try:
        document = _safe_load(raw)
    except yaml.YAMLError as error:
        return Frontmatter({}, raw, str(error).replace("\n", " "))
    if not is_json_object(document):
        return Frontmatter({}, raw, "the frontmatter is not a mapping")
    return Frontmatter(document, raw, None)


def split_tool_grants(value: str) -> list[str]:
    """Split an `allowed-tools` string on the separators that sit outside parentheses.

    A grant's pattern may contain spaces and commas (`Bash(curl -sS https://x/*)`), so a
    naive split would cut a single grant into pieces and report grammar errors that are not
    there.

    Args:
        value: The field's text.

    Returns:
        The individual grants, with surrounding whitespace removed.
    """
    grants: list[str] = []
    current: list[str] = []
    depth = 0
    for character in value:
        if character == "(":
            depth += 1
        elif character == ")":
            depth = max(depth - 1, 0)
        if depth == 0 and (character.isspace() or character == ","):
            grants.append("".join(current))
            current = []
            continue
        current.append(character)
    grants.append("".join(current))
    return [grant.strip() for grant in grants if grant.strip()]


def tool_grants(value: object) -> list[str]:
    """Normalise an `allowed-tools` field to a list of grants.

    Args:
        value: The field as YAML produced it: a string or a list.

    Returns:
        The grants, in order; empty when the field is absent or of another type.
    """
    if isinstance(value, str):
        return split_tool_grants(value)
    if is_json_array(value):
        return [item for item in value if isinstance(item, str)]
    return []


def check_known_keys(
    rel: str, block: Frontmatter, known: frozenset[str], ident: str
) -> list[Finding]:
    """Report frontmatter keys the documentation did not list (S2, warning).

    Args:
        rel: The file's repository-relative path.
        block: The parsed frontmatter.
        known: The documented key set.
        ident: The invariant ID to speak with.

    Returns:
        One warning naming every unknown key.
    """
    unknown = sorted(set(block.data) - known)
    if not unknown:
        return []
    return [
        Finding(
            ident,
            rel,
            f"frontmatter keys not documented on the reference page: {unknown}",
            "warning",
        )
    ]


def check_parses(rel: str, block: Frontmatter) -> list[Finding]:
    """Check that the frontmatter is there, starts on line 1 and parses (S1).

    Args:
        rel: The file's repository-relative path.
        block: The parsed frontmatter.

    Returns:
        One finding when the block is missing or YAML refused it.
    """
    if block.error is None:
        return []
    return [Finding("S1", rel, block.error)]


def _opens_imperatively(description: str) -> bool:
    """Report whether a description opens with a base-form verb or the documented phrase.

    Args:
        description: The field's value.

    Returns:
        True when the opener is acceptable.
    """
    stripped = description.lstrip()
    if stripped.lower().startswith(DOCUMENTED_OPENER):
        return True
    first = re.split(r"[^A-Za-z]", stripped, maxsplit=1)[0]
    return first.lower() in IMPERATIVE_OPENERS


def _plain_scalar_findings(rel: str, block: Frontmatter, field: str) -> list[Finding]:
    """Report a `key: value` line whose unquoted value carries a colon and a space.

    Args:
        rel: The file's repository-relative path.
        block: The parsed frontmatter.
        field: The key to inspect.

    Returns:
        One finding when the raw line would have broken a stricter parser.
    """
    prefix = f"{field}: "
    for line in block.raw.splitlines():
        if not line.startswith(prefix):
            continue
        value = line[len(prefix) :]
        if value[:1] in {'"', "'", "|", ">"}:
            return []
        if PLAIN_SCALAR_COLON in value:
            return [Finding("S3", rel, f"`{field}` is a plain scalar containing `: `")]
    return []


def check_description(rel: str, block: Frontmatter) -> list[Finding]:
    """Check a skill's `description` and `when_to_use` (S3).

    Args:
        rel: The file's repository-relative path.
        block: The parsed frontmatter.

    Returns:
        One finding per rule broken: a missing field, the listing cap, the opener, or a
        plain scalar that carries `: `.
    """
    findings: list[Finding] = []
    values: dict[str, str] = {}
    for field in ("description", "when_to_use"):
        value = block.data.get(field)
        if not isinstance(value, str) or not value.strip():
            findings.append(Finding("S3", rel, f"`{field}` is missing or empty"))
            continue
        values[field] = value
        findings.extend(_plain_scalar_findings(rel, block, field))
    combined = sum(len(text) for text in values.values())
    if combined > LISTING_LIMIT:
        findings.append(
            Finding(
                "S3",
                rel,
                f"`description` plus `when_to_use` is {combined} characters, over {LISTING_LIMIT}",
            )
        )
    description = values.get("description")
    if description is not None and not _opens_imperatively(description):
        opener = description.split(maxsplit=1)[0]
        findings.append(
            Finding("S3", rel, f"`description` opens with {opener!r}, not a base-form verb")
        )
    return findings


def check_tool_grants(rel: str, block: Frontmatter) -> list[Finding]:
    """Check that every `allowed-tools` entry parses and names a tool (S4).

    Args:
        rel: The file's repository-relative path.
        block: The parsed frontmatter.

    Returns:
        An error per entry that does not parse, and a warning per unknown tool name.
    """
    findings: list[Finding] = []
    for grant in tool_grants(block.data.get("allowed-tools")):
        if grant.count("(") != grant.count(")"):
            findings.append(
                Finding("S4", rel, f"`allowed-tools` entry {grant!r} has unbalanced parentheses")
            )
            continue
        match = TOOL_GRANT.match(grant)
        if match is None:
            findings.append(
                Finding(
                    "S4", rel, f"`allowed-tools` entry {grant!r} is not `Tool` or `Tool(pattern)`"
                )
            )
            continue
        tool = match.group("tool")
        if not is_known_tool(tool):
            findings.append(
                Finding(
                    "S4", rel, f"`allowed-tools` grants {tool!r}, not a documented tool", "warning"
                )
            )
    return findings


def check_agent_identity(rel: str, block: Frontmatter) -> list[Finding]:
    """Check a subagent's `name` and `description` (S5).

    Args:
        rel: The file's repository-relative path.
        block: The parsed frontmatter.

    Returns:
        One finding per rule broken.
    """
    findings: list[Finding] = []
    name = block.data.get("name")
    if not isinstance(name, str) or not name.strip():
        findings.append(Finding("S5", rel, "`name` is missing"))
    elif ":" in name:
        findings.append(
            Finding("S5", rel, f"`name` {name!r} contains `:`, which Claude Code refuses to load")
        )
    description = block.data.get("description")
    if not isinstance(description, str) or not description.strip():
        findings.append(Finding("S5", rel, "`description` is missing"))
    return findings


def check_agent_skills(rel: str, block: Frontmatter, known_skills: Sequence[str]) -> list[Finding]:
    """Check that every preloaded skill reference resolves on disk (S6).

    Args:
        rel: The file's repository-relative path.
        block: The parsed frontmatter.
        known_skills: Every `<plugin>:<skill>` this marketplace ships.

    Returns:
        One finding per entry that is malformed or names a skill that is not there.
    """
    value = block.data.get("skills")
    if value is None:
        return []
    entries = [item for item in value if isinstance(item, str)] if is_json_array(value) else []
    if isinstance(value, str):
        entries = [item.strip() for item in value.split(",") if item.strip()]
    findings: list[Finding] = []
    for entry in entries:
        if AGENT_SKILL_REF.match(entry) is None:
            findings.append(
                Finding("S6", rel, f"`skills` entry {entry!r} is not `<plugin>:<skill>`")
            )
        elif entry not in known_skills:
            findings.append(
                Finding(
                    "S6", rel, f"`skills` entry {entry!r} names no skill this marketplace ships"
                )
            )
    return findings


def read(path: Path) -> Frontmatter:
    """Read a Markdown file and parse its frontmatter.

    Args:
        path: The file to read.

    Returns:
        The parsed block.
    """
    return parse(path.read_text(encoding="utf-8"))
