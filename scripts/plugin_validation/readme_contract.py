"""The README contract: R1 to R14, over each plugin's README and the root catalog.

A plugin README is the only document a user reads before installing, so its structure is
enforced and its claims are cross-checked against the files: the derived kind, the
Compatibility table, the binaries the scripts invoke, the environment variables they read,
and the skills that exist on disk. What the structure cannot judge — whether a sentence is
true and worth reading — stays with `plugin-release-review`.

One rule is absolute and mechanical: R9, no eval scores in a README. Numbers there go stale
the moment a model changes, and a stale number is worse than none.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import TYPE_CHECKING, Final

from scripts.common.errors import Finding
from scripts.common.plugins import PLUGINS_DIRNAME, as_mapping, load_json
from scripts.plugin_validation.kind import Kind, derive_kind, plugin_dir, skill_names
from scripts.plugin_validation.runtime_boundary import invoked_binaries, ships_python
from scripts.plugin_validation.script_env import (
    SHARED_TEST_BASH,
    env_vars_for,
    suite_interpreter_vars,
)

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from pathlib import Path

REQUIRED_SECTIONS: Final[tuple[str, ...]] = (
    "🎯 What it does",
    "🚫 What it does not do",
    "⚡ Installation",
    "🧠 Skills",
    "🤖 Agents",
    "🪝 Hooks and side effects",
    "🔌 MCP, permissions, and network",
    "📋 Requirements",
    "✅ Verification",
    "🧭 Compatibility",
    "💡 Examples",
    "🔐 Security",
    "🚧 Limitations",
    "📝 Changelog",
    "📄 License",
)
"""The 15 sections every plugin README carries, in this order, with these exact headings."""

OTHER_COMPONENTS_SECTION: Final = "🧩 Other components"
"""Optional; allowed only when the plugin ships a component beyond skills and agents."""

FAQ_SECTION: Final = "❓ FAQ"
"""Optional; allowed anywhere after Limitations."""

OTHER_COMPONENT_PATHS: Final[tuple[str, ...]] = (
    "commands",
    "output-styles",
    "monitors",
    "workflows",
    ".mcp.json",
    ".lsp.json",
    "settings.json",
)
"""What makes an `Other components` section legitimate."""

BADGE: Final = re.compile(r"!\[(?P<alt>[^\]]*)\]\(https://img\.shields\.io/badge/(?P<slug>[^)]*)\)")
"""A shields.io badge in the row under the title."""

LEADING_BADGES: Final[tuple[str, ...]] = (
    "Version",
    "License: Apache-2.0",
    "Kind",
    "Claude Code",
    "Claude Cowork",
)
"""The badges every README opens with, in this order, before the requirement badges."""

KIND_BADGE_SLUG: Final = re.compile(r"^kind-(?P<kind>[a-z-]+)-")
"""The kind badge's payload, where a literal hyphen is written `--`."""

SURFACE_BADGE_SLUG: Final = re.compile(r"^Claude_(?P<surface>Code|Cowork)-(?P<status>[a-z_]+)-")
"""A surface badge's payload: the surface and the status slug it claims."""

NETWORK_BADGE_SLUG: Final = re.compile(r"^network-(?P<value>none|optional|required)-")
"""The network badge's payload."""

STATUS_SLUGS: Final[Mapping[str, str]] = {
    "✅": "supported",
    "⚠️": "partial",
    "🧪": "not_tested",
    "❌": "not_supported",
}
"""The status vocabulary, and the badge slug each status maps to."""

ISO_DATE: Final = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
"""A `Last verified` date."""

REMOTE_INSTALL: Final = re.compile(r"remote marketplace", re.IGNORECASE)
"""The evidence a ✅ needs: an install of the published marketplace, not a local checkout."""

SECONDARY_SURFACE: Final = re.compile(r"cloud", re.IGNORECASE)
"""A Claude Code row that names a deployment variant rather than a platform.

Such a row never decides the catalog status on its own; R14 collapses the platform rows.
"""

DELTA_COLUMN: Final = re.compile(r"\|\s*Δ\s*\|")
"""The eval delta column R9 forbids."""

EVAL_TABLE_HEADER: Final = re.compile(r"\|\s*Case\s*\|.*\|\s*With\s*\|", re.IGNORECASE)
"""An eval score table's header row, which R9 forbids in a README."""

