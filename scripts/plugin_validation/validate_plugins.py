"""`make validate`, second half: every invariant this repository adds to the official CLI.

The registry below is the specification. `--list` prints it, every message starts with its
ID, and each row names the defect it catches (P14), so gate output can be looked up without
reading any of this code.

Three families are listed but not run here, each for a stated reason and each naming the
command or the file that does run it: `L1`-`L6` belong to `make lint`, `T1` is a test over
`templates/`, and `Q1`-`Q3` and `X1`-`X5` are the repository-hygiene tests under
`scripts/hygiene/`. Listing them keeps one registry rather than four, which is what a
maintainer reading an ID out of gate output needs.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import TYPE_CHECKING, Final

from scripts.common.errors import (
    ExitCode,
    Finding,
    MaintainerError,
    MissingPathError,
    format_finding,
)
from scripts.common.plugins import plugin_ids, repo_root, tracked_files
from scripts.github import labels
from scripts.github.issue_forms import validate_forms
from scripts.github.repo_metadata import collect as repo_metadata_collect
from scripts.lint.lint_files import LINT_INVARIANTS
from scripts.marketplace.validate_marketplace import (
    MARKETPLACE_INVARIANTS,
    collect as marketplace_collect,
)
from scripts.plugin_validation import (
    evals,
    frontmatter,
    hook_contract,
    kind,
    readme_contract,
    runtime_boundary as boundary,
    workflows as workflow_checks,
)
from scripts.versioning.changelog import (
    check_entry,
    check_links,
    check_released_bodies,
    read_changelog,
)
from scripts.versioning.version_plan import (
    VERSIONING_INVARIANTS,
    plugin_tags,
    predecessors,
    read_renames,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

PLUGIN_INVARIANTS: Final[tuple[tuple[str, str, str], ...]] = (
    ("P1", "the kind the files derive equals the README `**Kind:**` line", "ADR-0001 drift"),
    ("P2", "`LICENSE` is byte-equal to the Apache-2.0 template", "SPDX detection"),
    (
        "P3",
        "`CHANGELOG.md` has a dated section for the manifest version",
        "a release with no notes",
    ),
    ("P4", "no `{{placeholder}}` survives in a shipped file", "template leftovers"),
    ("P5", "no top-level `bin/` in a plugin", "an undeclared runtime"),
    ("C1", "CHANGELOG footer links use one style, `tree/` then `compare/`", "mixed link styles"),
    ("C2", "a released section still reads as it did at its tag", "DEBT-0009: rewritten history"),
    (
        "S1",
        "frontmatter starts on line 1 and parses as YAML",
        "DEBT-0022: a skill that never loads",
    ),
    ("S2", "frontmatter keys are documented (warning)", "upstream additions"),
    (
        "S3",
        "`description` plus `when_to_use`: present, under the cap, imperative",
        "truncated listings",
    ),
    ("S4", "`allowed-tools` entries parse and name a tool (unknown: warning)", "inert grants"),
    ("S5", "an agent `name` has no `:` and a `description` is present", "a load failure"),
    ("S6", "an agent's `skills:` entries resolve on disk", "dangling references"),
    ("H1", "`hooks.json` parses; events and handler types are documented", "shape drift"),
    ("H2", "every regex matcher compiles under V8 and matches a tool", "`Write|Edit[`"),
    ("H3", "every exact matcher names a known tool (warning)", "a typo that fires nothing"),
    ("H4", "a `command` is present and non-empty", "the CLI catches absent, not empty"),
    ("H5", "a `${CLAUDE_PLUGIN_ROOT}` path exists, is executable, has a shebang", "a dead handler"),
    ("H6", "`timeout` is numeric and within the event's documented default", "a silent cancel"),
    (
        "R1",
        "the template's sections, in order, optional ones only when earned",
        "a README that hides a limit",
    ),
    (
        "R2",
        "badge order, kind slug and surface statuses match the files",
        "a badge that outranks the table",
    ),
    ("R3", "a ✅ row carries a dated `Last verified`", "an unproven claim"),
    (
        "R4",
        "the network badge is present and not `none` for a networked plugin",
        "an undisclosed request",
    ),
    (
        "R5",
        "every invoked binary has a Requirements row and a symptom line",
        "a plugin that never fires",
    ),
    ("R6", "every environment variable the scripts read is named", "an undiscoverable knob"),
    ("R7", "each shape template differs from the master only where it may", "template rot"),
    (
        "R8",
        "the root catalog lists every plugin, sorted, with its display name",
        "a stale catalog row",
    ),
    ("R9", "no eval score table and no `Δ` column", "numbers that go stale silently"),
    (
        "R10",
        "a plugin whose hooks run `bash` marks Windows without Git Bash ❌",
        "a silent no-op on Windows",
    ),
    ("R11", "every `/<id>:<skill>` in the Skills table exists", "a dead slash command"),
    (
        "R12",
        "`SECURITY.md` and `CODE_OF_CONDUCT.md` keep their templates' sections",
        "policy drift",
    ),
    ("R13", "the Cowork badge does not outrank a skill's `compatibility`", "a contradicted claim"),
    ("R14", "each catalog status is the collapse of the Compatibility rows", "ambiguous statuses"),
    (
        "B1",
        "shebangs, commands, grants and imports stay inside the runtime boundary",
        "a plugin that assumes uv",
    ),
    (
        "W1",
        "a workflow's `meta` is literal, its phases declared, its body runs",
        "a workflow that throws",
    ),
    ("E1", "a suite has a README, three cases and one must-not-fire case", "a vanity suite"),
    ("E2", "every case has a prompt and at least one grader", "a case that cannot fail"),
    ("E3", "`results/` is git-ignored and never tracked", "run output in the repository"),
    (
        "E4",
        "the suite README names the plugin and states the CI policy",
        "a suite that claims to gate",
    ),
)
"""Every invariant this module runs, plus the two it hands to other modules (P3, C1, C2)."""

DEFERRED_INVARIANTS: Final[tuple[tuple[str, str, str], ...]] = (
    ("T1", "`templates/**` pass R and S with `{{…}}` tolerated", "template rot"),
    ("Q1", "the quality floor: no per-file config, no downgraded rule", "a seeded `extend-ignore`"),
    ("Q2", "the rigor floor: the repo policy is at least the global one", "global drift"),
    ("Q3", "no suppressions in code files", "a silenced finding"),
    ("X1", "one home per canonical table", "duplicated policy"),
    ("X2", "vendored schemas are SHA-256 pinned", "a silent edit"),
    ("X3", "accepted ADRs are append-only", "rewritten history"),
    ("X4", "no stale Node tooling references", "documentation that names a deleted tool"),
    (
        "X5",
        "LICENSE, CODE_OF_CONDUCT and SECURITY are verbatim to their templates",
        "license detection",
    ),
)
"""Listed for lookup, run elsewhere: T1 is `test_templates.py`; Q and X arrive at step 6."""

GITHUB_INVARIANTS: Final[tuple[tuple[str, str, str], ...]] = (
    ("G1", "`labels.json` shape, required labels and the generated dropdown", "taxonomy drift"),
    ("G2", "`uses:` pinned to a SHA, `CLAUDE_CODE_VERSION` equal, `make` invoked", "DEBT-0004"),
    ("G3", "tool pins agree across the lock, the floors and the workflows", "a silent mismatch"),
)
"""The repository-metadata invariants, run through `scripts.github.repo_metadata`."""

TEST_NOTE: Final = "(scripts/plugin_validation/test_templates.py)"
"""How `--list` marks T1: the test that runs it."""

HYGIENE_TESTS: Final[dict[str, str]] = {
    "Q1": "scripts/hygiene/test_quality_floor.py",
    "Q2": "scripts/hygiene/test_rigor_floor.py",
    "Q3": "scripts/hygiene/test_suppressions.py",
    "X1": "scripts/hygiene/test_single_home.py",
    "X2": "scripts/hygiene/test_vendored_files.py",
    "X3": "scripts/hygiene/test_adr_append_only.py",
    "X4": "scripts/hygiene/test_tooling_alignment.py",
    "X5": "scripts/hygiene/test_legal_text.py",
}
"""Which test runs each hygiene invariant, so `--list` names the file rather than a step."""

LINT_NOTE: Final = "(make lint)"
"""How `--list` marks the byte-level IDs, which `scripts.lint.lint_files` owns."""

OUTPUT_FORMATS: Final[tuple[str, ...]] = ("text", "github")
"""`text` for a terminal, `github` for workflow annotations on the PR's own lines."""


