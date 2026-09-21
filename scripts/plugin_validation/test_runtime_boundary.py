"""B1: what a plugin may assume a user's machine already has (§2.1)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from scripts.common.plugins import plugin_ids, repo_root
from scripts.plugin_validation.conftest import PLUGIN_ID, track
from scripts.plugin_validation.runtime_boundary import (
    DEBT_TAG,
    check_forbidden,
    check_imports,
    check_shebangs,
    collect,
    imported_modules,
    invoked_binaries,
    python_commands,
    shell_commands,
)

if TYPE_CHECKING:
    from pathlib import Path

CCDOCS = "plugins/agent-self-knowledge/skills/claude-code-docs/scripts/ccdocs.py"


def test_a_message_mentioning_uv_is_not_an_invocation() -> None:
    """`die "install it with uv tool install ruff"` is prose, not a dependency."""
    source = "die \"ruff not found. Install it (for example 'uv tool install ruff').\"\n"
    assert "uv" not in shell_commands(source)


def test_a_command_substitution_stays_visible() -> None:
    """A double-quoted segment that runs something is kept in the scan."""
    assert "uv" in shell_commands('value="$(uv python find 3.9)"\n')


def test_python3_is_not_read_as_python() -> None:
    """The forbidden word is the bare spelling; `python3` is the portable one."""
    found = shell_commands("python3 script.py\n")
    assert "python3" in found
    assert "python" not in found


def test_a_subprocess_call_is_read_from_the_syntax_tree() -> None:
    """A list of tool names used as data is not an invocation of those tools."""
    source = 'import subprocess\nNAMES = ["npx"]\nsubprocess.run(["git", "status"])\n'
    assert python_commands(source) == {"git"}


def test_imports_are_reduced_to_their_package() -> None:
    """A submodule import still names the package the floor has to provide."""
    assert imported_modules("import urllib.request\nfrom json import loads\n") == {"urllib", "json"}


def test_the_scratch_plugin_is_inside_the_boundary(scratch: Path) -> None:
    """The fixture is the baseline the uv-shebang probe is measured against.

    Args:
        scratch: The scratch repository root.
    """
    assert collect(scratch, PLUGIN_ID) == []


def test_a_uv_run_shebang_is_refused(scratch: Path) -> None:
    """`#!/usr/bin/env -S uv run --script` assumes a tool the user never installed.

    Args:
        scratch: The scratch repository root.
    """
    path = scratch / "plugins" / PLUGIN_ID / "hooks" / "handler.sh"
    _ = path.write_text("#!/usr/bin/env -S uv run --script\nexit 0\n", encoding="utf-8")
    assert [finding.invariant_id for finding in check_shebangs(scratch, PLUGIN_ID)] == ["B1"]


def test_a_forbidden_binary_in_a_script_is_refused(scratch: Path) -> None:
    """A shipped script that runs `npx` never fires on a machine without Node.

    Args:
        scratch: The scratch repository root.
    """
    path = scratch / "plugins" / PLUGIN_ID / "hooks" / "handler.sh"
    _ = path.write_text("#!/usr/bin/env bash\nnpx something\n", encoding="utf-8")
    assert [finding.invariant_id for finding in check_forbidden(scratch, PLUGIN_ID)] == ["B1"]


def test_a_non_stdlib_import_is_refused(scratch: Path) -> None:
    """A shipped script may import only what a stock `python3` already has.

    Args:
        scratch: The scratch repository root.
    """
    path = scratch / "plugins" / PLUGIN_ID / "hooks" / "helper.py"
    track(scratch, path, "#!/usr/bin/env python3\nimport requests\n", executable=True)
    assert "B1" in [finding.invariant_id for finding in check_imports(scratch, PLUGIN_ID)]


def test_the_shipped_python_is_reported_as_advisory_debt() -> None:
    """`ccdocs.py` declares a shebang without the exec bit; that is Follow-up PR #1."""
    findings = check_shebangs(repo_root(), "agent-self-knowledge")
    assert [(finding.path, finding.severity) for finding in findings] == [(CCDOCS, "warning")]
    assert DEBT_TAG in findings[0].message


def test_every_shipped_plugin_stays_inside_the_boundary() -> None:
    """No published plugin has an error-level boundary finding today."""
    root = repo_root()
    errors = [
        finding
        for plugin_id in plugin_ids(root)
        for finding in collect(root, plugin_id)
        if finding.severity == "error"
    ]
    assert errors == []


def test_the_binaries_each_plugin_invokes_are_the_ones_its_readme_lists() -> None:
    """The set R5 is fed with is measured, not declared."""
    root = repo_root()
    assert invoked_binaries(root, "verify-completion") == {"bash", "jq"}
    assert invoked_binaries(root, "agent-self-knowledge") == {"curl", "python3"}
