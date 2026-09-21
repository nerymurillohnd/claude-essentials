"""The version-bump gate: what each plugin owes, which route the push takes, which label.

Three consumers read this entrypoint, and each reads a different part of it:

* `.claude/hooks/guard-push.sh` runs it before a direct push to `main` and refuses the push
  unless the output carries `bump: none`, so the last printed line is a contract:
  `Computed label: bump: <level>` and nothing after it. No other line may contain `bump: `.
* The `version-check` CI job runs it with `--base origin/<base ref> --verify-tag` on a pull
  request and with `--base <before sha>` on a push, adding `--deferred` when the pull request
  carries the `bump: deferred` label, and reads the exit status.
* `repo-auditor` and the delivery skill read `--json`, whose shape is fixed:
  `{route, label, deferred, plugins:[{name, predecessor, tagged, version, runtime_changed,
  first_runtime_path, required, ok, reason}]}`.

Nothing here touches the network: the base ref, the tags and the working tree are the only
inputs, and `--deferred` is passed in rather than looked up, so the same command gives the
same answer on a laptop and on a runner.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import sys
from typing import TYPE_CHECKING, Final, Literal

from scripts.common.errors import (
    ExecutableNotFoundError,
    ExitCode,
    Finding,
    MaintainerError,
    format_finding,
)
from scripts.common.plugins import repo_root
from scripts.versioning.tag_versions import claude_executable, run_claude_tag
from scripts.versioning.version_plan import Plan, build_plan, tag_exists, to_json_obj

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from scripts.versioning.version_plan import PluginPlan

OutputFormat = Literal["text", "github"]
"""How findings are rendered: plain lines, or GitHub Actions annotations."""

DEFAULT_BASE: Final = "origin/main"
"""What the route is measured against when the caller names no base."""

MINIMUM_LEVEL: Final = "patch"
"""The smallest bump a runtime change can owe; the lifecycle table may demand more."""

LABEL_PREFIX: Final = "Computed label: "
"""The prefix of the last line, which `guard-push.sh` parses with `sed`."""


@dataclass(frozen=True, slots=True)
class Options:
    """Parsed command line.

    Attributes:
        base: The ref the route is measured against.
        verify_tag: Also ask the official CLI whether each untagged version would tag.
        deferred: The pull request carries the `bump: deferred` label.
        as_json: Print the machine contract instead of the human report.
        output_format: How findings are rendered in the human report.
    """

    base: str
    verify_tag: bool
    deferred: bool
    as_json: bool
    output_format: OutputFormat


def parse_args(argv: Sequence[str] | None) -> Options:
    """Parse the command line.

    Args:
        argv: Arguments without the program name; `sys.argv[1:]` when None.

    Returns:
        The options.

    Raises:
        SystemExit: If argparse refuses the arguments.
    """
    parser = argparse.ArgumentParser(
        prog="python -m scripts.versioning.check_versions",
        description="Check plugin version bumps and compute the push route and label.",
    )
    _ = parser.add_argument("--base", default=DEFAULT_BASE, help="ref to compare against")
    _ = parser.add_argument(
        "--verify-tag",
        action="store_true",
        help="run `claude plugin tag --dry-run` for every untagged version",
    )
    _ = parser.add_argument(
        "--deferred",
        action="store_true",
        help="the pull request declares its runtime drift deliberate",
    )
    _ = parser.add_argument("--json", action="store_true", help="print the machine contract")
    _ = parser.add_argument(
        "--output-format",
        choices=("text", "github"),
        default="text",
        help="render findings as plain lines or as GitHub Actions annotations",
    )
    values: dict[str, object] = vars(parser.parse_args(argv))
    chosen = values["output_format"]
    output_format: OutputFormat = "github" if chosen == "github" else "text"
    base = values["base"]
    return Options(
        base=base if isinstance(base, str) else DEFAULT_BASE,
        verify_tag=bool(values["verify_tag"]),
        deferred=bool(values["deferred"]),
        as_json=bool(values["json"]),
        output_format=output_format,
    )


def plugin_line(plugin: PluginPlan) -> str:
    """Render one plugin's verdict.

    No line may contain `bump: `, because `guard-push.sh` searches the whole output for it.

    Args:
        plugin: The plugin's plan.

    Returns:
        The single line printed for that plugin.
    """
    if not plugin.version:
        return f"{plugin.name} removed"
    head = f"{plugin.name} {plugin.version}"
    if plugin.tagged is None:
        return f"{head} new plugin"
    if plugin.first_runtime_path is None:
        return f"{head} exempt"
    runtime = f"{head} runtime: {plugin.first_runtime_path}"
    if plugin.required:
        return f"{runtime} → needs {MINIMUM_LEVEL}"
    if plugin.version == plugin.tagged:
        return f"{runtime} → deferred"
    return f"{runtime} → bumped from {plugin.tagged} ({plugin.level})"


def finding_line(finding: Finding, *, output_format: OutputFormat) -> str:
    """Render one finding for a maintainer or for GitHub Actions.

    Args:
        finding: The violation to print.
        output_format: `text` for a plain line, `github` for a workflow annotation.

    Returns:
        The single line printed for that finding.
    """
    if output_format == "text":
        return format_finding(finding)
    where = "" if finding.path is None else f" file={finding.path}"
    return f"::{finding.severity}{where}::{finding.invariant_id} {finding.message}"


def render(
    plan: Plan,
    *,
    extra: Sequence[str],
    findings: Sequence[Finding],
    output_format: OutputFormat,
) -> list[str]:
    """Build the whole report, label last.

    Args:
        plan: The plan to report.
        extra: Lines from `--verify-tag`, printed after the plugin lines.
        findings: Every finding, the plan's own plus the tag verification's.
        output_format: How findings are rendered.

    Returns:
        The lines to print, in order.
    """
    lines = [plugin_line(plugin) for plugin in plan.plugins]
    lines.extend(extra)
    lines.extend(finding_line(finding, output_format=output_format) for finding in findings)
    lines.append(f"{LABEL_PREFIX}{plan.label}")
    return lines


def verify_tags(root: Path, plan: Plan) -> tuple[list[str], list[Finding]]:
    """Ask the official CLI whether every untagged version would tag cleanly.

    Running this before merge means the `Tag plugin versions` workflow does not fail on
    `main` over a problem a reviewer could have seen.

    Args:
        root: The repository root.
        plan: The plan whose plugins are checked.

    Returns:
        One line per plugin checked, and a finding per plugin the CLI refused.
    """
    try:
        _ = claude_executable()
    except ExecutableNotFoundError as error:
        return [], [Finding("V6", None, f"--verify-tag needs the CLI: {error}")]
    lines: list[str] = []
    findings: list[Finding] = []
    for plugin in plan.plugins:
        tag = f"{plugin.name}--v{plugin.version}"
        if not plugin.version or tag_exists(root, tag):
            continue
        result = run_claude_tag(root, plugin.name, extra=["--dry-run"])
        verdict = "would tag" if result.returncode == 0 else "refused"
        lines.append(f"{plugin.name} {plugin.version} tag dry-run: {verdict}")
        if result.returncode != 0:
            findings.append(
                Finding("V6", f"plugins/{plugin.name}", f"{tag} was refused: {result.output}"),
            )
    return lines, findings


def main(argv: Sequence[str] | None = None) -> int:
    """Run the gate.

    Args:
        argv: Arguments without the program name; `sys.argv[1:]` when None.

    Returns:
        0 when every plugin passes, 1 when one does not, 2 when the inputs are unusable.
    """
    options = parse_args(argv)
    root = repo_root()
    try:
        plan = build_plan(root, base=options.base, deferred=options.deferred)
    except MaintainerError as error:
        print(f"error: {error}", file=sys.stderr)
        return int(ExitCode.USAGE)
    findings = list(plan.findings)
    extra: list[str] = []
    if options.verify_tag:
        verified, more = verify_tags(root, plan)
        extra.extend(verified)
        findings.extend(more)
    if options.as_json:
        print(json.dumps(to_json_obj(plan), indent=2))
    else:
        for line in render(
            plan, extra=extra, findings=findings, output_format=options.output_format
        ):
            print(line)
    failed = any(not plugin.ok for plugin in plan.plugins) or any(
        finding.severity == "error" for finding in findings
    )
    return int(ExitCode.FINDINGS if failed else ExitCode.OK)


if __name__ == "__main__":
    raise SystemExit(main())