EVAL_SENTENCE: Final = (
    "**Behavioral evals** — [`evals/`](evals/) run per the maintainer's eval protocol; results "
    "are reported in the pull request or a dated file under `docs/audits/`, never here"
)
"""What replaces an eval score table (§A10)."""

SKILL_COMMAND: Final = re.compile(r"`/(?P<plugin>[a-z0-9-]+):(?P<skill>[a-z0-9-]+)`")
"""A slash command naming a skill, as the Skills table writes it."""

NETWORK_MODULES: Final[frozenset[str]] = frozenset(
    {"http", "httpx", "requests", "socket", "ssl", "urllib"}
)
"""Standard-library and third-party modules whose presence means a script reaches the network."""

NETWORK_BINARIES: Final[frozenset[str]] = frozenset({"curl", "wget"})
"""Binaries whose presence means a script reaches the network."""

NETWORK_TOOLS: Final[frozenset[str]] = frozenset({"WebFetch", "WebSearch"})
"""Tool grants that reach the network."""

BINARY_ROW_LABELS: Final[Mapping[str, tuple[str, ...]]] = {
    "bash": ("bash",),
    "curl": ("curl",),
    "git": ("git",),
    "jq": ("jq",),
    "python3": ("python", "python3"),
    "ruff": ("ruff",),
    "shellcheck": ("shellcheck",),
    "shfmt": ("shfmt",),
    "node": ("node", "node.js"),
    "gh": ("gh", "github cli"),
    "make": ("make",),
    "docker": ("docker",),
}
"""How a binary's name appears in the first column of the Requirements table."""

COMPATIBILITY_CELLS: Final = 4
"""Cells a Compatibility row carries: surface, status, last verified, notes."""

REQUIREMENT_CELLS: Final = 3
"""Cells a Requirements row must carry before it can be read: label, minimum, check."""

CATALOG_CELLS: Final = 5
"""Cells a root catalog row carries: link, summary, kind, Claude Code, Cowork, requirements."""

GIT_BASH: Final = "Git Bash"
"""What a Windows user needs before a `bash` hook can run (R10)."""


@dataclass(frozen=True, slots=True)
class CompatibilityRow:
    """One row of the Compatibility table.

    Attributes:
        surface: The first cell, naming the surface and platform.
        status: The status emoji, or an empty string when the cell carries none.
        verified: The `Last verified` cell.
        notes: The remaining cell.
    """

    surface: str
    status: str
    verified: str
    notes: str


def sections(text: str) -> dict[str, list[str]]:
    """Split a README into its level-two sections.

    Args:
        text: The README's text.

    Returns:
        Heading text mapped to its lines; everything before the first heading is keyed
        with the empty string.
    """
    result: dict[str, list[str]] = {"": []}
    current = ""
    for line in text.splitlines():
        if line.startswith("## "):
            current = line[3:].strip()
            result[current] = []
            continue
        result[current].append(line)
    return result


def heading_order(text: str) -> list[str]:
    """List a README's level-two headings in order.

    Args:
        text: The README's text.

    Returns:
        The headings, without the `## ` prefix.
    """
    return [line[3:].strip() for line in text.splitlines() if line.startswith("## ")]


def table_rows(lines: Sequence[str]) -> list[list[str]]:
    """Read the body rows of every Markdown table in a section.

    Args:
        lines: The section's lines.

    Returns:
        One list of cells per row, with the header and separator rows removed.
    """
    rows: list[list[str]] = []
    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if all(set(cell) <= {"-", ":"} and cell for cell in cells):
            continue
        rows.append(cells)
    return rows


def check_sections(rel: str, text: str, *, has_other_components: bool) -> list[Finding]:
    """Check that the required sections are present, in order, and nothing extra (R1).

    Args:
        rel: The README's repository-relative path.
        text: The README's text.
        has_other_components: Whether the plugin ships a component that earns the
            optional `Other components` section.

    Returns:
        One finding per missing, reordered or unearned section.
    """
    headings = heading_order(text)
    findings: list[Finding] = [
        Finding("R1", rel, f"section {name!r} is missing")
        for name in REQUIRED_SECTIONS
        if name not in headings
    ]
    required_present = [name for name in headings if name in REQUIRED_SECTIONS]
    expected = [name for name in REQUIRED_SECTIONS if name in headings]
    if required_present != expected:
        findings.append(Finding("R1", rel, "the required sections are not in the template's order"))
    if OTHER_COMPONENTS_SECTION in headings and not has_other_components:
        findings.append(
            Finding(
                "R1", rel, f"{OTHER_COMPONENTS_SECTION!r} but the plugin ships no such component"
            )
        )
    unknown = [
        name
        for name in headings
        if name not in {*REQUIRED_SECTIONS, OTHER_COMPONENTS_SECTION, FAQ_SECTION}
    ]
    findings.extend(
        Finding("R1", rel, f"section {name!r} is not in the template") for name in unknown
    )
    return findings


