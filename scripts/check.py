#!/usr/bin/env python3
"""Single entry point for every gate. CI runs exactly these commands.

Usage:
  python3 scripts/check.py                  # every gate (same as CI)
  python3 scripts/check.py <gate> [...]     # selected gates, in the given order
  python3 scripts/check.py test-install     # isolated install test (tests committed HEAD)
  python3 scripts/check.py clean            # remove caches and orphaned test directories
  python3 scripts/check.py ci-tools         # CI only: install the pinned tool versions
  python3 scripts/check.py --list           # list the gates

The repository has no dependency manifest
(docs/adr/decisions/ADR_2026-10-03_validation-stack.md): tools are
resolved by name on PATH locally and installed at the pinned versions below on
CI runners.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import sys
import tempfile
from typing import TYPE_CHECKING

import repo

if TYPE_CHECKING:
    from collections.abc import Callable

CLAUDE_CODE_VERSION = repo.MIN_CLAUDE_CODE
PRETTIER_VERSION = "3.9.9"
ACTIONLINT_VERSION = "1.7.12"
ACTIONLINT_SCRIPT_SHA = "914e7df21a07ef503a81201c76d2b11c789d3fca"
RUFF_VERSION = "0.16.10"
BASEDPYRIGHT_VERSION = "1.40.1"
CHECK_JSONSCHEMA_VERSION = "0.38.2"
ZIZMOR_VERSION = "1.30.1"

# Prefixes of every temporary directory the scripts and tests create, so
# `clean` and the leftover check can find orphans (docs/testing.md#cleanup).
TEMP_PREFIXES = (
    "claude-essentials-install-",
    "claude-essentials-drive-",
    "claude-essentials-review-",
    "add-component-",
    "new-plugin-",
    "gate-fixture-",
)

SCRIPTS = repo.ROOT / "scripts"

# Python scripts without a `.py` extension. ruff and basedpyright skip them when they scan a
# directory, so the `python` gate passes each one by name; a test lists them from their shebang.
EXTENSIONLESS_SCRIPTS = ("scripts/git-hooks/commit-msg",)


def _script(name: str, *args: str) -> list[str]:
    return [sys.executable, str(SCRIPTS / name), *args]


def _validate() -> list[list[str]]:
    # `.claude` checks the repository's own project skills and agents (Claude Code 2.1.233+).
    targets = [
        ".",
        ".claude",
        *(str(plugin.relative_to(repo.ROOT)) for plugin in repo.plugin_dirs()),
    ]
    return [["claude", "plugin", "validate", target, "--strict"] for target in targets]


def _schemas() -> list[list[str]]:
    github = repo.ROOT / ".github"
    workflows = sorted(str(p.relative_to(repo.ROOT)) for p in (github / "workflows").glob("*.yml"))
    forms = sorted(
        str(p.relative_to(repo.ROOT))
        for p in (github / "ISSUE_TEMPLATE").glob("*.yml")
        if p.name != "config.yml"
    )
    return [
        ["check-jsonschema", "--builtin-schema", "vendor.github-workflows", *workflows],
        ["check-jsonschema", "--builtin-schema", "vendor.github-issue-forms", *forms],
        [
            "check-jsonschema",
            "--builtin-schema",
            "vendor.github-issue-config",
            ".github/ISSUE_TEMPLATE/config.yml",
        ],
    ]


GATES: dict[str, tuple[str, Callable[[], list[list[str]]]]] = {
    "validate": (
        "Official validator on the marketplace and each plugin (--strict)",
        _validate,
    ),
    "repo": (
        "Catalog, names, versions, changelogs, portability, labels, tags",
        lambda: [_script("check_repo.py")],
    ),
    "adrs": (
        "Architecture decision records: names, dates, status, sections, links",
        lambda: [_script("validate_adrs.py")],
    ),
    "readmes": (
        "Generated README content is up to date",
        lambda: [_script("sync_readmes.py", "--check")],
    ),
    "docs": (
        "Docs match the code: pins, gate list, script names, rule paths, links",
        lambda: [_script("check_docs.py")],
    ),
    "tests": (
        "Gate tests with injected defects",
        lambda: [
            [
                sys.executable,
                "-m",
                "unittest",
                "discover",
                "-s",
                "tests",
                "-t",
                ".",
                "-v",
            ]
        ],
    ),
    "format": (
        "Prettier check for Markdown, JSON and YAML",
        lambda: [["prettier", "--check", "."]],
    ),
    "python": (
        "ruff lint and format check, basedpyright with warnings as errors",
        lambda: [
            ["ruff", "check", ".", *EXTENSIONLESS_SCRIPTS],
            ["ruff", "format", "--check", ".", *EXTENSIONLESS_SCRIPTS],
            ["basedpyright", "--warnings"],
            ["basedpyright", "--warnings", *EXTENSIONLESS_SCRIPTS],
        ],
    ),
    "workflows": (
        "actionlint and the zizmor security audit",
        lambda: [
            ["actionlint"],
            [
                "uvx",
                f"zizmor@{ZIZMOR_VERSION}",
                "--offline",
                "--collect=workflows",
                ".github/workflows",
            ],
        ],
    ),
    "schemas": (
        "GitHub workflow and issue-form files against their JSON Schemas",
        _schemas,
    ),
}


def run_commands(commands: list[list[str]]) -> bool:
    """Run commands in order, echoing each one and its output; stop at the first failure."""
    for command in commands:
        repo.emit(f"$ {' '.join(command)}")
        result = repo.run(command, check=False)
        output = (result.stdout + result.stderr).rstrip()
        if output:
            repo.emit(output)
        if result.returncode != 0:
            repo.emit(f"✘ exit {result.returncode}: {' '.join(command)}")
            return False
    return True


def run_gates(names: list[str]) -> int:
    """Run the named gates and summarize which ones failed."""
    failed: list[str] = []
    for name in names:
        description, commands = GATES[name]
        repo.emit(f"\n=== {name}: {description}")
        if not run_commands(commands()):
            failed.append(name)
    repo.emit()
    if failed:
        repo.emit(f"check: {len(failed)} gate(s) failed: {', '.join(failed)}")
        return 1
    repo.emit(f"check: all {len(names)} gate(s) passed")
    return 0


def orphaned_temp_dirs() -> list[Path]:
    """Temporary directories left behind by the scripts or tests."""
    base = Path(tempfile.gettempdir())
    return sorted(p for p in base.iterdir() if p.name.startswith(TEMP_PREFIXES))


def clean() -> int:
    """Remove repository caches and orphaned temporary directories, then verify."""
    removed = 0
    for cache in [*repo.ROOT.rglob("__pycache__"), *repo.ROOT.rglob(".ruff_cache")]:
        if ".git" not in cache.parts and cache.is_dir():
            shutil.rmtree(cache)
            removed += 1
    for orphan in orphaned_temp_dirs():
        shutil.rmtree(orphan, ignore_errors=True)
        removed += 1
    leftovers = orphaned_temp_dirs()
    if leftovers:
        repo.emit("✘ could not remove: " + ", ".join(str(p) for p in leftovers))
        return 1
    repo.emit(
        f"clean: removed {removed} cache or temporary director{'y' if removed == 1 else 'ies'}"
    )
    return 0


def ci_tools() -> int:
    """Install the pinned tools on a CI runner. Never run it on a contributor's machine."""
    local_bin = Path.home() / ".local" / "bin"
    actionlint_script = f"https://raw.githubusercontent.com/rhysd/actionlint/{ACTIONLINT_SCRIPT_SHA}/scripts/download-actionlint.bash"
    commands = [
        [
            "npm",
            "install",
            "--global",
            "--no-fund",
            "--no-audit",
            f"prettier@{PRETTIER_VERSION}",
        ],
        ["uv", "tool", "install", f"ruff=={RUFF_VERSION}"],
        ["uv", "tool", "install", f"basedpyright=={BASEDPYRIGHT_VERSION}"],
        ["uv", "tool", "install", f"check-jsonschema=={CHECK_JSONSCHEMA_VERSION}"],
        [
            "bash",
            "-c",
            f'curl -fsSL "{actionlint_script}" | bash -s -- "{ACTIONLINT_VERSION}" "{local_bin}"',
        ],
        [
            "bash",
            "-c",
            f'curl -fsSL https://claude.ai/install.sh | bash -s "{CLAUDE_CODE_VERSION}"',
        ],
    ]
    return 0 if run_commands(commands) else 1


def main() -> int:
    """Run the selected gates or command."""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    _ = parser.add_argument(
        "targets", nargs="*", help="gates or a command: test-install, clean, ci-tools"
    )
    _ = parser.add_argument("--list", action="store_true", help="list the gates")
    args = parser.parse_args()
    targets: list[str] = args.targets  # pyright: ignore[reportAny]  # argparse Namespace attributes are Any
    list_only: bool = args.list  # pyright: ignore[reportAny]  # argparse Namespace attributes are Any

    if list_only:
        for name, (description, _commands) in GATES.items():
            repo.emit(f"  {name:<10} {description}")
        return 0
    if targets == ["test-install"]:
        return 0 if run_commands([_script("test_install.py")]) else 1
    if targets == ["clean"]:
        return clean()
    if targets == ["ci-tools"]:
        return ci_tools()
    unknown = [t for t in targets if t not in GATES]
    if unknown:
        parser.error(f"unknown target(s): {', '.join(unknown)}; use --list")
    return run_gates(targets or list(GATES))


if __name__ == "__main__":
    sys.exit(main())