def registry_lines() -> list[str]:
    """Render every invariant ID this repository speaks with.

    Returns:
        One line per ID, in family order, with a note on the ones run elsewhere.
    """
    lines = [f"{ident}  {check} — {defect}" for ident, check, defect in MARKETPLACE_INVARIANTS]
    lines.extend(f"{ident}  {check} — {defect}" for ident, check, defect in PLUGIN_INVARIANTS)
    lines.extend(f"{ident}  {check} — {defect}" for ident, check, defect in GITHUB_INVARIANTS)
    lines.extend(f"{ident}  {check}" for ident, check in VERSIONING_INVARIANTS)
    lines.extend(
        f"{ident}  {check} — {defect} {LINT_NOTE}" for ident, check, defect in LINT_INVARIANTS
    )
    for ident, check, defect in DEFERRED_INVARIANTS:
        note = TEST_NOTE if ident == "T1" else f"({HYGIENE_TESTS[ident]})"
        lines.append(f"{ident}  {check} — {defect} {note}")
    return lines


def _skill_files(root: Path, plugin_id: str) -> list[str]:
    """List a plugin's `SKILL.md` files.

    Args:
        root: The repository root.
        plugin_id: The plugin directory name.

    Returns:
        Repository-relative paths.
    """
    return [
        f"plugins/{plugin_id}/skills/{name}/SKILL.md" for name in kind.skill_names(root, plugin_id)
    ]