def badges(text: str) -> list[tuple[str, str]]:
    """List the badges in the row under the title.

    Args:
        text: The README's text.

    Returns:
        Pairs of alt text and shields.io payload, in document order.
    """
    header = sections(text)[""]
    return [
        (match.group("alt"), match.group("slug"))
        for line in header
        for match in BADGE.finditer(line)
    ]


def compatibility_rows(text: str) -> list[CompatibilityRow]:
    """Read the Compatibility table.

    Args:
        text: The README's text.

    Returns:
        One record per body row, header row included only when it is not the column titles.
    """
    rows: list[CompatibilityRow] = []
    for cells in table_rows(sections(text).get("🧭 Compatibility", [])):
        if len(cells) < COMPATIBILITY_CELLS or cells[0] == "Surface":
            continue
        status = next((emoji for emoji in STATUS_SLUGS if emoji in cells[1]), "")
        rows.append(CompatibilityRow(cells[0], status, cells[2], cells[3]))
    return rows


def _platform_rows(rows: Sequence[CompatibilityRow], surface: str) -> list[CompatibilityRow]:
    """Select the rows that decide one surface's collapsed status.

    Args:
        rows: Every Compatibility row.
        surface: `Claude Code` or `Claude Cowork`.

    Returns:
        The rows naming that surface, minus deployment variants such as cloud sessions.
    """
    return [
        row
        for row in rows
        if row.surface.startswith(surface) and SECONDARY_SURFACE.search(row.surface) is None
    ]


def collapse(rows: Sequence[CompatibilityRow], surface: str) -> str:
    """Collapse a surface's platform rows into the one status the catalog carries (R14).

    Args:
        rows: Every Compatibility row.
        surface: `Claude Code` or `Claude Cowork`.

    Returns:
        A status emoji: ✅ only when every platform row is ✅ with a dated remote install,
        ⚠️ when the rows are mixed, 🧪 when none is ✅, and ❌ when every row is ❌.
    """
    selected = _platform_rows(rows, surface)
    if not selected:
        return ""
    statuses = [row.status for row in selected]
    if all(status == "❌" for status in statuses):
        return "❌"
    supported = [row for row in selected if row.status == "✅"]
    dated = [
        row
        for row in supported
        if ISO_DATE.search(row.verified) and REMOTE_INSTALL.search(row.notes)
    ]
    if supported and len(dated) == len([status for status in statuses if status != "❌"]):
        return "✅"
    if supported or "⚠️" in statuses:
        return "⚠️"
    return "🧪"


def check_badges(root: Path, plugin_id: str, rel: str, text: str) -> list[Finding]:
    """Check the badge row's order, the kind slug and the surface statuses (R2).

    Args:
        root: The repository root.
        plugin_id: The plugin directory name.
        rel: The README's repository-relative path.
        text: The README's text.

    Returns:
        One finding per rule broken.
    """
    found = badges(text)
    leading = [alt for alt, _ in found[: len(LEADING_BADGES)]]
    findings: list[Finding] = []
    if leading != list(LEADING_BADGES):
        findings.append(
            Finding("R2", rel, f"the badge row opens with {leading}, not {list(LEADING_BADGES)}")
        )
    findings.extend(_kind_badge_findings(root, plugin_id, rel, found))
    findings.extend(_surface_badge_findings(rel, found, compatibility_rows(text)))
    return findings


def _kind_badge_findings(
    root: Path, plugin_id: str, rel: str, found: Sequence[tuple[str, str]]
) -> list[Finding]:
    """Check that the kind badge shows the kind the files derive (R2).

    Args:
        root: The repository root.
        plugin_id: The plugin directory name.
        rel: The README's repository-relative path.
        found: The badges read from the row.

    Returns:
        One finding when the badge is absent or shows another kind.
    """
    derived = derive_kind(root, plugin_id)
    slug = next((payload for alt, payload in found if alt == "Kind"), None)
    if slug is None:
        return [Finding("R2", rel, "no `Kind` badge")]
    match = KIND_BADGE_SLUG.match(slug)
    if match is None:
        return [Finding("R2", rel, "the `Kind` badge payload is not `kind-<kind>-<colour>`")]
    shown = match.group("kind").replace("--", "-")
    if derived is not None and shown != derived.value:
        return [
            Finding(
                "R2", rel, f"the `Kind` badge says {shown!r} but the files derive {derived.value!r}"
            )
        ]
    return []


