r"""L3: the bytes of every text file, held to what `.editorconfig` already declares.

The defect this catches: a file written by a tool that turned a `\t` or a `\u0000` into a
literal control character, a CRLF that makes every later diff whole-file, or a missing final
newline that turns an append into a two-line change. All three are invisible in a rendered
diff and expensive once they land.

`.editorconfig` is the source of truth, not a second copy of it: the rules are read from that
file, so `[*.md] trim_trailing_whitespace = false` is honoured here exactly as the editor
honours it. Binary files are recognised by a null byte and skipped.
"""

from __future__ import annotations

import fnmatch
from typing import TYPE_CHECKING, Final

from scripts.common.errors import Finding

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

INVARIANT: Final = "L3"
"""The ID every message in this module starts with."""

EDITORCONFIG: Final = ".editorconfig"
"""The file whose rules this module enforces."""

SNIFF: Final = 8192
"""How many bytes decide whether a file is binary."""

CONTROL_CEILING: Final = 0x20
"""Every code point below this is a control character."""

ALLOWED_CONTROL: Final = frozenset({0x09, 0x0A})
"""Tab and newline: the only control characters a text file in this repository may hold."""


def _sections(root: Path) -> list[tuple[str, dict[str, str]]]:
    """Read `.editorconfig` into its glob sections, in file order.

    The format is a small INI dialect: `root = true` before any header, then one `[glob]`
    section per rule set. It is read here rather than with `configparser` because the
    preamble line belongs to no section and because the parser's own types would force a
    suppression this repository does not allow.

    Args:
        root: The repository root.

    Returns:
        One `(glob, settings)` pair per section; later sections win, as EditorConfig says.
    """
    path = root / EDITORCONFIG
    if not path.is_file():
        return []
    sections: list[tuple[str, dict[str, str]]] = []
    current: dict[str, str] | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", ";")):
            continue
        if stripped.startswith("[") and stripped.endswith("]"):
            current = {}
            sections.append((stripped[1:-1], current))
        elif "=" in stripped and current is not None:
            key, _, value = stripped.partition("=")
            current[key.strip().lower()] = value.strip().lower()
    return sections


def _matches(glob: str, rel: str) -> bool:
    """Apply one EditorConfig glob to a repository-relative path.

    A pattern without a `/` matches the file name alone; one with a `/` matches the whole
    path. That is the subset of EditorConfig's syntax this repository's file uses.

    Args:
        glob: The section name, without brackets.
        rel: The repository-relative path.

    Returns:
        True when the section applies.
    """
    if "/" in glob:
        return fnmatch.fnmatchcase(rel, glob)
    return fnmatch.fnmatchcase(rel.rsplit("/", 1)[-1], glob)


def settings_for(root: Path, rel: str) -> dict[str, str]:
    """Resolve the EditorConfig settings that apply to one file.

    Args:
        root: The repository root.
        rel: The repository-relative path.

    Returns:
        The merged settings, lower-cased keys and values.
    """
    resolved: dict[str, str] = {}
    for glob, settings in _sections(root):
        if _matches(glob, rel):
            resolved.update({key: value.strip().lower() for key, value in settings.items()})
    return resolved


def is_binary(data: bytes) -> bool:
    r"""Report whether a file should be treated as bytes rather than text.

    Git's heuristic is the null byte alone. This adds one condition, because the defect this
    module exists to catch is precisely a `\u0000` that some writer turned into a literal
    byte inside an otherwise ordinary text file: such a file still decodes as UTF-8, so
    requiring both a null byte and an undecodable stream keeps images and fonts out while
    leaving that defect visible as a control character.

    Args:
        data: The file's contents.

    Returns:
        True when the file holds a null byte near the start and is not UTF-8.
    """
    if b"\0" not in data[:SNIFF]:
        return False
    try:
        _ = data.decode("utf-8")
    except UnicodeDecodeError:
        return True
    return False


