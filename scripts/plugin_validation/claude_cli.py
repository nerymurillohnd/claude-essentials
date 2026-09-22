"""The official CLI, wrapped: `claude plugin validate --strict`.

Manifest and hook *shape* belong to the CLI, and this repository adds invariants on top
rather than mirroring its schema (P6). The wrapper exists for three reasons: to resolve the
binary once, to turn a missing binary into one `error:` line instead of a traceback, and to
keep the marketplace root and every plugin in one list so `make validate-cli` cannot check
fewer things than it claims to.
"""

from __future__ import annotations

import shutil
import subprocess
from typing import TYPE_CHECKING, Final

from scripts.common.errors import ExecutableNotFoundError

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

CLI_NAME: Final = "claude"
"""The binary; CI pins its version through `CLAUDE_CODE_VERSION`."""

STRICT_FLAG: Final = "--strict"
"""Turns an unrecognized manifest field from a warning into an error."""

MARKETPLACE_TARGET: Final = "."
"""The marketplace root, validated as a whole before the individual plugins."""


def executable() -> str:
    """Resolve the Claude Code CLI.

    Returns:
        Its absolute path.

    Raises:
        ExecutableNotFoundError: If `claude` is not on PATH.
    """
    found = shutil.which(CLI_NAME)
    if found is None:
        raise ExecutableNotFoundError(CLI_NAME)
    return found


TEMPLATE_SHAPES_DIR: Final = "templates"
"""Where the plugin shapes live; each carries a `.claude-plugin/plugin.json`."""


def template_shapes(root: Path) -> list[str]:
    """List the template folders that are plugin-shaped.

    Anthropic's `validate-plugins` action treats every folder holding a
    `.claude-plugin/plugin.json` as a plugin and validates it when it changes, so the
    shapes under `templates/` must pass the same `--strict` check the plugins do. Found
    in CI on 2026-09-22: the shapes' `REPLACE-WITH-*` names were not kebab-case.

    Args:
        root: The repository root.

    Returns:
        `templates/<shape>` for every shape with a manifest, sorted.
    """
    return sorted(
        manifest.parent.parent.relative_to(root).as_posix()
        for manifest in (root / TEMPLATE_SHAPES_DIR).glob("*/.claude-plugin/plugin.json")
    )


def targets(root: Path, plugin_ids_: Sequence[str]) -> list[str]:
    """List what `claude plugin validate` is run against.

    Args:
        root: The repository root.
        plugin_ids_: The plugin directory names.

    Returns:
        The marketplace root, each plugin directory, then each plugin-shaped template,
        as relative paths.
    """
    return [
        MARKETPLACE_TARGET,
        *(f"plugins/{plugin_id}" for plugin_id in plugin_ids_),
        *template_shapes(root),
    ]


def validate(root: Path, target: str) -> tuple[bool, str]:
    """Run `claude plugin validate <target> --strict`.

    Args:
        root: The directory the CLI runs in.
        target: The path to validate, relative to `root`.

    Returns:
        Whether the CLI accepted it, and the output it printed.

    Raises:
        ExecutableNotFoundError: If `claude` is not on PATH.
    """
    binary = executable()
    try:
        completed = subprocess.run(
            ["/usr/bin/claude", "plugin", "validate", target, STRICT_FLAG],
            executable=binary,
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as error:
        return False, str(error)
    return completed.returncode == 0, (completed.stdout + completed.stderr).strip()