def _surface_badge_findings(
    rel: str, found: Sequence[tuple[str, str]], rows: Sequence[CompatibilityRow]
) -> list[Finding]:
    """Check that each surface badge shows the collapsed Compatibility status (R2).

    Args:
        rel: The README's repository-relative path.
        found: The badges read from the row.
        rows: The Compatibility rows.

    Returns:
        One finding per surface whose badge and table disagree.
    """
    findings: list[Finding] = []
    for alt, payload in found:
        match = SURFACE_BADGE_SLUG.match(payload)
        if match is None:
            continue
        surface = f"Claude {match.group('surface')}"
        expected = STATUS_SLUGS.get(collapse(rows, surface))
        if expected is not None and match.group("status") != expected:
            findings.append(
                Finding(
                    "R2",
                    rel,
                    (
                        f"the {alt} badge says {match.group('status')!r};"
                        f" the table collapses to {expected!r}"
                    ),
                )
            )
    return findings


def check_last_verified(rel: str, text: str) -> list[Finding]:
    """Check that every ✅ row carries a dated `Last verified` (R3).

    Args:
        rel: The README's repository-relative path.
        text: The README's text.

    Returns:
        One finding per ✅ row without a `YYYY-MM-DD` date.
    """
    return [
        Finding("R3", rel, f"{row.surface!r} is ✅ but `Last verified` carries no YYYY-MM-DD date")
        for row in compatibility_rows(text)
        if row.status == "✅" and ISO_DATE.search(row.verified) is None
    ]


def uses_network(root: Path, plugin_id: str, grants: Sequence[str], modules: Sequence[str]) -> bool:
    """Report whether anything the plugin ships reaches the network.

    Args:
        root: The repository root.
        plugin_id: The plugin directory name.
        grants: The tool names its skills and agents grant.
        modules: The modules its shipped Python imports.

    Returns:
        True when a network binary, module or tool grant is present.
    """
    if invoked_binaries(root, plugin_id) & NETWORK_BINARIES:
        return True
    if set(modules) & NETWORK_MODULES:
        return True
    return bool(set(grants) & NETWORK_TOOLS)


def check_network_badge(rel: str, text: str, *, networked: bool) -> list[Finding]:
    """Check that the network badge is present and honest (R4).

    Args:
        rel: The README's repository-relative path.
        text: The README's text.
        networked: Whether the shipped files reach the network.

    Returns:
        One finding when the badge is absent, or claims `none` for a plugin that does.
    """
    value = next(
        (
            match.group("value")
            for _, payload in badges(text)
            for match in [NETWORK_BADGE_SLUG.match(payload)]
            if match
        ),
        None,
    )
    if value is None:
        return [Finding("R4", rel, "no `network` badge")]
    if value == "none" and networked:
        return [
            Finding(
                "R4", rel, "the network badge says `none` but a shipped file reaches the network"
            )
        ]
    return []


def requirement_rows(text: str) -> list[list[str]]:
    """Read the Requirements table's body rows.

    Args:
        text: The README's text.

    Returns:
        One list of cells per row, the column titles removed.
    """
    return [
        cells
        for cells in table_rows(sections(text).get("📋 Requirements", []))
        if len(cells) >= REQUIREMENT_CELLS and cells[0] != "Requirement"
    ]


def _requirement_index(text: str) -> dict[str, list[str]]:
    """Index the Requirements table by its lower-cased first cell.

    Args:
        text: The README's text.

    Returns:
        The label mapped to the row's cells.
    """
    return {cells[0].strip("`").strip().lower(): cells for cells in requirement_rows(text)}


def check_requirements(root: Path, plugin_id: str, rel: str, text: str) -> list[Finding]:
    """Check that every invoked binary has a complete Requirements row (R5).

    Args:
        root: The repository root.
        plugin_id: The plugin directory name.
        rel: The README's repository-relative path.
        text: The README's text.

    Returns:
        One finding per binary with no row, a row with no minimum or no check command, or
        no symptom named under Limitations; and one when a `.py` ships with no Python row.
    """
    index = _requirement_index(text)
    findings: list[Finding] = []
    for binary in sorted(invoked_binaries(root, plugin_id)):
        findings.extend(_requirement_findings(rel, text, binary, index))
    if ships_python(root, plugin_id) and not any(label.startswith("python") for label in index):
        findings.append(
            Finding(
                "R5", rel, "the plugin ships Python but the Requirements table has no Python row"
            )
        )
    return findings


