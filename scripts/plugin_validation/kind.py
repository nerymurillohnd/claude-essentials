"""Plugin shape and the four file-level invariants that go with it (P1 to P5).

The *kind* of a plugin is derived from its files and never declared in `plugin.json`, so
`claude plugin validate --strict` keeps accepting the manifest (ADR-0001 amendment). The
README's `**Kind:**` line is the only place it is written down, which is exactly why P1
compares the two.
"""

from __future__ import annotations

import enum
import re
from typing import TYPE_CHECKING, Final

from scripts.common.errors import Finding
from scripts.common.plugins import PLUGINS_DIRNAME, tracked_files

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

LICENSE_TEMPLATE: Final = "templates/LICENSE-Apache-2.0-reusable-template.md"
"""The master copy every plugin `LICENSE` is a byte-for-byte copy of (ADR-0005)."""

LICENSE_COMMENT_END: Final = "-->\n"
"""The end of the template's instruction comment; the license text follows it."""

APACHE_2_0_SHA256: Final = "cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30"
"""SHA-256 of https://www.apache.org/licenses/LICENSE-2.0.txt, recorded by the template."""

KIND_LINE: Final = re.compile(r"^\*\*Kind:\*\*\s+`(?P<kind>[a-z-]+)`")
"""The README line P1 reads, as the plugin README template writes it."""

PLACEHOLDER: Final = re.compile(r"(?<!\$)\{\{|REPLACE-WITH-[A-Z0-9-]+")
"""A template leftover: `{{…}}` not preceded by `$`, or a retired `REPLACE-WITH-*` token."""

SKILL_FILE: Final = "SKILL.md"
"""The file that makes a directory under `skills/` a skill."""

COMPONENT_TREES: Final[tuple[str, ...]] = (
    "commands",
    "hooks",
    "output-styles",
    "monitors",
    "workflows",
    "scripts",
    "assets",
)
"""Plugin-root trees that, when present, mean the plugin ships more than one component."""

COMPONENT_FILES: Final[tuple[str, ...]] = (".mcp.json", ".lsp.json", "settings.json")
"""Plugin-root files that are components in their own right."""


class Kind(enum.StrEnum):
    """The three shapes this marketplace distributes through the plugin mechanism."""

    BUNDLE = "bundle"
    SKILL_ONLY = "skill-only"
    AGENT_ONLY = "agent-only"


def plugin_dir(root: Path, plugin_id: str) -> Path:
    """Return the directory a plugin lives in.

    Args:
        root: The repository root.
        plugin_id: The plugin directory name.

    Returns:
        The absolute path of `plugins/<plugin_id>`.
    """
    return root / PLUGINS_DIRNAME / plugin_id


def skill_names(root: Path, plugin_id: str) -> list[str]:
    """List the skills a plugin ships.

    Args:
        root: The repository root.
        plugin_id: The plugin directory name.

    Returns:
        Sorted skill directory names; empty when the plugin ships none.
    """
    skills = plugin_dir(root, plugin_id) / "skills"
    if not skills.is_dir():
        return []
    return sorted(entry.name for entry in skills.iterdir() if (entry / SKILL_FILE).is_file())


def agent_names(root: Path, plugin_id: str) -> list[str]:
    """List the subagents a plugin ships.

    Args:
        root: The repository root.
        plugin_id: The plugin directory name.

    Returns:
        Sorted agent file stems; empty when the plugin ships none.
    """
    agents = plugin_dir(root, plugin_id) / "agents"
    if not agents.is_dir():
        return []
    return sorted(entry.stem for entry in agents.iterdir() if entry.suffix == ".md")


def _other_components(root: Path, plugin_id: str) -> list[str]:
    """List the component trees and files a plugin ships besides skills and agents.

    Args:
        root: The repository root.
        plugin_id: The plugin directory name.

    Returns:
        Sorted names of the trees and files that are present.
    """
    base = plugin_dir(root, plugin_id)
    present = [name for name in COMPONENT_TREES if (base / name).is_dir()]
    present.extend(name for name in COMPONENT_FILES if (base / name).is_file())
    return sorted(present)


