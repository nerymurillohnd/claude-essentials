"""L4: GitHub Actions workflows, checked by actionlint and audited by zizmor.

Two tools with two roles. **actionlint** is a syntax and expression checker: an undefined
`needs` reference or a typo in a `${{ }}` expression is a workflow that fails on the runner
and nowhere else, so it blocks. **zizmor** is a security auditor, run with its strictest
persona; its findings are policy questions rather than breakage.

Until step 7 rewrites every workflow, zizmor is advisory: today's files carry 24 findings
that the rewrite addresses in one piece, and failing the gate on them would only mean
suppressing them one by one first. `ZIZMOR_BLOCKING` is the switch, pinned by a test so
flipping it is a deliberate edit rather than a side effect.

The ignore policy is enforced even while zizmor is advisory, because that is the part this
repository owns: the only `# zizmor: ignore[...]` this repository accepts is
`dangerous-triggers`, and only on a line whose comment cites ADR-0004 (the issue-triage
workflow's `pull_request_target`, which never checks out the head).
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Final

from scripts.common.environment import in_github_actions
from scripts.common.errors import Finding
from scripts.lint.tools import run, tool_path

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from scripts.common.errors import Severity

INVARIANT: Final = "L4"
"""The ID every blocking message in this module starts with."""

ADVISORY_INVARIANT: Final = "G2"
"""The ID the zizmor summary is reported under; G2 is the workflow-hygiene invariant."""

ADVISORY_PREFIX: Final = "G2 advisory (step 7):"
"""What marks a line that reports rather than refuses."""

ZIZMOR_BLOCKING: Final[bool] = False  # flipped at step 7
"""Whether a zizmor finding fails the gate. False until the workflows are rewritten."""

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

SUMMARY: Final = re.compile(r"^\d+ findings?.*$", re.MULTILINE)
"""zizmor's closing count line, which is what the advisory reports."""


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


def _offline() -> bool:
    """Decide whether zizmor may reach the network.

    Returns:
        True locally, so a laptop run never depends on GitHub being reachable; False under
        Actions, where the online audits are the point.
    """
    return not in_github_actions()


def zizmor_summary(root: Path, paths: Sequence[str]) -> str:
    """Run zizmor and return its closing count line.

    Args:
        root: The repository root.
        paths: The workflow files to audit.

    Returns:
        The summary line, or a short description when zizmor printed none.

    Raises:
        ExecutableNotFoundError: If `.venv/bin/zizmor` is missing.
    """
    executable = tool_path(root, "zizmor")
    args = ["--persona=auditor", "--format", "plain"]
    if _offline():
        args.append("--offline")
    completed = run(executable, [*args, *paths], cwd=root)
    match = SUMMARY.search(f"{completed.stdout}\n{completed.stderr}")
    if match is None:
        return "no findings"
    return match.group().strip()


def check(root: Path, paths: Sequence[str]) -> list[Finding]:
    """Check every workflow in a candidate list.

    Args:
        root: The repository root.
        paths: Repository-relative candidate paths; anything outside the workflow directory
            is ignored.

    Returns:
        actionlint's findings and the ignore-policy findings as errors, plus one zizmor
        advisory whose severity follows `ZIZMOR_BLOCKING`.

    Raises:
        ExecutableNotFoundError: If a locked binary is missing.
    """
    selected = select(paths)
    if not selected:
        return []
    findings = [*_actionlint(root, selected), *check_ignore_policy(root, selected)]
    summary = zizmor_summary(root, selected)
    severity: Severity = "error" if ZIZMOR_BLOCKING else "warning"
    findings.append(
        Finding(
            ADVISORY_INVARIANT,
            WORKFLOW_DIR,
            f"{ADVISORY_PREFIX} zizmor --persona=auditor reports {summary}",
            severity,
        )
    )
    return findings