def _requirement_findings(
    rel: str, text: str, binary: str, index: Mapping[str, list[str]]
) -> list[Finding]:
    """Check one binary's Requirements row and its symptom line.

    Args:
        rel: The README's repository-relative path.
        text: The README's text.
        binary: The binary the shipped files invoke.
        index: The Requirements table, indexed by label.

    Returns:
        One finding per rule broken.
    """
    labels = BINARY_ROW_LABELS.get(binary, (binary,))
    cells = next((index[label] for label in labels if label in index), None)
    if cells is None:
        return [Finding("R5", rel, f"{binary!r} is invoked but has no Requirements row")]
    findings: list[Finding] = []
    if not cells[1] or cells[1] == "—":
        findings.append(
            Finding("R5", rel, f"the Requirements row for {binary!r} names no minimum version")
        )
    if "`" not in cells[2]:
        findings.append(
            Finding("R5", rel, f"the Requirements row for {binary!r} names no check command")
        )
    symptoms = "\n".join(
        sections(text).get("🚧 Limitations", []) + sections(text).get(FAQ_SECTION, [])
    )
    if binary not in symptoms.lower() and binary not in symptoms:
        findings.append(
            Finding("R5", rel, f"no Limitations row names the symptom of a missing {binary!r}")
        )
    return findings


def check_env_vars(root: Path, rel: str, text: str, scripts: Sequence[str]) -> list[Finding]:
    """Check that the README names every environment variable the scripts read (R6).

    Args:
        root: The repository root.
        rel: The README's repository-relative path.
        text: The README's text.
        scripts: The plugin's shipped scripts, repository-relative.

    Returns:
        One finding per variable the scripts read and the README never names, and one when
        a suite honours the shared fallback without the README documenting it.
    """
    names: set[str] = set()
    for script in scripts:
        names |= env_vars_for(root / script)
    findings = [
        Finding("R6", rel, f"scripts read `{name}` but the README never names it")
        for name in sorted(names)
        if name not in text
    ]
    suite_vars = suite_interpreter_vars(names)
    documented = {name for name in suite_vars if name in text}
    findings.extend(
        Finding("R6", rel, f"`{name}` is documented but no shipped suite reads it")
        for name in sorted(suite_interpreter_vars(_backticked(text)) - suite_vars)
    )
    if SHARED_TEST_BASH in names and SHARED_TEST_BASH not in documented:
        findings.append(
            Finding(
                "R6", rel, f"a suite honours `{SHARED_TEST_BASH}` but the README never names it"
            )
        )
    return findings


def _backticked(text: str) -> set[str]:
    """List the upper-case words the README writes in backticks.

    Args:
        text: The README's text.

    Returns:
        The words, which is where a documented variable name appears.
    """
    return set(re.findall(r"`([A-Z][A-Z0-9_]*)`", text))


def check_no_eval_scores(rel: str, text: str) -> list[Finding]:
    """Check that the README carries no eval score table and no delta column (R9).

    Args:
        rel: The README's repository-relative path.
        text: The README's text.

    Returns:
        One finding per offending table, naming the sentence that replaces it.
    """
    findings: list[Finding] = []
    if DELTA_COLUMN.search(text) is not None:
        findings.append(
            Finding(
                "R9", rel, f"an eval table carries a `Δ` column; replace it with: {EVAL_SENTENCE}"
            )
        )
    if EVAL_TABLE_HEADER.search(text) is not None:
        findings.append(
            Finding(
                "R9", rel, f"an eval score table is in the README; replace it with: {EVAL_SENTENCE}"
            )
        )
    return findings


def check_windows_rule(rel: str, text: str, *, runs_bash: bool) -> list[Finding]:
    """Check the Windows rule for a plugin whose hooks run `bash` (R10).

    Args:
        rel: The README's repository-relative path.
        text: The README's text.
        runs_bash: Whether a hook command or fragment runs `bash`.

    Returns:
        One finding when the README never names Git Bash, and one per Compatibility row
        that names Windows without Git Bash and is not marked ❌.
    """
    if not runs_bash:
        return []
    findings: list[Finding] = []
    if GIT_BASH not in text:
        findings.append(Finding("R10", rel, "hooks run `bash` but the README never names Git Bash"))
    findings.extend(
        Finding("R10", rel, f"{row.surface!r} is {row.status or 'unmarked'}, not ❌")
        for row in compatibility_rows(text)
        if "without Git Bash" in row.surface and row.status != "❌"
    )
    return findings


