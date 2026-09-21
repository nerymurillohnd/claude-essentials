"""A scratch marketplace on disk, so a negative probe can be seeded and then removed.

Every validator in this area reads the working tree through git, so a fixture that only
wrote files would exercise a different code path than the gate does. The fixture therefore
builds a real repository: `git init`, the files, `git add`, a commit and a tag, which is
what `C2` needs to compare a released section with its own tag.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from typing import TYPE_CHECKING, Final

import pytest

from scripts.common.plugins import repo_root
from scripts.plugin_validation.kind import LICENSE_TEMPLATE, license_text

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

PLUGIN_ID: Final = "scratch-plugin"
"""The single plugin every scratch tree ships."""

SKILL_ID: Final = "scratch-skill"
"""The single skill that plugin ships."""

VERSION: Final = "0.1.0"
"""The plugin's only released version, which the fixture also tags."""

RELEASE_DATE: Final = "2026-09-20"
"""The date of that release, used in the CHANGELOG heading."""

MANIFEST: Final[dict[str, object]] = {
    "name": PLUGIN_ID,
    "displayName": "Scratch Plugin",
    "description": "A plugin that exists only so a probe can be seeded and then removed.",
    "version": VERSION,
    "author": {"name": "Nery Samuel Murillo Tejada"},
    "license": "Apache-2.0",
    "homepage": f"https://github.com/nerymurillohnd/claude-essentials/tree/main/plugins/{PLUGIN_ID}",
    "metadata": {"marketplace": {"category": "quality", "tags": ["scratch"]}},
}
"""A manifest that satisfies the catalog invariants, so probes are the only failures."""

SKILL: Final = """---
name: scratch-skill
description: Check one thing and report it, so a probe has a skill to break.
when_to_use: When a test needs a skill whose frontmatter is valid before a probe edits it.
allowed-tools: Read Grep
---

# Scratch skill

Body.
"""
"""A skill whose frontmatter passes S1 to S4 until a probe changes it."""

HOOKS: Final[dict[str, object]] = {
    "description": "scratch hooks",
    "hooks": {
        "PostToolUse": [
            {
                "matcher": "Edit|Write",
                "hooks": [
                    {
                        "type": "command",
                        "command": 'bash "${CLAUDE_PLUGIN_ROOT}/hooks/handler.sh"',
                        "timeout": 5,
                    }
                ],
            }
        ]
    },
}
"""A hook file that passes H1 to H6 until a probe changes it."""

HANDLER: Final = "#!/usr/bin/env bash\nset -euo pipefail\nexit 0\n"
"""The handler the hook command resolves to; H5 requires it to exist and be executable."""

FRAGMENT: Final[dict[str, object]] = {
    "matcher": "Bash",
    "hooks": [
        {
            "type": "command",
            "command": 'bash "${CLAUDE_PLUGIN_ROOT}/hooks/handler.sh"',
            "timeout": 5,
        }
    ],
}
"""A settings fragment, the second surface H1 to H6 cover."""

WORKFLOW: Final = """export const meta = {
  name: "scratch",
  description: "A workflow that runs against the stub runtime.",
  phases: [{ title: "Check", detail: "one stub agent" }],
};

const report = await agent("check something", { label: "check", phase: "Check" });
log("done");
return { report: report };
"""
"""A workflow that passes W1 until a probe changes it."""

README: Final = f"""# 🧪 Scratch Plugin

[![Version](https://img.shields.io/badge/dynamic/json?url=x&query=%24.version&label=version&color=blue)](CHANGELOG.md)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Kind](https://img.shields.io/badge/kind-bundle-8A2BE2)](../../docs/decisions/adr-0001-marketplace-distribution-model.md)
[![Claude Code](https://img.shields.io/badge/Claude_Code-not_tested-D97757?logo=claude&logoColor=white)](#-compatibility)
[![Claude Cowork](https://img.shields.io/badge/Claude_Cowork-not_tested-D97757?logo=claude&logoColor=white)](#-compatibility)
![Network](https://img.shields.io/badge/network-none-lightgrey)

**Kind:** `bundle` — a full workflow: multiple components working together.

## 🎯 What it does

Nothing; it exists for the probes.

## 🚫 What it does not do

Nothing at all.

## ⚡ Installation

None.

## 🧠 Skills

| Skill | Invoke |
| --- | --- |
| `{SKILL_ID}` | `/{PLUGIN_ID}:{SKILL_ID}` |

## 🤖 Agents

None — this plugin ships no agents.

## 🪝 Hooks and side effects

One `PostToolUse` hook. Windows without Git Bash is not supported: the hooks run `bash`.

## 🔌 MCP, permissions, and network

None — no MCP servers, no network access, no credentials.

## 🧩 Other components

One workflow.

## 📋 Requirements

| Requirement | Minimum | Check | Why |
| --- | --- | --- | --- |
| Bash | 3.2 | `bash --version` | Runs the handler. |

## ✅ Verification

Run the handler.

## 🧭 Compatibility

| Surface | Status | Last verified | Notes |
| --- | --- | --- | --- |
| Claude Code | 🧪 Not tested | — | Nothing is verified. |
| Claude Code on Windows without Git Bash | ❌ Not supported | — | The hooks run `bash`. |
| Claude Cowork | 🧪 Not tested | — | Nothing is verified. |

## 💡 Examples

None.

## 🔐 Security

Reads nothing.

## 🚧 Limitations

| Limitation | What you'll see | Safe recovery |
| --- | --- | --- |
| `bash` is absent | The hook never runs | Install Git Bash |

## 📝 Changelog

See [CHANGELOG.md](CHANGELOG.md).

## 📄 License

[Apache-2.0](LICENSE).
"""
"""A README shaped like the template, so R-family probes are the only R findings."""

