# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Single entry point for every gate. CI runs exactly these commands.

Usage:
  uv run scripts/check.py                  # every gate (same as CI)
  uv run scripts/check.py <gate> [...]     # selected gates, in the given order
  uv run scripts/check.py test-install     # isolated install test (tests committed HEAD)
  uv run scripts/check.py clean            # remove caches and orphaned test directories
  uv run scripts/check.py ci-tools         # CI only: install the pinned tool versions
  uv run scripts/check.py --list           # list the gates

The repository has no dependency manifest (docs/adr/0008-validation-stack.md):
tools are resolved by name on PATH locally and installed at the pinned
versions below on CI runners.
"""

from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path

import repo

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
TEMP_PREFIXES = ("claude-essentials-install-", "new-plugin-", "gate-fixture-")

SCRIPTS = repo.ROOT / "scripts"


def _uv_script(name: str, *args: str) -> list[str]:
    return ["uv", "run", str(SCRIPTS / name), *args]


def _validate() -> list[list[str]]:
    commands = [["claude", "plugin", "validate", ".", "--strict"]]
    for plugin in repo.plugin_dirs():
        commands.append(
            [
                "claude",
                "plugin",
                "validate",
                str(plugin.relative_to(repo.ROOT)),
                "--strict",
            ]
        )
    return commands


def _schemas() -> list[list[str]]:
    github = repo.ROOT / ".github"
    workflows = sorted(
        str(p.relative_to(repo.ROOT)) for p in (github / "workflows").glob("*.yml")
    )
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
        lambda: [_uv_script("check_repo.py")],
    ),
    "readmes": (
        "Generated README content is up to date",
        lambda: [_uv_script("sync_readmes.py", "--check")],
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
            ["ruff", "check", "."],
            ["ruff", "format", "--check", "."],
            ["basedpyright", "--warnings"],
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
    for command in commands:
        print(f"$ {' '.join(command)}", flush=True)
        result = repo.run(command, check=False)
        output = (result.stdout + result.stderr).rstrip()
        if output:
            print(output, flush=True)
        if result.returncode != 0:
            print(f"✘ exit {result.returncode}: {' '.join(command)}", flush=True)
            return False
    return True


def run_gates(names: list[str]) -> int:
    failed: list[str] = []
    for name in names:
        description, commands = GATES[name]
        print(f"\n=== {name}: {description}", flush=True)
        if not run_commands(commands()):
            failed.append(name)
    print()
    if failed:
        print(f"check: {len(failed)} gate(s) failed: {', '.join(failed)}")
        return 1
    print(f"check: all {len(names)} gate(s) passed")
    return 0


def orphaned_temp_dirs() -> list[Path]:
    """Temporary directories left behind by the scripts or tests."""
    base = Path(tempfile.gettempdir())
    return sorted(p for p in base.iterdir() if p.name.startswith(TEMP_PREFIXES))


def clean() -> int:
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
        print("✘ could not remove: " + ", ".join(str(p) for p in leftovers))
        return 1
    print(
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
            print(f"  {name:<10} {description}")
        return 0
    if targets == ["test-install"]:
        return 0 if run_commands([_uv_script("test_install.py")]) else 1
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
