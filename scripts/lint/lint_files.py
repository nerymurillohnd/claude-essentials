"""`make lint`, `make lint-staged`, `make fix` and `make fix-file`: one entrypoint, six IDs.

What this gate checks is the part of the repository no parser of plugin manifests looks at:
the bytes of every file, the shell scripts, the JSON form, and the workflows. Ruff and
basedpyright own the Python half and `make lint`/`make types` run them directly over an
explicit file list (§A7); `--staged` folds them in as well, because the commit guard has to
refuse a commit for a type error too, and running them over the staged set alone keeps that
check inside a hook's budget.

Three file sets, one code path:

* no flag — every tracked or new file, which is what `make lint` and CI check;
* `--staged` — staged, modified and untracked files, which is what a commit could include;
* `--file <path>` — one file, which is what the `PostToolUse` hook rewrites.

`--fix --file` is the one mode that writes *and* reports: the hook runs it after every edit
and has to say what the writers could not repair, so it exits non-zero when anything is left.
`--fix` over the whole tree stays a writer, because `make lint` is what follows it everywhere.
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
from scripts.common.plugins import git_output, repo_root, working_files
from scripts.lint import json_files, shell_files, text_files, workflows_files
from scripts.lint.tools import run, tool_path, venv_env

if TYPE_CHECKING:
    from collections.abc import Sequence

LINT_INVARIANTS: Final[tuple[tuple[str, str, str], ...]] = (
    ("L1", "shell scripts pass ShellCheck and shfmt", "a hook that silently does nothing"),
    ("L2", "every JSON file is in canonical form", "a diff that is pure whitespace"),
    ("L3", "text files are UTF-8, LF, final newline, no stray control bytes", "invisible bytes"),
    (
        "L4",
        "workflows pass actionlint and the zizmor ignore policy",
        "a workflow that only fails on the runner",
    ),
    (
        "L5",
        "the staged Python passes `ruff format --check` and `ruff check`",
        "a commit the gate then rejects",
    ),
    ("L6", "the staged Python passes basedpyright", "a type error reaching `main`"),
)
"""The lint registry: ID, what it checks, and the defect it catches (P14)."""

PYTHON_SUFFIX: Final = ".py"
"""Which staged files L5 and L6 apply to."""

PYTHON_ROOTS: Final[tuple[str, ...]] = ("scripts/", "plugins/")
"""The trees `[tool.basedpyright] include` covers: the maintainer's Python and every plugin's.

Shipped Python is checked like the maintainer's, against the repository's Python, which is
also the floor each plugin declares (enforced by `run_plugin_suites`)."""

OUTPUT_BUDGET: Final = 4000
"""How much of a tool's own output one finding carries."""


def registry_lines() -> list[str]:
    """Render the lint registry for `--list`.

    Returns:
        One line per ID, in family order.
    """
    return [f"{ident}  {check} — {defect}" for ident, check, defect in LINT_INVARIANTS]


def all_paths(root: Path) -> list[str]:
    """List every file the gate checks by default.

    Args:
        root: The repository root.

    Returns:
        Sorted repository-relative paths.
    """
    return working_files(root)


def changed_paths(root: Path) -> list[str]:
    """List the files a commit made right now could include.

    At `PreToolUse` time a chained `git add … && git commit` has staged nothing yet, so the
    modified and untracked files count as well. Each listing runs on its own, so a failure
    raises rather than being masked by a pipeline (the guard fails closed).

    Args:
        root: The repository root.

    Returns:
        Sorted repository-relative paths that exist as files.

    Raises:
        GitCommandFailedError: If either listing fails.
    """
    staged = git_output(root, ["diff", "--cached", "--name-only", "-z", "--diff-filter=ACMR"])
    dirty = git_output(root, ["ls-files", "--modified", "--others", "--exclude-standard", "-z"])
    names = {entry for entry in f"{staged}{dirty}".split("\0") if entry}
    return sorted(name for name in names if (root / name).is_file())


def python_paths(paths: Sequence[str]) -> list[str]:
    """Keep the Python the gates cover out of a file set.

    Args:
        paths: Repository-relative paths.

    Returns:
        The `.py` files under `scripts/` and `plugins/`, which is what the type policy covers.
    """
    return [rel for rel in paths if rel.endswith(PYTHON_SUFFIX) and rel.startswith(PYTHON_ROOTS)]


def check_python(root: Path, paths: Sequence[str]) -> list[Finding]:
    """Run Ruff and basedpyright over a file set (L5, L6).

    Args:
        root: The repository root.
        paths: The `.py` files to check.

    Returns:
        One finding per tool that reported something, carrying that tool's own output.

    Raises:
        ExecutableNotFoundError: If a locked binary is missing.
    """
    if not paths:
        return []
    findings: list[Finding] = []
    ruff = tool_path(root, "ruff")
    for args in (["format", "--check", *paths], ["check", *paths]):
        completed = run(ruff, args, cwd=root)
        if completed.returncode != 0:
            output = f"{completed.stdout}{completed.stderr}".strip()
            findings.append(
                Finding("L5", None, f"`ruff {args[0]}` reports:\n{output[:OUTPUT_BUDGET]}")
            )
    types = run(tool_path(root, "basedpyright"), list(paths), cwd=root, env=venv_env(root))
    if types.returncode != 0:
        output = f"{types.stdout}{types.stderr}".strip()
        findings.append(Finding("L6", None, f"basedpyright reports:\n{output[:OUTPUT_BUDGET]}"))
    return findings


