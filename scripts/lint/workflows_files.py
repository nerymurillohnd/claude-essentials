"""L4: GitHub Actions workflows, checked by actionlint and audited by zizmor.

Two tools with two roles. **actionlint** is a syntax and expression checker: an undefined
`needs` reference or a typo in a `${{ }}` expression is a workflow that fails on the runner
and nowhere else. **zizmor** is a security auditor, run with its strictest persona. Both
block: the step-7 rewrite brought every workflow to zero zizmor findings, and
`ZIZMOR_BLOCKING` is pinned by a test so turning it off again is a deliberate edit.

The ignore policy is the part this repository owns: the only `# zizmor: ignore[...]` it
accepts is `dangerous-triggers`, and only on a line whose comment cites ADR-0004. Two
workflows carry it, both on `pull_request_target`: `triage.yml` (base checkout only) and
`close-external-prs.yml` (no checkout at all); neither runs pull request code or restores a
cache.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Final

from scripts.common.errors import Finding
from scripts.lint.tools import run, tool_path

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from scripts.common.errors import Severity

INVARIANT: Final = "L4"
"""The ID every blocking message in this module starts with."""

ZIZMOR_INVARIANT: Final = "G2"
"""The ID a zizmor finding is reported under; G2 is the workflow-hygiene invariant."""

ZIZMOR_BLOCKING: Final[bool] = True
"""Whether a zizmor finding fails the gate; True since the step-7 rewrite."""

WORKFLOW_DIR: Final = ".github/workflows"
"""Where the workflows this module checks live."""

WORKFLOW_SUFFIXES: Final[tuple[str, ...]] = (".yml", ".yaml")
"""Both spellings GitHub accepts, so a renamed file is never silently unchecked."""

ACTIONLINT_LINE: Final = re.compile(
    r"^(?P<path>[^:]+):(?P<line>\d+):(?P<column>\d+):\s*(?P<rest>.+)$"
)
"""One actionlint finding: path, line, column, then the message and its rule."""

ZIZMOR_IGNORE: Final = re.compile(r"#\s*zizmor:\s*ignore\[(?P<rules>[^\]]*)\]")
"""An inline zizmor suppression, whatever rules it names."""

ALLOWED_IGNORE: Final = "dangerous-triggers"
"""The one rule this repository may suppress (ADR-0004)."""

IGNORE_CITATION: Final = "ADR-0004"
"""What the suppression's own line must cite for it to be accepted."""

SUMMARY: Final = re.compile(r"^(?:\d+ findings?|No findings).*$", re.MULTILINE)
"""zizmor's closing line: `N findings (...)` or `No findings to report. ... (N ignored)`."""

FINDING_HEADLINE: Final = re.compile(r"^(?:error|warning|help|info)\[[a-z-]+\]:.*$")
"""The first line of one zizmor finding, which names the audit."""

FINDING_LOCATION: Final = re.compile(r"^\s*-->\s*(?P<location>\S+)")
"""The `--> path:line:column` line under a headline."""

CLEAN_EXIT_CODES: Final = frozenset({0})
"""zizmor exits 0 with nothing to report and 10-14 by the highest finding's severity."""


def select(paths: Sequence[str]) -> list[str]:
    """Keep the workflow files out of a candidate list.

    Args:
        paths: Repository-relative candidate paths.

    Returns:
        The paths under `.github/workflows/` that end in a YAML suffix.
    """
    return [
        rel
        for rel in paths
        if rel.startswith(f"{WORKFLOW_DIR}/") and rel.endswith(WORKFLOW_SUFFIXES)
    ]


def _actionlint(root: Path, paths: Sequence[str]) -> list[Finding]:
    """Run actionlint over the workflows and turn its output into findings.

    Args:
        root: The repository root.
        paths: The workflow files to check.

    Returns:
        One finding per reported line.

    Raises:
        ExecutableNotFoundError: If `.venv/bin/actionlint` is missing.
    """
    executable = tool_path(root, "actionlint")
    completed = run(executable, ["-no-color", *paths], cwd=root)
    findings: list[Finding] = []
    for line in completed.stdout.splitlines():
        match = ACTIONLINT_LINE.match(line)
        if match is None:
            continue
        findings.append(Finding(INVARIANT, match["path"], f"line {match['line']}: {match['rest']}"))
    return findings


