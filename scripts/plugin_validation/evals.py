"""Eval-suite authoring invariants E1 to E4.

An eval suite is never a gate (P8): it is expensive and non-deterministic, so nothing here
runs a case. What is checked is that a suite can measure something — enough cases, at least
one that proves the plugin stays quiet, a prompt and graders per case, results that stay out
of git, and a README whose CI section matches the policy the repository actually runs.

The defect this catches is the vanity suite: four cases that all fire, so the run can only
ever agree with its author.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from scripts.common.errors import Finding
from scripts.common.plugins import PLUGINS_DIRNAME, git_output_or_none
from scripts.plugin_validation.frontmatter import read
from scripts.plugin_validation.kind import plugin_dir, skill_names

if TYPE_CHECKING:
    from pathlib import Path

EVALS_DIRNAME: Final = "evals"
"""The directory a plugin's behavioural suite lives in."""

RESULTS_DIRNAME: Final = "results"
"""Where a run writes its output; it must stay git-ignored."""

README_NAME: Final = "README.md"
"""The suite's own README, which E1 requires and E4 reads."""

PROMPT_NAME: Final = "prompt.md"
"""The file that carries a case's prompt, unless `case.yaml` carries it instead."""

CASE_FILE: Final = "case.yaml"
"""The optional per-case configuration, which may carry `execution.prompt` instead."""

GRADERS_DIRNAME: Final = "graders"
"""Where a case's graders live; each is a Markdown file with YAML frontmatter."""

MINIMUM_CASES: Final = 3
"""Cases a suite needs before a delta means anything."""

MUST_NOT_FIRE: Final[dict[str, object]] = {"min": 0, "max": 0, "arm": "both"}
"""The grader frontmatter that makes a case a must-not-fire case."""

CI_SECTION: Final = "CI policy"
"""The heading E4 reads to check the suite's CI claims."""

CI_REQUIRED_CLAIMS: Final[tuple[str, ...]] = (
    "never blocking",
    "evals/**",
)
"""What the CI section states: evals never block, and an `evals/**` change selects no run."""


def evals_dir(root: Path, plugin_id: str) -> Path:
    """Return a plugin's eval directory.

    Args:
        root: The repository root.
        plugin_id: The plugin directory name.

    Returns:
        The path, whether or not it exists.
    """
    return plugin_dir(root, plugin_id) / EVALS_DIRNAME


def case_dirs(root: Path, plugin_id: str) -> list[Path]:
    """List a plugin's eval cases.

    Args:
        root: The repository root.
        plugin_id: The plugin directory name.

    Returns:
        Sorted case directories; empty when the suite does not exist.
    """
    base = evals_dir(root, plugin_id)
    if not base.is_dir():
        return []
    return sorted(
        entry for entry in base.iterdir() if entry.is_dir() and entry.name != RESULTS_DIRNAME
    )


def is_must_not_fire(grader: Path) -> bool:
    """Report whether a grader asserts the plugin stayed out of the way.

    Args:
        grader: The grader file.

    Returns:
        True when its frontmatter carries `min: 0`, `max: 0` and `arm: both`.
    """
    data = read(grader).data
    return all(data.get(key) == value for key, value in MUST_NOT_FIRE.items())


def check_suite(root: Path, plugin_id: str) -> list[Finding]:
    """Check a plugin's suite shape (E1).

    Args:
        root: The repository root.
        plugin_id: The plugin directory name.

    Returns:
        One finding per rule broken; none when the plugin ships no suite at all.
    """
    base = evals_dir(root, plugin_id)
    rel = f"{PLUGINS_DIRNAME}/{plugin_id}/{EVALS_DIRNAME}"
    if not base.is_dir():
        return [Finding("E1", f"{PLUGINS_DIRNAME}/{plugin_id}", "ships no eval suite")]
    findings: list[Finding] = []
    if not (base / README_NAME).is_file():
        findings.append(Finding("E1", rel, f"no `{README_NAME}`"))
    cases = case_dirs(root, plugin_id)
    if len(cases) < MINIMUM_CASES:
        findings.append(
            Finding("E1", rel, f"{len(cases)} cases; a suite needs at least {MINIMUM_CASES}")
        )
    if not any(_has_must_not_fire(case) for case in cases):
        findings.append(
            Finding(
                "E1", rel, "no must-not-fire case (a grader with `min: 0`, `max: 0`, `arm: both`)"
            )
        )
    return findings