def _agent_files(root: Path, plugin_id: str) -> list[str]:
    """List a plugin's subagent files.

    Args:
        root: The repository root.
        plugin_id: The plugin directory name.

    Returns:
        Repository-relative paths.
    """
    return [f"plugins/{plugin_id}/agents/{name}.md" for name in kind.agent_names(root, plugin_id)]


def known_skill_references(root: Path) -> list[str]:
    """List every `<plugin>:<skill>` this marketplace ships.

    Args:
        root: The repository root.

    Returns:
        Sorted references, which S6 resolves against.
    """
    return sorted(
        f"{plugin_id}:{skill}"
        for plugin_id in plugin_ids(root)
        for skill in kind.skill_names(root, plugin_id)
    )


def check_frontmatter(root: Path, plugin_id: str, known: Sequence[str]) -> list[Finding]:
    """Run S1 to S6 over a plugin's skills and subagents.

    Args:
        root: The repository root.
        plugin_id: The plugin directory name.
        known: Every `<plugin>:<skill>` reference that resolves.

    Returns:
        Every finding.
    """
    findings: list[Finding] = []
    for rel in _skill_files(root, plugin_id):
        block = frontmatter.read(root / rel)
        findings.extend(frontmatter.check_parses(rel, block))
        findings.extend(frontmatter.check_known_keys(rel, block, frontmatter.SKILL_KEYS, "S2"))
        findings.extend(frontmatter.check_description(rel, block))
        findings.extend(frontmatter.check_tool_grants(rel, block))
    for rel in _agent_files(root, plugin_id):
        block = frontmatter.read(root / rel)
        findings.extend(frontmatter.check_parses(rel, block))
        findings.extend(frontmatter.check_known_keys(rel, block, frontmatter.AGENT_KEYS, "S2"))
        findings.extend(frontmatter.check_agent_identity(rel, block))
        findings.extend(frontmatter.check_agent_skills(rel, block, known))
        findings.extend(frontmatter.check_tool_grants(rel, block))
    return findings


def check_hooks(root: Path, plugin_id: str) -> list[Finding]:
    """Run H1 to H7 over a plugin's `hooks.json` and settings fragments.

    Args:
        root: The repository root.
        plugin_id: The plugin directory name.

    Returns:
        Every finding.
    """
    findings = hook_contract.check_hooks_file(root, plugin_id)
    for rel in tracked_files(root, f"plugins/{plugin_id}/*"):
        if rel.rsplit("/", 1)[-1] == hook_contract.FRAGMENT_NAME:
            findings.extend(hook_contract.check_fragment(root, plugin_id, rel))
    return findings