def collect(root: Path, paths: Sequence[str], *, python: bool = False) -> list[Finding]:
    """Run every check over one file set.

    Args:
        root: The repository root.
        paths: Repository-relative paths to check.
        python: Whether to add the Ruff and basedpyright checks (L5, L6).

    Returns:
        Every finding, in ID order.
    """
    findings = [
        *shell_files.check(root, paths),
        *json_files.check(root, paths),
        *text_files.check(root, paths),
        *workflows_files.check(root, paths),
    ]
    if python:
        findings.extend(check_python(root, python_paths(paths)))
    return findings


def fix_python(root: Path, paths: Sequence[str]) -> list[str]:
    """Run Ruff's writers over a Python file set.

    Only the safe fixes: `--unsafe-fixes` rewrites code in ways that can change behaviour, so
    it is never part of a target and never part of a hook.

    The lint fixes run before the formatter, which is the order Ruff's own documentation
    recommends and the only one that converges in a single pass: removing an unused import
    leaves the blank lines around it for the formatter to close up, so formatting first would
    leave the file needing a second run and the hook reporting a defect it had just created.

    Args:
        root: The repository root.
        paths: The `.py` files to rewrite.

    Returns:
        The repository-relative paths whose bytes changed.

    Raises:
        ExecutableNotFoundError: If `.venv/bin/ruff` is missing.
    """
    if not paths:
        return []
    before = {rel: (root / rel).read_bytes() for rel in paths}
    ruff = tool_path(root, "ruff")
    _ = run(ruff, ["check", "--fix", *paths], cwd=root)
    _ = run(ruff, ["format", *paths], cwd=root)
    return [rel for rel in paths if (root / rel).read_bytes() != before[rel]]


def apply_fixes(
    root: Path, paths: Sequence[str], *, dry_run: bool = False, python: bool = False
) -> list[str]:
    """Run every writer over one file set.

    Text comes last: shfmt and the canonical JSON writer both end their output with a final
    newline and no trailing whitespace, so nothing they write can then need repairing.

    Args:
        root: The repository root.
        paths: Repository-relative paths to rewrite.
        dry_run: When true, report what would change and write nothing.
        python: Whether to add Ruff's writers. `make fix` runs them itself over the whole
            tree, so only the single-file path (the `PostToolUse` hook) asks for them here.

    Returns:
        Sorted repository-relative paths that changed, or would.
    """
    changed = {
        *shell_files.fix(root, paths, dry_run=dry_run),
        *json_files.fix(root, paths, dry_run=dry_run),
        *text_files.fix(root, paths, dry_run=dry_run),
    }
    if python and not dry_run:
        changed.update(fix_python(root, python_paths(paths)))
    return sorted(changed)


def select_paths(root: Path, *, staged: bool, single: str | None) -> list[str]:
    """Resolve which file set the command line asked for.

    Args:
        root: The repository root.
        staged: Whether to use the commit set rather than the whole tree.
        single: One repository-relative path, or None.

    Returns:
        Repository-relative paths.

    Raises:
        MissingPathError: If `--file` names something that is not a file.
    """
    if single is not None:
        rel = single.removeprefix(f"{root}/")
        if not (root / rel).is_file():
            raise MissingPathError(Path(single), "the file to check")
        return [rel]
    return changed_paths(root) if staged else all_paths(root)


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
        prog="python -m scripts.lint.lint_files",
        description="Check the bytes, shell scripts, JSON form and workflows of this tree.",
    )
    _ = parser.add_argument("--list", action="store_true", help="print the lint registry")
    _ = parser.add_argument("--root", default=None, help="check this tree instead of this one")
    _ = parser.add_argument(
        "--staged", action="store_true", help="check what a commit could include, Python included"
    )
    _ = parser.add_argument("--file", default=None, help="check exactly one file")
    _ = parser.add_argument("--fix", action="store_true", help="rewrite what can be rewritten")
    _ = parser.add_argument(
        "--dry-run", action="store_true", help="with --fix: list what would change"
    )
    return parser.parse_args(argv)


def _report(findings: Sequence[Finding]) -> int:
    """Print every finding and decide the exit status.

    Args:
        findings: What the checks returned.

    Returns:
        1 when anything is an error, 0 otherwise.
    """
    for finding in findings:
        print(format_finding(finding))
    if any(finding.severity == "error" for finding in findings):
        return int(ExitCode.FINDINGS)
    warnings = sum(1 for finding in findings if finding.severity == "warning")
    print(f"lint: every file passes ({warnings} warning(s))")
    return int(ExitCode.OK)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the lint gate.

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
    single = values["file"]
    try:
        root = Path(raw_root) if isinstance(raw_root, str) else repo_root()
        paths = select_paths(
            root,
            staged=values["staged"] is True,
            single=single if isinstance(single, str) else None,
        )
        if values["fix"]:
            one_file = isinstance(single, str)
            changed = apply_fixes(root, paths, dry_run=values["dry_run"] is True, python=one_file)
            verb = "would rewrite" if values["dry_run"] else "rewrote"
            for rel in changed:
                print(f"{verb} {rel}")
            print(f"lint --fix: {len(changed)} file(s)")
            if not one_file or values["dry_run"] is True:
                return int(ExitCode.OK)
            # A single-file fix is the PostToolUse writer, and the hook has to know what is
            # left over, so it reports afterwards. A whole-tree fix stays a writer only:
            # `make lint` is the next step everywhere it is used.
            return _report(collect(root, paths, python=True))
        findings = collect(root, paths, python=values["staged"] is True)
    except (MaintainerError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return int(ExitCode.USAGE)
    return _report(findings)


if __name__ == "__main__":
    raise SystemExit(main())
