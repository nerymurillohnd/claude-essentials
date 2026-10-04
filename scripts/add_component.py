#!/usr/bin/env python3
"""Add a skill or an agent to an existing plugin with the official generator.

Usage:
  python3 scripts/add_component.py <plugin> skill|agent <name> --description "<text>"

Like new_plugin.py, it runs `claude plugin init --with skills|agents` in a throwaway
HOME and CLAUDE_CONFIG_DIR, then copies the generated example into
plugins/<plugin>/ under the new name. It adds a TODO note under `## [Unreleased]`
in the plugin changelog and regenerates the README, so `python3 scripts/check.py`
fails until the author writes the component and the user-facing note; the release
is then a minor bump (docs/releasing.md).

Hooks, MCP and LSP servers are not handled here: they merge into shared files and
need the security review (docs/security-review.md).
"""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys
import tempfile

import new_plugin
import repo

KINDS = ("skill", "agent")
TEMP_PREFIX = "add-component-"


class ComponentError(SystemExit):
    """The component cannot be added; the message says why."""


def target_path(plugin: Path, kind: str, name: str) -> Path:
    """Where the component lives inside the plugin."""
    if kind == "skill":
        return plugin / "skills" / name / "SKILL.md"
    return plugin / "agents" / f"{name}.md"


def generated_path(output: Path, kind: str) -> Path:
    """Where `claude plugin init` writes its example component."""
    if kind == "skill":
        return output / "skills" / "example" / "SKILL.md"
    return output / "agents" / "example.md"


def rename(text: str, name: str) -> str:
    """Give the generated example the component's name in frontmatter and heading."""
    text = re.sub(r"^name: example$", f"name: {name}", text, count=1, flags=re.MULTILINE)
    return re.sub(r"^# example$", f"# {name}", text, count=1, flags=re.MULTILINE)


def add_unreleased_note(text: str, note: str) -> str:
    """Add `- note` under `### Added` in `## [Unreleased]`, creating the subsection."""
    lines = text.rstrip("\n").splitlines()
    start = lines.index("## [Unreleased]")
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    added = next((i for i in range(start + 1, end) if lines[i] == "### Added"), None)
    if added is None:
        lines[start + 1 : start + 1] = ["", "### Added", "", f"- {note}"]
    else:
        last = added + 1
        while last + 1 < end and lines[last + 1].strip():
            last += 1
        lines.insert(last + 1, f"- {note}")
    return "\n".join(lines) + "\n"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    _ = parser.add_argument("plugin", help="existing plugin under plugins/")
    _ = parser.add_argument("kind", choices=KINDS)
    _ = parser.add_argument("name", help="kebab-case component name")
    _ = parser.add_argument("--description", required=True, help="what the component does")
    return parser.parse_args()


def main() -> int:
    """Scaffold the component, record the release note placeholder, sync and validate."""
    args = _parse_args()
    plugin_name: str = args.plugin  # pyright: ignore[reportAny]  # argparse Namespace attributes are Any
    kind: str = args.kind  # pyright: ignore[reportAny]  # argparse Namespace attributes are Any
    name: str = args.name  # pyright: ignore[reportAny]  # argparse Namespace attributes are Any
    description: str = args.description  # pyright: ignore[reportAny]  # argparse Namespace attributes are Any
    plugin = repo.PLUGINS_DIR / plugin_name
    if not (plugin / ".claude-plugin" / "plugin.json").is_file():
        msg = f"plugins/{plugin_name} is not a plugin; create one with new_plugin.py"
        raise ComponentError(msg)
    if not repo.KEBAB_RE.match(name):
        msg = f"component name {name!r} must be kebab-case"
        raise ComponentError(msg)
    target = target_path(plugin, kind, name)
    if target.exists():
        msg = f"{target.relative_to(repo.ROOT)} already exists"
        raise ComponentError(msg)
    with tempfile.TemporaryDirectory(prefix=TEMP_PREFIX) as tmp:
        output = new_plugin.run_init("scaffold", description, [f"{kind}s"], Path(tmp))
        target.parent.mkdir(parents=True, exist_ok=True)
        text = generated_path(output, kind).read_text(encoding="utf-8")
        _ = target.write_text(rename(text, name), encoding="utf-8")
    if Path(tmp).exists():
        msg = f"temporary scaffold directory {tmp} was not removed"
        raise ComponentError(msg)
    changelog = plugin / "CHANGELOG.md"
    note = f"TODO: describe the new `{name}` {kind} for users."
    _ = changelog.write_text(
        add_unreleased_note(changelog.read_text(encoding="utf-8"), note), encoding="utf-8"
    )
    repo.format_files([target, changelog])
    synced = repo.run([sys.executable, str(repo.ROOT / "scripts" / "sync_readmes.py")], check=False)
    repo.emit(synced.stdout.strip() or synced.stderr.strip())
    validation = repo.run(["claude", "plugin", "validate", str(plugin), "--strict"], check=False)
    repo.emit(validation.stdout.strip())
    steps = [
        f"Added {target.relative_to(repo.ROOT)}. Next steps:",
        "  1. Replace the TODOs in the component and the CHANGELOG note with real content.",
        f"  2. python3 scripts/bump_version.py plugin {plugin_name} minor",
        "  3. python3 scripts/check.py, then a pull request (the run-marketplace skill drives it).",
    ]
    repo.emit("\n" + "\n".join(steps))
    return 0


if __name__ == "__main__":
    sys.exit(main())