def _has_must_not_fire(case: Path) -> bool:
    """Report whether a case carries a must-not-fire grader.

    Args:
        case: The case directory.

    Returns:
        True when at least one grader asserts the plugin did not fire.
    """
    graders = case / GRADERS_DIRNAME
    if not graders.is_dir():
        return False
    return any(is_must_not_fire(path) for path in sorted(graders.glob("*.md")))


def check_cases(root: Path, plugin_id: str) -> list[Finding]:
    """Check that every case can run and can fail (E2).

    Args:
        root: The repository root.
        plugin_id: The plugin directory name.

    Returns:
        One finding per case without a prompt or without graders.
    """
    findings: list[Finding] = []
    for case in case_dirs(root, plugin_id):
        rel = f"{PLUGINS_DIRNAME}/{plugin_id}/{EVALS_DIRNAME}/{case.name}"
        if not _has_prompt(case):
            findings.append(
                Finding("E2", rel, f"no `{PROMPT_NAME}` and no `{CASE_FILE}` carrying the prompt")
            )
        graders = case / GRADERS_DIRNAME
        if not graders.is_dir() or not sorted(graders.glob("*.md")):
            findings.append(Finding("E2", rel, f"no `{GRADERS_DIRNAME}/` with at least one grader"))
    return findings


def _has_prompt(case: Path) -> bool:
    """Report whether a case carries a prompt.

    Args:
        case: The case directory.

    Returns:
        True when `prompt.md` exists, or `case.yaml` names an execution prompt.
    """
    if (case / PROMPT_NAME).is_file():
        return True
    config = case / CASE_FILE
    return config.is_file() and "prompt" in config.read_text(encoding="utf-8")


def check_results_ignored(root: Path, plugin_id: str) -> list[Finding]:
    """Check that run output stays out of git (E3).

    Args:
        root: The repository root.
        plugin_id: The plugin directory name.

        One finding when `results/` is not ignored, and one when a result file is tracked.
    """
    rel = f"{PLUGINS_DIRNAME}/{plugin_id}/{EVALS_DIRNAME}/{RESULTS_DIRNAME}"
    if not evals_dir(root, plugin_id).is_dir():
        return []
    # `git check-ignore -q` exits 0 when the path is ignored and 1 when it is not, so the
    # helper that turns a non-zero exit into None answers exactly that question.
    ignored = git_output_or_none(root, ["check-ignore", "-q", f"{rel}/run.json"]) is not None
    findings: list[Finding] = []
    if not ignored:
        findings.append(
            Finding("E3", rel, "run output is not git-ignored; add `**/evals/results/`")
        )
    tracked = git_output_or_none(root, ["ls-files", "--", rel])
    if tracked:
        findings.append(Finding("E3", rel, "run output is tracked"))
    return findings


def check_readme(root: Path, plugin_id: str) -> list[Finding]:
    """Check the suite README's title and CI section (E4).

    Args:
        root: The repository root.
        plugin_id: The plugin directory name.

    Returns:
        One finding when the title names neither the plugin nor one of its skills, and one
        per CI claim the section does not make.
    """
    path = evals_dir(root, plugin_id) / README_NAME
    rel = f"{PLUGINS_DIRNAME}/{plugin_id}/{EVALS_DIRNAME}/{README_NAME}"
    if not path.is_file():
        return []
    text = path.read_text(encoding="utf-8")
    title = next((line for line in text.splitlines() if line.startswith("# ")), "")
    names = {plugin_id, *skill_names(root, plugin_id)}
    findings: list[Finding] = []
    if not any(name in title for name in names):
        findings.append(
            Finding("E4", rel, f"the title names neither {plugin_id!r} nor one of its skills")
        )
    if CI_SECTION not in text:
        findings.append(Finding("E4", rel, f"no `{CI_SECTION}` section"))
        return findings
    findings.extend(
        Finding("E4", rel, f"the CI section never states {claim!r}")
        for claim in CI_REQUIRED_CLAIMS
        if claim not in text
    )
    return findings


def collect(root: Path, plugin_id: str) -> list[Finding]:
    """Run E1 to E4 over one plugin.

    Args:
        root: The repository root.
        plugin_id: The plugin directory name.

    Returns:
        Every finding, in invariant order.
    """
    return [
        *check_suite(root, plugin_id),
        *check_cases(root, plugin_id),
        *check_results_ignored(root, plugin_id),
        *check_readme(root, plugin_id),
    ]
