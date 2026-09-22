"""What the official CLI already checks, and the tool names this repository knows about.

Two dated constants live here, both read from the live documentation on `DOCS_DATE` and
both deliberately kept in one place so a refresh is a single edit (P1):

* `KNOWN_TOOLS` — the built-in tool names a hook matcher or an `allowed-tools` grant can
  name. An unknown name is a **warning**, never an error: upstream adds tools between
  refreshes, and a gate that fails on a tool that exists would be worse than one that
  reports a name it has not heard of.
* `CLI_PROBE_MATRIX` — which defects `claude plugin validate --strict` catches on its own.
  It is the justification for every repository invariant that overlaps the CLI (P6): a row
  marked `caught=False` is why the matching ID exists here.

The `coverage_matrix` pytest marker reserves the diff against the live documentation for
the nightly job, so a laptop run of `make test-fast` never depends on a fetched page.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

DOCS_DATE: Final = "2026-09-21"
"""The day the constants below were read from the live documentation."""

DOCS_SOURCES: Final[tuple[str, ...]] = (
    "https://code.claude.com/docs/en/sub-agents#available-tools",
    "https://code.claude.com/docs/en/hooks#matcher-patterns",
    "https://code.claude.com/docs/en/plugins-reference",
)
"""The pages `KNOWN_TOOLS` was read from on `DOCS_DATE`."""

MCP_TOOL_PREFIX: Final = "mcp__"
"""Every tool from an MCP server carries this prefix; such names are always accepted."""

KNOWN_TOOLS: Final[frozenset[str]] = frozenset(
    {
        "Agent",
        "Artifact",
        "AskUserQuestion",
        "Bash",
        "CronCreate",
        "CronDelete",
        "CronList",
        "Edit",
        "EndConversation",
        "EnterPlanMode",
        "EnterWorktree",
        "ExitPlanMode",
        "ExitWorktree",
        "Glob",
        "Grep",
        "ListAgents",
        "Monitor",
        "NotebookEdit",
        "PowerShell",
        "Read",
        "ScheduleWakeup",
        "SendMessage",
        "Skill",
        "SubagentHandback",
        "Task",
        "TaskCreate",
        "TaskGet",
        "TaskList",
        "TaskOutput",
        "TaskStop",
        "TaskUpdate",
        "TodoWrite",
        "ToolSearch",
        "WaitForMcpServers",
        "WebFetch",
        "WebSearch",
        "Workflow",
        "Write",
    }
)
"""Built-in tool names the documentation listed on `DOCS_DATE`.

`Task` is the pre-2.1.63 name of `Agent` and still resolves, so it is listed too.
"""


@dataclass(frozen=True, slots=True)
class CliProbe:
    """One defect, and whether the official CLI refuses it on its own.

    Attributes:
        defect: The seeded defect, phrased as it would appear in a plugin.
        caught: Whether `claude plugin validate --strict` refuses it.
        invariant_id: The repository invariant that covers it, or None when the CLI does.
        source: Where the observation is recorded.
    """

    defect: str
    caught: bool
    invariant_id: str | None
    source: str


PROBE_SOURCE: Final = "consolidated governance refactor plan, 2026-09-21 (§A6 defect column)"
"""Where the rows below come from.

`docs/audits/2026-09-20-cli-validation-coverage.md` does not exist in this working tree, so
the matrix records the plan's own measurements rather than a re-measurement made here. The
nightly `coverage_matrix` job is where a fresh probe belongs.
"""

CLI_PROBE_MATRIX: Final[tuple[CliProbe, ...]] = (
    CliProbe('manifest `version` of "1.0"', caught=False, invariant_id="M5", source=PROBE_SOURCE),
    CliProbe(
        "hook `command` present but empty", caught=False, invariant_id="H4", source=PROBE_SOURCE
    ),
    CliProbe("hook `command` key absent", caught=True, invariant_id=None, source=PROBE_SOURCE),
    CliProbe(
        "regex matcher that cannot compile", caught=False, invariant_id="H2", source=PROBE_SOURCE
    ),
    CliProbe(
        "`${CLAUDE_PLUGIN_ROOT}` path that does not exist",
        caught=False,
        invariant_id="H5",
        source=PROBE_SOURCE,
    ),
    CliProbe(
        "`timeout` above the event's documented default",
        caught=False,
        invariant_id="H6",
        source=PROBE_SOURCE,
    ),
    CliProbe(
        "manifest `name` different from the directory name",
        caught=False,
        invariant_id="M1",
        source=PROBE_SOURCE,
    ),
    CliProbe("unrecognized manifest field", caught=True, invariant_id=None, source=PROBE_SOURCE),
)
"""Why each overlapping invariant exists (P14); a `caught=True` row is left to the CLI."""


def is_known_tool(name: str) -> bool:
    """Report whether a tool name is one the documentation listed, or an MCP tool.

    Args:
        name: The tool name exactly as the manifest or grant spells it.

    Returns:
        True for a documented built-in name and for any `mcp__…` name.
    """
    return name in KNOWN_TOOLS or name.startswith(MCP_TOOL_PREFIX)


def unknown_tools(names: frozenset[str]) -> list[str]:
    """List the names that are neither documented built-ins nor MCP tools.

    Args:
        names: Candidate tool names.

    Returns:
        The unknown names, sorted.
    """
    return sorted(name for name in names if not is_known_tool(name))