def _decode(rel: str, data: bytes) -> str | Finding:
    """Decode a file as UTF-8 or explain why it is not text.

    Args:
        rel: The repository-relative path.
        data: The file's contents.

    Returns:
        The decoded text, or the finding to report instead.
    """
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as error:
        return Finding(INVARIANT, rel, f"is not valid UTF-8: {error}")


def _control_findings(rel: str, text: str) -> list[Finding]:
    """Report every line that carries a control character other than tab.

    Args:
        rel: The repository-relative path.
        text: The decoded contents.

    Returns:
        One finding per offending line.
    """
    findings: list[Finding] = []
    for number, line in enumerate(text.split("\n"), start=1):
        bad = sorted(
            {ord(ch) for ch in line if ord(ch) < CONTROL_CEILING and ord(ch) not in ALLOWED_CONTROL}
        )
        if bad:
            names = ", ".join(f"U+{code:04X}" for code in bad)
            findings.append(Finding(INVARIANT, rel, f"line {number} holds {names}"))
    return findings


def check_text(root: Path, rel: str, text: str) -> list[Finding]:
    """Apply every byte rule to one already-decoded file.

    Args:
        root: The repository root, used to resolve `.editorconfig`.
        rel: The repository-relative path.
        text: The decoded contents.

    Returns:
        Every finding, in the order the rules are listed in this module's docstring.
    """
    settings = settings_for(root, rel)
    findings = _control_findings(rel, text)
    if "\r" in text:
        findings.append(Finding(INVARIANT, rel, "holds a carriage return; `.editorconfig` says LF"))
    if text and settings.get("insert_final_newline") == "true" and not text.endswith("\n"):
        findings.append(Finding(INVARIANT, rel, "has no final newline"))
    if settings.get("trim_trailing_whitespace") == "true":
        for number, line in enumerate(text.split("\n"), start=1):
            if line != line.rstrip():
                findings.append(Finding(INVARIANT, rel, f"line {number} has trailing whitespace"))
    return findings


def check(root: Path, paths: Sequence[str]) -> list[Finding]:
    """Check the bytes of every text file in a candidate list.

    Args:
        root: The repository root.
        paths: Repository-relative candidate paths; binary files are skipped.

    Returns:
        Every finding.
    """
    findings: list[Finding] = []
    for rel in paths:
        data = (root / rel).read_bytes()
        if is_binary(data):
            continue
        text = _decode(rel, data)
        if isinstance(text, Finding):
            findings.append(text)
            continue
        findings.extend(check_text(root, rel, text))
    return findings


def repaired(root: Path, rel: str, text: str) -> str:
    """Render one file with the defects a writer may safely repair.

    Control characters are never removed: deleting bytes a tool wrote would destroy content
    rather than format it, so `check` keeps reporting them until a human looks.

    Args:
        root: The repository root.
        rel: The repository-relative path.
        text: The decoded contents.

    Returns:
        The repaired text, which equals the input when nothing was wrong.
    """
    settings = settings_for(root, rel)
    fixed = text.replace("\r\n", "\n").replace("\r", "\n") if "\r" in text else text
    if settings.get("trim_trailing_whitespace") == "true":
        fixed = "\n".join(line.rstrip() for line in fixed.split("\n"))
    if fixed and settings.get("insert_final_newline") == "true" and not fixed.endswith("\n"):
        fixed += "\n"
    return fixed


def fix(root: Path, paths: Sequence[str], *, dry_run: bool = False) -> list[str]:
    """Repair the byte-level defects of every text file in a candidate list.

    Args:
        root: The repository root.
        paths: Repository-relative candidate paths; binary and undecodable files are skipped.
        dry_run: When true, report what would change and write nothing.

    Returns:
        The repository-relative paths that were rewritten, or would be.
    """
    changed: list[str] = []
    for rel in paths:
        path = root / rel
        data = path.read_bytes()
        if is_binary(data):
            continue
        text = _decode(rel, data)
        if isinstance(text, Finding):
            continue
        fixed = repaired(root, rel, text)
        if fixed != text:
            if not dry_run:
                _ = path.write_text(fixed, encoding="utf-8", newline="")
            changed.append(rel)
    return changed