CHANGELOG: Final = f"""# Changelog

All notable changes to this plugin are documented here.

## [Unreleased]

## [{VERSION}] - {RELEASE_DATE}

### Added

- The first release.

[Unreleased]: https://github.com/nerymurillohnd/claude-essentials/compare/{PLUGIN_ID}--v{VERSION}...HEAD
[{VERSION}]: https://github.com/nerymurillohnd/claude-essentials/tree/{PLUGIN_ID}--v{VERSION}
"""
"""A CHANGELOG whose released body C2 can compare against the tag the fixture creates."""

GRADER: Final = """---
type: tool_used
tool: Skill
input_match: scratch-skill
---
"""
"""A grader that asserts the skill fired."""

MUST_NOT_FIRE_GRADER: Final = """---
type: tool_used
tool: Skill
input_match: scratch-skill
min: 0
max: 0
arm: both
---
"""
"""The grader that makes a case a must-not-fire case (E1)."""

EVALS_README: Final = f"""# Evals — `{PLUGIN_ID}`

One flow.

## CI policy

- **Conditional, never blocking:** a change under `evals/**` selects no run.
"""
"""A suite README that satisfies E4."""


def _git(root: Path, args: Sequence[str]) -> None:
    """Run a git command in the scratch tree and fail the test if it does not work.

    Args:
        root: The scratch repository.
        args: Arguments after the binary.
    """
    binary = shutil.which("git")
    assert binary is not None, "git is required to build the scratch repository"
    environment = dict(os.environ)
    environment.update(
        {
            "GIT_AUTHOR_NAME": "Probe",
            "GIT_AUTHOR_EMAIL": "probe@example.invalid",
            "GIT_COMMITTER_NAME": "Probe",
            "GIT_COMMITTER_EMAIL": "probe@example.invalid",
        }
    )
    completed = subprocess.run(
        ["/usr/bin/git", *args],
        executable=binary,
        cwd=root,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr


def _write(path: Path, text: str, *, executable: bool = False) -> None:
    """Write a file, creating its parents.

    Args:
        path: The file to write.
        text: Its contents.
        executable: Whether to set the exec bit.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text(text, encoding="utf-8")
    if executable:
        path.chmod(0o755)


def _build_case(base: Path, name: str, *, must_not_fire: bool) -> None:
    """Write one eval case.

    Args:
        base: The suite directory.
        name: The case directory name.
        must_not_fire: Whether its grader asserts the plugin stayed quiet.
    """
    _write(base / name / "prompt.md", "Do something unrelated.\n")
    grader = MUST_NOT_FIRE_GRADER if must_not_fire else GRADER
    _write(base / name / "graders" / "fired.md", grader)


def track(root: Path, path: Path, text: str, *, executable: bool = False) -> None:
    """Write a file into the scratch plugin and make git track it.

    Every validator reads the working tree through `git ls-files`, so a file that is only
    written is invisible to them.

    Args:
        root: The scratch repository root.
        path: The file to write.
        text: Its contents.
        executable: Whether to set the exec bit.
    """
    _write(path, text, executable=executable)
    _git(root, ["add", "--", str(path.relative_to(root))])


@pytest.fixture
def scratch(tmp_path: Path) -> Path:
    """Build a scratch marketplace with one plugin that passes the probed invariants.

    Args:
        tmp_path: pytest's per-test directory.

    Returns:
        The scratch repository root.
    """
    root = tmp_path / "marketplace"
    plugin = root / "plugins" / PLUGIN_ID
    _write(root / LICENSE_TEMPLATE, (repo_root() / LICENSE_TEMPLATE).read_text(encoding="utf-8"))
    _write(plugin / "LICENSE", license_text(root))
    _write(plugin / ".claude-plugin" / "plugin.json", json.dumps(MANIFEST, indent=2) + "\n")
    _write(plugin / "README.md", README)
    _write(plugin / "CHANGELOG.md", CHANGELOG)
    _write(plugin / "skills" / SKILL_ID / "SKILL.md", SKILL)
    _write(plugin / "hooks" / "hooks.json", json.dumps(HOOKS, indent=2) + "\n")
    _write(plugin / "hooks" / "handler.sh", HANDLER, executable=True)
    _write(
        plugin / "skills" / SKILL_ID / "assets" / "settings-fragment.json",
        json.dumps(FRAGMENT, indent=2) + "\n",
    )
    _write(plugin / "workflows" / "scratch.js", WORKFLOW)
    _write(plugin / "evals" / "README.md", EVALS_README)
    _build_case(plugin / "evals", "01-fires", must_not_fire=False)
    _build_case(plugin / "evals", "02-fires-again", must_not_fire=False)
    _build_case(plugin / "evals", "90-stays-quiet", must_not_fire=True)
    _write(root / ".gitignore", "**/evals/results/\n")
    _git(root, ["init", "--quiet"])
    _git(root, ["add", "-A"])
    _git(root, ["commit", "--quiet", "-m", "scratch"])
    _git(root, ["tag", f"{PLUGIN_ID}--v{VERSION}"])
    return root