def check_skill_commands(root: Path, plugin_id: str, rel: str, text: str) -> list[Finding]:
    """Check that every slash command in the Skills table resolves on disk (R11).

    Args:
        root: The repository root.
        plugin_id: The plugin directory name.
        rel: The README's repository-relative path.
        text: The README's text.

    Returns:
        One finding per command naming a skill that does not exist.
    """
    known = set(skill_names(root, plugin_id))
    lines = "\n".join(sections(text).get("🧠 Skills", []))
    return [
        Finding(
            "R11", rel, f"`/{match.group('plugin')}:{match.group('skill')}` names no shipped skill"
        )
        for match in SKILL_COMMAND.finditer(lines)
        if match.group("plugin") != plugin_id or match.group("skill") not in known
    ]


def check_cowork_claim(rel: str, text: str, compatibility_fields: Sequence[str]) -> list[Finding]:
    """Check the Cowork badge against what the shipped skills declare (R13).

    Args:
        rel: The README's repository-relative path.
        text: The README's text.
        compatibility_fields: The `compatibility:` values of the plugin's skills.

    Returns:
        One finding when a badge claims Cowork support that a skill contradicts.
    """
    claimed = next(
        (
            match.group("status")
            for _, payload in badges(text)
            for match in [SURFACE_BADGE_SLUG.match(payload)]
            if match and match.group("surface") == "Cowork"
        ),
        None,
    )
    if claimed != "supported":
        return []
    denied = [field for field in compatibility_fields if "Not supported in Claude Cowork" in field]
    if not denied:
        return []
    return [
        Finding(
            "R13", rel, "the Cowork badge says `supported` while a shipped skill says it is not"
        )
    ]


def manifest(root: Path, plugin_id: str) -> dict[str, object]:
    """Read a plugin's manifest.

    Args:
        root: The repository root.
        plugin_id: The plugin directory name.

    Returns:
        The parsed manifest.
    """
    path = plugin_dir(root, plugin_id) / ".claude-plugin" / "plugin.json"
    return as_mapping(load_json(path), path=path)


def catalog_rows(readme: str) -> dict[str, list[str]]:
    """Read the root README's plugin catalog, keyed by plugin id.

    Args:
        readme: The root README's text.

    Returns:
        The row cells for each `plugins/<id>/README.md` link found.
    """
    rows: dict[str, list[str]] = {}
    for line in readme.splitlines():
        stripped = line.strip()
        if not stripped.startswith("| ["):
            continue
        match = re.search(r"\]\(plugins/(?P<id>[a-z0-9-]+)/README\.md\)", stripped)
        if match is None:
            continue
        rows[match.group("id")] = [cell.strip() for cell in stripped.strip("|").split("|")]
    return rows


def check_catalog(root: Path, readme: str, plugin_ids_: Sequence[str]) -> list[Finding]:
    """Check the root README's catalog against the plugins on disk (R8 and R14).

    Args:
        root: The repository root.
        readme: The root README's text.
        plugin_ids_: The plugin directory names.

    Returns:
        One finding per missing row, wrong link text, wrong kind, wrong status, and one
        when the rows are not sorted.
    """
    rows = catalog_rows(readme)
    findings: list[Finding] = [
        Finding("R8", "README.md", f"{plugin_id!r} has no catalog row")
        for plugin_id in plugin_ids_
        if plugin_id not in rows
    ]
    listed = list(rows)
    if listed != sorted(listed):
        findings.append(Finding("R8", "README.md", "the catalog rows are not sorted by plugin id"))
    for plugin_id in plugin_ids_:
        cells = rows.get(plugin_id)
        if cells is not None:
            findings.extend(_catalog_row_findings(root, plugin_id, cells))
    return findings