def check_changelog(root: Path, plugin_id: str) -> list[Finding]:
    """Run P3, C1 and C2 over a plugin's CHANGELOG.

    Args:
        root: The repository root.
        plugin_id: The plugin directory name.

    Returns:
        Every finding.
    """
    rel = f"plugins/{plugin_id}/CHANGELOG.md"
    path = root / rel
    if not path.is_file():
        return [Finding("P3", rel, "no CHANGELOG")]
    changelog = read_changelog(path)
    version = readme_contract.manifest(root, plugin_id).get("version")
    names = [plugin_id, *predecessors(plugin_id, read_renames(root))]
    tags = {ref.tag for name in names for ref in plugin_tags(root, name)}
    findings: list[Finding] = []
    if isinstance(version, str):
        findings.extend(check_entry(changelog, version=version, path=rel))
    findings.extend(check_links(changelog, path=rel, names=names, known_tags=tags))
    findings.extend(check_released_bodies(root, changelog, path=rel, names=names, known_tags=tags))
    return findings


def check_readme(root: Path, plugin_id: str) -> list[Finding]:
    """Run the per-plugin half of R1 to R13.

    Args:
        root: The repository root.
        plugin_id: The plugin directory name.

    Returns:
        Every finding.
    """
    rel = readme_contract.readme_rel(plugin_id)
    path = root / rel
    if not path.is_file():
        return [Finding("R1", rel, "no README")]
    text = path.read_text(encoding="utf-8")
    scripts = boundary.shipped_scripts(root, plugin_id)
    grants, compatibilities, modules = _skill_facts(root, plugin_id)
    runs_bash = any(
        command.split()[:1] == ["bash"] for _, command in boundary.hook_commands(root, plugin_id)
    )
    return [
        *readme_contract.check_sections(
            rel, text, has_other_components=readme_contract.has_other_components(root, plugin_id)
        ),
        *kind.check_kind(root, plugin_id, text),
        *readme_contract.check_badges(root, plugin_id, rel, text),
        *readme_contract.check_last_verified(rel, text),
        *readme_contract.check_network_badge(
            rel, text, networked=readme_contract.uses_network(root, plugin_id, grants, modules)
        ),
        *readme_contract.check_requirements(root, plugin_id, rel, text),
        *readme_contract.check_env_vars(root, rel, text, scripts),
        *readme_contract.check_no_eval_scores(rel, text),
        *readme_contract.check_windows_rule(rel, text, runs_bash=runs_bash),
        *readme_contract.check_skill_commands(root, plugin_id, rel, text),
        *readme_contract.check_cowork_claim(rel, text, compatibilities),
    ]


def _skill_facts(root: Path, plugin_id: str) -> tuple[list[str], list[str], list[str]]:
    """Read what a plugin's skills grant, claim and import.

    Args:
        root: The repository root.
        plugin_id: The plugin directory name.

    Returns:
        The granted tool names, the `compatibility:` values, and the modules its shipped
        Python imports.
    """
    grants: list[str] = []
    compatibilities: list[str] = []
    for rel in [*_skill_files(root, plugin_id), *_agent_files(root, plugin_id)]:
        block = frontmatter.read(root / rel)
        for grant in frontmatter.tool_grants(block.data.get("allowed-tools")):
            match = frontmatter.TOOL_GRANT.match(grant)
            if match is not None:
                grants.append(match.group("tool"))
        value = block.data.get("compatibility")
        if isinstance(value, str):
            compatibilities.append(value)
    modules: list[str] = []
    for rel in boundary.shipped_scripts(root, plugin_id):
        if rel.endswith(boundary.PYTHON_SUFFIX):
            modules.extend(boundary.imported_modules((root / rel).read_text(encoding="utf-8")))
    return grants, compatibilities, modules