def derive_kind(root: Path, plugin_id: str) -> Kind | None:
    """Derive a plugin's kind from the files it ships (ADR-0001).

    Args:
        root: The repository root.
        plugin_id: The plugin directory name.

    Returns:
        `SKILL_ONLY` for exactly one skill and nothing else, `AGENT_ONLY` for exactly one
        subagent and nothing else, `BUNDLE` for anything else that ships a component, and
        None when the directory ships no component at all.
    """
    skills = skill_names(root, plugin_id)
    agents = agent_names(root, plugin_id)
    others = _other_components(root, plugin_id)
    if not skills and not agents and not others:
        return None
    if len(skills) == 1 and not agents and not others:
        return Kind.SKILL_ONLY
    if len(agents) == 1 and not skills and not others:
        return Kind.AGENT_ONLY
    return Kind.BUNDLE


def readme_kind(readme: str) -> str | None:
    """Read the kind a README declares.

    Args:
        readme: The README's text.

    Returns:
        The declared kind, or None when the README carries no `**Kind:**` line.
    """
    for line in readme.splitlines():
        match = KIND_LINE.match(line)
        if match is not None:
            return match.group("kind")
    return None


def check_kind(root: Path, plugin_id: str, readme: str) -> list[Finding]:
    """Check that the README declares the kind the files imply (P1).

    Args:
        root: The repository root.
        plugin_id: The plugin directory name.
        readme: The README's text.

    Returns:
        One finding when no kind can be derived, none is declared, or they disagree.
    """
    rel = f"{PLUGINS_DIRNAME}/{plugin_id}/README.md"
    derived = derive_kind(root, plugin_id)
    declared = readme_kind(readme)
    if derived is None:
        return [
            Finding(
                "P1", f"{PLUGINS_DIRNAME}/{plugin_id}", "ships no skill, agent or other component"
            )
        ]
    if declared is None:
        return [Finding("P1", rel, f"no `**Kind:**` line; the files derive `{derived}`")]
    if declared != derived.value:
        return [Finding("P1", rel, f"declares `{declared}` but the files derive `{derived}`")]
    return []


def license_text(root: Path) -> str:
    """Return the Apache-2.0 text every `LICENSE` in this repository must equal.

    The template file prefixes the text with an instruction comment and one blank line;
    the rule inside that comment is to copy only what follows it.

    Args:
        root: The repository root.

    Returns:
        The license text, starting at the first line of the license itself.
    """
    template = (root / LICENSE_TEMPLATE).read_text(encoding="utf-8")
    body = template.split(LICENSE_COMMENT_END, 1)[1]
    return body.removeprefix("\n")


def check_license(root: Path, plugin_id: str) -> list[Finding]:
    """Check that a plugin's `LICENSE` is the template's text byte for byte (P2).

    Args:
        root: The repository root.
        plugin_id: The plugin directory name.

    Returns:
        One finding when the file is missing or differs.
    """
    rel = f"{PLUGINS_DIRNAME}/{plugin_id}/LICENSE"
    path = plugin_dir(root, plugin_id) / "LICENSE"
    if not path.is_file():
        return [Finding("P2", rel, "no `LICENSE` file")]
    if path.read_text(encoding="utf-8") != license_text(root):
        return [
            Finding(
                "P2",
                rel,
                f"differs from `{LICENSE_TEMPLATE}`; SPDX detection needs the verbatim text",
            )
        ]
    return []


def _text_lines(path: Path) -> Iterable[tuple[int, str]]:
    """Yield a file's numbered lines, skipping anything that is not UTF-8 text.

    Args:
        path: The file to read.

    Yields:
        One-based line numbers with their text.
    """
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError, OSError:
        return
    yield from enumerate(content.splitlines(), start=1)


def check_placeholders(root: Path, plugin_id: str) -> list[Finding]:
    """Check that no template placeholder survived into a shipped plugin file (P4).

    Args:
        root: The repository root.
        plugin_id: The plugin directory name.

    Returns:
        One finding per line that still carries a placeholder.
    """
    findings: list[Finding] = []
    for rel in tracked_files(root, f"{PLUGINS_DIRNAME}/{plugin_id}/*"):
        for number, line in _text_lines(root / rel):
            if PLACEHOLDER.search(line) is not None:
                findings.append(
                    Finding("P4", rel, f"line {number} still carries a template placeholder")
                )
    return findings


def check_no_bin(root: Path, plugin_id: str) -> list[Finding]:
    """Check that a plugin ships no top-level `bin/` directory (P5).

    Args:
        root: The repository root.
        plugin_id: The plugin directory name.

    Returns:
        One finding when the directory exists.
    """
    if (plugin_dir(root, plugin_id) / "bin").exists():
        return [
            Finding(
                "P5",
                f"{PLUGINS_DIRNAME}/{plugin_id}/bin",
                "a top-level `bin/` ships an undeclared runtime",
            )
        ]
    return []