def _catalog_row_findings(root: Path, plugin_id: str, cells: Sequence[str]) -> list[Finding]:
    """Check one catalog row against the plugin's manifest and README (R8 and R14).

    Args:
        root: The repository root.
        plugin_id: The plugin directory name.
        cells: The row's cells.

    Returns:
        One finding per mismatch.
    """
    minimum_cells = 5
    if len(cells) < minimum_cells:
        return [
            Finding(
                "R8", "README.md", f"the row for {plugin_id!r} has fewer than {minimum_cells} cells"
            )
        ]
    findings: list[Finding] = []
    display = manifest(root, plugin_id).get("displayName")
    link_text = cells[0].split("]", 1)[0].lstrip("[")
    if isinstance(display, str) and link_text != display:
        findings.append(
            Finding(
                "R8",
                "README.md",
                f"the row for {plugin_id!r} links as {link_text!r}, not {display!r}",
            )
        )
    derived = derive_kind(root, plugin_id)
    if derived is not None and cells[2].strip("`") != derived.value:
        findings.append(
            Finding(
                "R8",
                "README.md",
                f"the row for {plugin_id!r} says kind {cells[2]}, not `{derived.value}`",
            )
        )
    readme = (plugin_dir(root, plugin_id) / "README.md").read_text(encoding="utf-8")
    rows = compatibility_rows(readme)
    for index, surface in ((3, "Claude Code"), (4, "Claude Cowork")):
        expected = collapse(rows, surface)
        if expected and expected not in cells[index]:
            findings.append(
                Finding(
                    "R14",
                    "README.md",
                    (
                        f"the row for {plugin_id!r} shows {cells[index]!r} for"
                        f" {surface}, not {expected}"
                    ),
                )
            )
    return findings


def has_other_components(root: Path, plugin_id: str) -> bool:
    """Report whether a plugin earns the optional `Other components` section.

    Args:
        root: The repository root.
        plugin_id: The plugin directory name.

    Returns:
        True when one of the component paths exists.
    """
    base = plugin_dir(root, plugin_id)
    return any((base / name).exists() for name in OTHER_COMPONENT_PATHS)


def kind_of(root: Path, plugin_id: str) -> Kind | None:
    """Return a plugin's derived kind.

    Args:
        root: The repository root.
        plugin_id: The plugin directory name.

    Returns:
        The kind, or None when the directory ships no component.
    """
    return derive_kind(root, plugin_id)


def readme_rel(plugin_id: str) -> str:
    """Return a plugin README's repository-relative path.

    Args:
        plugin_id: The plugin directory name.

    Returns:
        The path.
    """
    return f"{PLUGINS_DIRNAME}/{plugin_id}/README.md"


TEMPLATE_MASTER: Final = "templates/plugin-README-reusable-template.md"
"""The master copy the three shape templates are pre-filled instances of."""

TEMPLATE_SHAPES: Final[Mapping[str, str]] = {
    "templates/plugin-bundle/README.md": "bundle",
    "templates/plugin-skill-only/README.md": "skill-only",
    "templates/plugin-agent-only/README.md": "agent-only",
}
"""The three shapes and the kind each one is filled in for."""

KIND_SPECIFIC_SECTIONS: Final[frozenset[str]] = frozenset(
    {
        "",
        "🧠 Skills",
        "🤖 Agents",
        "🪝 Hooks and side effects",
        "🔌 MCP, permissions, and network",
        OTHER_COMPONENTS_SECTION,
        "✅ Verification",
    }
)
"""Where a shape may differ from the master: the badge row and the component sections.

Everything else — Installation, Requirements, Compatibility, Examples, Security,
Limitations, Changelog, License — is shared text, and R7 fails when a shape drifts there.
"""

COMMENT_END: Final = "-->\n"
"""The end of the instruction comment a template opens with."""

LEGAL_DOCUMENTS: Final[Mapping[str, str]] = {
    "SECURITY.md": "templates/SECURITY-reusable-template.md",
    "CODE_OF_CONDUCT.md": "templates/CODE_OF_CONDUCT-reusable-template.md",
}
"""The two documents R12 holds to their templates outside the placeholder lines."""

PLACEHOLDER: Final = re.compile(r"\{\{[^{}]*\}\}")
"""An innermost placeholder; it is removed repeatedly so a nested one disappears too."""

SENTENCE_BREAK: Final = re.compile(r"(?<=[.:]) (?=[A-Z-])|(?= - )")
"""Where a required stretch of wording is cut, so one re-worded bullet is one finding."""

HTML_COMMENT: Final = re.compile(r"<!--.*?-->", re.DOTALL)
"""An instruction comment, which the copy deletes and R12 therefore removes first."""

OPTIONAL_MARKER: Final = "<!-- Optional"
"""How a template marks a section a copy may drop entirely."""