def check_ignore_policy(root: Path, paths: Sequence[str]) -> list[Finding]:
    """Check every zizmor suppression against the one this repository accepts.

    Args:
        root: The repository root.
        paths: The workflow files to read.

    Returns:
        One finding per suppression that names another rule or cites no ADR.
    """
    findings: list[Finding] = []
    for rel in paths:
        for number, line in enumerate((root / rel).read_text(encoding="utf-8").splitlines(), 1):
            match = ZIZMOR_IGNORE.search(line)
            if match is None:
                continue
            rules = [rule.strip() for rule in match["rules"].split(",") if rule.strip()]
            if rules != [ALLOWED_IGNORE]:
                findings.append(
                    Finding(
                        INVARIANT, rel, f"line {number}: only `{ALLOWED_IGNORE}` may be ignored"
                    )
                )
            elif IGNORE_CITATION not in line:
                findings.append(
                    Finding(INVARIANT, rel, f"line {number}: the ignore cites no {IGNORE_CITATION}")
                )
    return findings


ZIZMOR_OFFLINE: Final = True
"""zizmor runs offline everywhere, CI included (decided 2026-09-22).

Online, `stale-action-refs` and `ref-version-mismatch` fire on the pin of
`anthropics/claude-plugins-community/.github/actions/validate-plugins`: that repository
publishes no tag, so no pin can satisfy them, and excluding the two audits would be a
suppression by another name. The cost is the online audits (`impostor-commit`,
`known-vulnerable-actions`, `ref-confusion`); it is recorded as debt and in the ADR-0004
amendment, and closes when upstream tags the action or the action is vendored before
`official` becomes a required check.
"""


def _offline() -> bool:
    """Decide whether zizmor may reach the network.

    Returns:
        Always True: see `ZIZMOR_OFFLINE` for why CI runs offline too.
    """
    return ZIZMOR_OFFLINE


def _zizmor(root: Path, paths: Sequence[str]) -> tuple[int, str]:
    """Run zizmor over the workflows.

    Args:
        root: The repository root.
        paths: The workflow files to audit.

    Returns:
        The exit status and the combined output.

    Raises:
        ExecutableNotFoundError: If `.venv/bin/zizmor` is missing.
    """
    executable = tool_path(root, "zizmor")
    args = ["--persona=auditor", "--format", "plain"]
    if _offline():
        args.append("--offline")
    completed = run(executable, [*args, *paths], cwd=root)
    return completed.returncode, f"{completed.stdout}\n{completed.stderr}"


def zizmor_summary(root: Path, paths: Sequence[str]) -> str:
    """Run zizmor and return its closing line.

    Args:
        root: The repository root.
        paths: The workflow files to audit.

    Returns:
        The summary line, or a short description when zizmor printed none.

    Raises:
        ExecutableNotFoundError: If `.venv/bin/zizmor` is missing.
    """
    _status, output = _zizmor(root, paths)
    match = SUMMARY.search(output)
    return "no summary" if match is None else match.group().strip()


def finding_lines(output: str) -> list[str]:
    """Pair every zizmor headline with the location printed under it.

    Args:
        output: zizmor's plain-format output.

    Returns:
        One `location: headline` line per finding, in output order.
    """
    lines: list[str] = []
    headline: str | None = None
    for line in output.splitlines():
        if FINDING_HEADLINE.match(line):
            headline = line.strip()
            continue
        location = FINDING_LOCATION.match(line)
        if headline is not None and location is not None:
            lines.append(f"{location['location']}: {headline}")
            headline = None
    return lines


def zizmor_findings(root: Path, paths: Sequence[str]) -> list[Finding]:
    """Audit the workflows and report every zizmor finding.

    Args:
        root: The repository root.
        paths: The workflow files to audit.

    Returns:
        One finding per zizmor finding, plus one when zizmor itself failed; severity follows
        `ZIZMOR_BLOCKING`.

    Raises:
        ExecutableNotFoundError: If `.venv/bin/zizmor` is missing.
    """
    status, output = _zizmor(root, paths)
    if status in CLEAN_EXIT_CODES:
        return []
    severity: Severity = "error" if ZIZMOR_BLOCKING else "warning"
    reported = finding_lines(output)
    if not reported:
        summary = SUMMARY.search(output)
        detail = output.strip()[-400:] if summary is None else summary.group().strip()
        reported = [f"zizmor exited {status}: {detail}"]
    return [
        Finding(ZIZMOR_INVARIANT, WORKFLOW_DIR, f"zizmor --persona=auditor: {line}", severity)
        for line in reported
    ]


def check(root: Path, paths: Sequence[str]) -> list[Finding]:
    """Check every workflow in a candidate list.

    Args:
        root: The repository root.
        paths: Repository-relative candidate paths; anything outside the workflow directory
            is ignored.

    Returns:
        actionlint's findings, the ignore-policy findings and every zizmor finding.

    Raises:
        ExecutableNotFoundError: If a locked binary is missing.
    """
    selected = select(paths)
    if not selected:
        return []
    return [
        *_actionlint(root, selected),
        *check_ignore_policy(root, selected),
        *zizmor_findings(root, selected),
    ]
