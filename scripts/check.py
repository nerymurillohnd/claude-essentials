#!/usr/bin/env python3
"""Single entry point for every gate. CI runs exactly these commands.

Usage:
  scripts/check.py                  # every gate (same as CI)
  scripts/check.py <gate> [...]     # selected gates, in the given order
  scripts/check.py test-install     # isolated install test (tests committed HEAD)
  scripts/check.py clean            # remove caches and orphaned test directories
  scripts/check.py ci-tools         # CI only: install the latest tool releases
  scripts/check.py --list           # list the gates

The repository has no dependency manifest and pins no tool version
(docs/adr/decisions/ADR_2026-10-05_unpinned-tooling-and-shebang-interpreters.md):
every gate runs the tool found by name on PATH, and CI runners install the latest
release of each tool.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import sys
import tempfile
from typing import TYPE_CHECKING

import repo

if TYPE_CHECKING:
    from collections.abc import Callable

# The latest actionlint release for CI runners, verified against the checksums file the
# release publishes (the download script picks a version written into the script itself).
ACTIONLINT_INSTALL = """\
set -euo pipefail
assets=$(mktemp -d)
trap 'rm -rf "${assets}"' EXIT
gh release download --repo rhysd/actionlint --dir "${assets}" \\
  --pattern 'actionlint_*_linux_amd64.tar.gz' --pattern 'actionlint_*_checksums.txt'
(cd "${assets}" && sha256sum --check --ignore-missing actionlint_*_checksums.txt)
tar -xzf "${assets}"/actionlint_*_linux_amd64.tar.gz -C "${HOME}/.local/bin" actionlint
"""

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
    return [str(SCRIPTS / name), *args]


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
        "Docs match the code: Claude Code minimum, gate list, script names, rule paths, links",
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
                "zizmor",
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
        try:
            result = repo.run(command, check=False)
        except FileNotFoundError:
            repo.emit(f"✘ {command[0]} is not on PATH; install it (docs/testing.md, Set up)")
            return False
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


# The maintainer's global ruff configuration, stored in the RUFF_CONFIG Actions variable
# (`gh variable set RUFF_CONFIG < ~/.config/ruff/ruff.toml`): the repository has no ruff.toml,
# so ruff falls back to this user-level file on CI exactly as on the maintainer's machine.
RUFF_CONFIG_VARIABLE = "RUFF_CONFIG"


def ruff_user_config(env: dict[str, str]) -> Path:
    """Where ruff looks for its user-level configuration on Linux and macOS."""
    base = env.get("XDG_CONFIG_HOME") or str(Path(env.get("HOME") or Path.home()) / ".config")
    return Path(base) / "ruff" / "ruff.toml"


def write_ruff_config(env: dict[str, str]) -> Path | None:
    """Write the RUFF_CONFIG variable to ruff's user-level configuration file."""
    config = env.get(RUFF_CONFIG_VARIABLE, "")
    if not config.strip():
        command = f"gh variable set {RUFF_CONFIG_VARIABLE} < ~/.config/ruff/ruff.toml"
        repo.emit(f"✘ {RUFF_CONFIG_VARIABLE} is empty; set it with `{command}`")
        return None
    target = ruff_user_config(env)
    target.parent.mkdir(parents=True, exist_ok=True)
    _ = target.write_text(config.rstrip("\n") + "\n", encoding="utf-8")
    return target


def ruff_uses(target: Path) -> bool:
    """True when ruff resolves `target` as the configuration for the repository's scripts."""
    result = repo.run(["ruff", "check", "--show-settings", str(SCRIPTS / "check.py")], check=False)
    expected = f'Settings path: "{target}"'
    if expected in result.stdout:
        repo.emit(f"ruff uses {target}")
        return True
    repo.emit(f"✘ ruff does not use {target}; check that the repository has no ruff config")
    return False


def ci_tools() -> int:
    """Install the latest release of every tool on a CI runner; never on a contributor's machine."""
    (Path.home() / ".local" / "bin").mkdir(parents=True, exist_ok=True)
    commands = [
        ["npm", "install", "--global", "--no-fund", "--no-audit", "prettier"],
        ["uv", "tool", "install", "ruff"],
        ["uv", "tool", "install", "basedpyright"],
        ["uv", "tool", "install", "check-jsonschema"],
        ["uv", "tool", "install", "zizmor"],
        ["bash", "-c", ACTIONLINT_INSTALL],
        ["bash", "-c", "curl -fsSL https://claude.ai/install.sh | bash"],
    ]
    if not run_commands(commands):
        return 1
    target = write_ruff_config(dict(os.environ))
    return 0 if target is not None and ruff_uses(target) else 1


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