OPTIONAL_LOOKBACK: Final = 6
"""Lines before a heading that an `<!-- Optional` comment may sit in and still mark it.

A template introduces an optional section with a comment above its heading, so the marker
belongs to the heading that follows rather than to the section it was written after.
"""

MIN_SEGMENT: Final = 40
"""Characters a fixed segment needs before R12 requires the copy to carry it.

Shorter fragments are punctuation and list bullets that survive any rewrap; comparing them
would report a difference wherever a line was re-wrapped after a placeholder was filled in.
"""


def template_body(path: Path) -> str:
    """Return a template's text with its leading instruction comment removed.

    Args:
        path: The template file.

    Returns:
        The body, starting at the first line after the comment.
    """
    text = path.read_text(encoding="utf-8")
    if not text.startswith("<!--"):
        return text
    return text.split(COMMENT_END, 1)[1].lstrip("\n")


def check_template_shapes(root: Path) -> list[Finding]:
    """Check that each shape template differs from the master only where it may (R7).

    Args:
        root: The repository root.

    Returns:
        One finding per shape whose headings drift, and one per shared line it changed.
    """
    master = sections(template_body(root / TEMPLATE_MASTER))
    findings: list[Finding] = []
    for rel, shape in TEMPLATE_SHAPES.items():
        body = template_body(root / rel)
        findings.extend(_shape_findings(rel, shape, master, sections(body)))
    return findings


def _shape_findings(
    rel: str, shape: str, master: Mapping[str, list[str]], filled: Mapping[str, list[str]]
) -> list[Finding]:
    """Compare one shape template with the master.

    Args:
        rel: The shape template's repository-relative path.
        shape: The kind the shape is filled in for.
        master: The master's sections.
        filled: The shape's sections.

    Returns:
        One finding per missing required section and per shared line that drifted.
    """
    findings: list[Finding] = []
    for name, lines in master.items():
        if name in KIND_SPECIFIC_SECTIONS:
            continue
        if name not in filled:
            findings.append(Finding("R7", rel, f"the {shape} shape drops section {name!r}"))
            continue
        missing = [line for line in lines if line.strip() and line not in filled[name]]
        findings.extend(
            Finding("R7", rel, f"section {name!r} differs from the master: {line.strip()[:60]!r}")
            for line in missing
        )
    return findings


def _headings(text: str) -> list[str]:
    """List a document's level-two headings in order.

    Args:
        text: The document.

    Returns:
        The headings, without the `## ` prefix.
    """
    return heading_order(text)


def required_headings(template: str) -> list[str]:
    """List the sections a copy of a template has to keep.

    A section the template marks `<!-- Optional` may be dropped, so it is left out.

    Args:
        template: The template's body.

    Returns:
        The headings, in order.
    """
    blocks = sections(template)
    lines = template.splitlines()
    required: list[str] = []
    for index, line in enumerate(lines):
        if not line.startswith("## "):
            continue
        name = line[3:].strip()
        preceding = lines[max(index - OPTIONAL_LOOKBACK, 0) : index]
        body = "\n".join([*preceding, *blocks.get(name, [])])
        if OPTIONAL_MARKER in body or PLACEHOLDER.search(name) is not None:
            continue
        required.append(name)
    return required


def check_legal_texts(root: Path) -> list[Finding]:
    """Check the repository's legal documents against their templates (R12).

    What is checked here is structure: every section the template requires is present, in
    the template's order, and no placeholder survived the copy. The verbatim wording is
    deliberately not compared here — a filled-in placeholder re-wraps the paragraph around
    it, so a line-by-line comparison reports differences that are not drift. X5
    (`scripts/hygiene/test_legal_text.py`, step 6) owns the verbatim check, which keeps one
    home per rule (X1).

    Args:
        root: The repository root.

    Returns:
        One finding per missing or reordered section, and one per surviving placeholder.
    """
    findings: list[Finding] = []
    for rel, template in LEGAL_DOCUMENTS.items():
        text = (root / rel).read_text(encoding="utf-8")
        wanted = required_headings(template_body(root / template))
        present = [name for name in _headings(text) if name in wanted]
        findings.extend(
            Finding("R12", rel, f"section {name!r} of `{template}` is missing")
            for name in wanted
            if name not in present
        )
        if present != [name for name in wanted if name in present]:
            findings.append(Finding("R12", rel, f"the sections are not in `{template}`'s order"))
        if PLACEHOLDER.search(HTML_COMMENT.sub("", text)) is not None:
            findings.append(Finding("R12", rel, "a template placeholder survived the copy"))
    return findings