def check_plugin(root: Path, plugin_id: str, known: Sequence[str]) -> list[Finding]:
    """Run every per-plugin invariant over one plugin.

    Args:
        root: The repository root.
        plugin_id: The plugin directory name.
        known: Every `<plugin>:<skill>` reference that resolves.

    Returns:
        Every finding, in family order.
    """
    findings: list[Finding] = [
        *kind.check_license(root, plugin_id),
        *kind.check_placeholders(root, plugin_id),
        *kind.check_no_bin(root, plugin_id),
        *check_changelog(root, plugin_id),
        *check_frontmatter(root, plugin_id, known),
        *check_hooks(root, plugin_id),
        *check_readme(root, plugin_id),
        *boundary.collect(root, plugin_id),
        *evals.collect(root, plugin_id),
    ]
    for rel in tracked_files(root, f"plugins/{plugin_id}/workflows/*.js"):
        findings.extend(workflow_checks.check_workflow(root, rel))
    return findings


def collect(root: Path, *, only: str | None = None) -> list[Finding]:
    """Run every invariant over one working tree.

    Args:
        root: The repository root.
        only: A single plugin id to check, or None for all of them and the repository-wide
            invariants.

    Returns:
        Every finding.

    Raises:
        MissingPathError: If the root does not exist.
    """
    if not root.is_dir():
        raise MissingPathError(root, "the repository root")
    chosen = [only] if only is not None else plugin_ids(root)
    known = known_skill_references(root)
    findings: list[Finding] = []
    for plugin_id in chosen:
        findings.extend(check_plugin(root, plugin_id, known))
    if only is not None:
        return findings
    readme = (root / "README.md").read_text(encoding="utf-8")
    findings.extend(readme_contract.check_catalog(root, readme, plugin_ids(root)))
    findings.extend(readme_contract.check_template_shapes(root))
    findings.extend(readme_contract.check_legal_texts(root))
    findings.extend(marketplace_collect(root))
    findings.extend(labels.validate(root))
    findings.extend(validate_forms(root))
    findings.extend(repo_metadata_collect(root))
    return findings


def annotation(finding: Finding) -> str:
    """Render a finding as a GitHub workflow command.

    Args:
        finding: The finding to render.

    Returns:
        The `::error` or `::warning` line, on the file it belongs to when there is one.
    """
    level = "error" if finding.severity == "error" else "warning"
    location = f" file={finding.path}" if finding.path else ""
    return f"::{level}{location}::{finding.invariant_id} {finding.message}"


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    """Parse the command line.

    Args:
        argv: Arguments without the program name; `sys.argv[1:]` when None.

    Returns:
        The parsed arguments.

    Raises:
        SystemExit: If argparse refuses the arguments.
    """
    parser = argparse.ArgumentParser(
        prog="python -m scripts.plugin_validation.validate_plugins",
        description="Check every plugin invariant this repository adds to the official CLI.",
    )
    _ = parser.add_argument("--list", action="store_true", help="print the invariant registry")
    _ = parser.add_argument("--root", default=None, help="check this tree instead of this one")
    _ = parser.add_argument("--plugin", default=None, help="check only this plugin")
    _ = parser.add_argument(
        "--output-format", default="text", choices=OUTPUT_FORMATS, help="how findings are printed"
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the plugin gate.

    Args:
        argv: Arguments without the program name; `sys.argv[1:]` when None.

    Returns:
        0 when nothing fires or only warnings do, 1 on any error, 2 on unusable inputs.
    """
    options = parse_args(argv)
    values: dict[str, object] = vars(options)
    if values["list"]:
        for line in registry_lines():
            print(line)
        return int(ExitCode.OK)
    raw_root = values["root"]
    only = values["plugin"]
    try:
        root = Path(raw_root) if isinstance(raw_root, str) else repo_root()
        findings = collect(root, only=only if isinstance(only, str) else None)
    except (MaintainerError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return int(ExitCode.USAGE)
    github = values["output_format"] == "github"
    for finding in findings:
        print(annotation(finding) if github else format_finding(finding))
    failed = any(finding.severity == "error" for finding in findings)
    if not failed:
        warnings = sum(1 for finding in findings if finding.severity == "warning")
        print(f"plugins: every invariant passes ({warnings} warning(s))")
    return int(ExitCode.FINDINGS if failed else ExitCode.OK)


if __name__ == "__main__":
    raise SystemExit(main())
