#!/usr/bin/env python3
"""Documentation drift gate: what the docs say about the repository matches the repository.

Run: scripts/check_docs.py [--root PATH]

Checks, each against the single source of truth in the code:
  * every copy of the minimum Claude Code version equals repo.MIN_CLAUDE_CODE
    (PIN_SITES lists where copies live);
  * the gate count and list in the rules and docs/testing.md equal check.GATES;
  * every `scripts/<name>.py` a document names exists, and every
    `scripts/check.py <target>` names a real gate or command;
  * every path-scoped rule in .claude/rules matches at least one file;
  * every relative Markdown link resolves;
  * every project skill's `name` equals its directory.

Exit 0 when the documentation is in sync, 1 otherwise. Each failure names the
file and what to change (docs/adr/decisions/ADR_2026-10-04_claude-code-automation.md).
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import re
import sys

import check
from check_repo import Report
import repo

# Directories that hold no documentation of the repository's current state; used only
# when the root is not a git checkout (the gate tests' fixtures), since git ls-files
# already leaves out ignored files such as worktrees and eval results.
_SKIPPED_DIRS = frozenset({".git", "node_modules", "__pycache__", ".ruff_cache", ".venv"})
_SKIPPED_PREFIXES = (".claude/worktrees/",)
_EVAL_RESULTS_RE = re.compile(r"^plugins/[^/]+/evals/results/")
# Text files whose mentions of docs/*.md must point at an existing document. Not
# ruff.toml: it is a copy of the maintainer's global config and cites Ruff's own docs.
_REFERENCE_SUFFIXES = frozenset({".md", ".py", ".yml", ".yaml", ".json"})
_DOC_REFERENCE_RE = re.compile(r"(?<![\w./-])(docs/[\w./-]+\.md)\b")
# Untracked private notes and templates full of placeholders are not checked for links.
_UNCHECKED_LINK_FILES = frozenset({"CLAUDE.local.md"})
_UNCHECKED_LINK_DIRS = frozenset({"templates"})
# Targets of check.py that are commands rather than gates.
_COMMANDS = frozenset({"test-install", "clean", "ci-tools", "--list"})
_NUMBER_WORDS = {
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
}


@dataclass(frozen=True)
class PinSite:
    """A place in the docs that repeats a version constant of repo.py, in capture-group order."""

    path: str
    pattern: str
    constants: tuple[str, ...]


PIN_SITES: tuple[PinSite, ...] = (
    PinSite(
        ".claude/rules/claude-code-version.md",
        r"verified on Claude Code (\d+\.\d+\.\d+) on",
        ("MIN_CLAUDE_CODE",),
    ),
    PinSite(
        ".claude/rules/claude-code-version.md",
        r"pinned at (\d+\.\d+\.\d+), in",
        ("MIN_CLAUDE_CODE",),
    ),
    PinSite(
        ".claude/rules/claude-code-version.md",
        r"every changelog entry newer than (\d+\.\d+\.\d+)\.",
        ("MIN_CLAUDE_CODE",),
    ),
    PinSite(
        "CLAUDE.md",
        r"verified on Claude Code (\d+\.\d+\.\d+) that",
        ("MIN_CLAUDE_CODE",),
    ),
    PinSite(
        "docs/releasing.md",
        r"Claude Code (\d+\.\d+\.\d+) or later",
        ("MIN_CLAUDE_CODE",),
    ),
    PinSite(
        ".github/ISSUE_TEMPLATE/bug_report.yml",
        r"label: Claude Code version\n(?:.*\n)*?\s+placeholder: (\d+\.\d+\.\d+)",
        ("MIN_CLAUDE_CODE",),
    ),
)

_SCRIPT_RE = re.compile(r"\bscripts/([\w/-]+\.py)\b")
# Only commands written as code count; prose such as "check.py and" is not a target.
_CHECK_TARGET_RE = re.compile(r"`scripts/check\.py ((?:--)?[a-z][\w-]*)[^`\n]*`")
_LINK_RE = re.compile(r"\]\(([^)\s]+)\)")
_FENCE_RE = re.compile(r"^(```|~~~).*?^\1", re.MULTILINE | re.DOTALL)
_CODE_SPAN_RE = re.compile(r"`[^`\n]*`")
_FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)


def _rel(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def _captures(pattern: re.Pattern[str], text: str) -> list[str]:
    """The first capture group of every match, typed (findall returns Any)."""
    return [str(match.group(1)) for match in pattern.finditer(text)]


_TARGET_ROW_RE = re.compile(r"^\| `scripts/check\.py ([\w-]+)`", re.MULTILINE)
_RULE_GLOB_RE = re.compile(r'^\s+- "([^"]+)"$', re.MULTILINE)


def repository_files(root: Path) -> list[Path]:
    """Files git would commit (tracked or new, never ignored), so local runs match CI."""
    if (root / ".git").exists():
        listed = repo.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
            cwd=root,
            check=False,
        )
        if listed.returncode == 0:
            names = [name for name in listed.stdout.split("\0") if name]
            return sorted(root / name for name in names if (root / name).is_file())
    return [
        path
        for path in sorted(root.rglob("*"))
        if path.is_file()
        and not _SKIPPED_DIRS.intersection(path.relative_to(root).parts[:-1])
        and not _rel(root, path).startswith(_SKIPPED_PREFIXES)
        and not _EVAL_RESULTS_RE.match(_rel(root, path))
        and path.name not in {".DS_Store", "CLAUDE.local.md"}
    ]


def check_doc_references(root: Path, files: list[Path], report: Report) -> None:
    """Every docs/*.md a document, script or config names exists."""
    for path in files:
        if path.suffix not in _REFERENCE_SUFFIXES and path.name != ".gitignore":
            continue
        for reference in sorted(
            set(_captures(_DOC_REFERENCE_RE, path.read_text(encoding="utf-8")))
        ):
            if "YYYY" not in reference and not (root / reference).is_file():
                report.fail(_rel(root, path), f"names {reference}, which does not exist")


def check_pins(root: Path, report: Report) -> None:
    """Every copy of a version constant equals its value in scripts/repo.py."""
    for site in PIN_SITES:
        path = root / site.path
        if not path.is_file():
            report.fail(site.path, "missing file listed in PIN_SITES (scripts/check_docs.py)")
            continue
        matches = list(re.finditer(site.pattern, path.read_text(encoding="utf-8")))
        if not matches:
            report.fail(
                site.path,
                f"pin text /{site.pattern}/ not found; update the text or PIN_SITES",
            )
        for match in matches:
            for group, constant in enumerate(site.constants, start=1):
                expected = str(getattr(repo, constant))  # pyright: ignore[reportAny]  # module constants are read by name
                found = match.group(group)
                if found != expected:
                    report.fail(site.path, f"{found} must be {expected} ({constant} in repo.py)")


def _count(text: str) -> int | None:
    word = text.lower()
    return int(word) if word.isdigit() else _NUMBER_WORDS.get(word)


def check_gate_list(root: Path, report: Report) -> None:
    """The gate count and names in the docs equal check.GATES."""
    gates = list(check.GATES)
    rule = root / ".claude" / "rules" / "testing" / "gates.md"
    where = _rel(root, rule)
    text = rule.read_text(encoding="utf-8") if rule.is_file() else ""
    count = re.search(r"`scripts/check\.py`: (\w+) gates", text)
    if count is None or _count(count.group(1)) != len(gates):
        found = count.group(1) if count else "no count"
        report.fail(where, f"gate count is {found}, check.py has {len(gates)}")
    listed = re.search(r"The gates are (.+?)\.\n", text)
    names = re.split(r", | and ", listed.group(1)) if listed else []
    if names != gates:
        report.fail(where, f"gate list {names} must be {gates} (check.py order)")
    testing = root / "docs" / "testing.md"
    targets = _captures(_TARGET_ROW_RE, testing.read_text(encoding="utf-8"))
    for gate in gates:
        if gate not in targets:
            report.fail("docs/testing.md", f'Targets table has no row for gate "{gate}"')
    for target in targets:
        if target not in gates and target not in _COMMANDS:
            report.fail("docs/testing.md", f'Targets table lists unknown target "{target}"')


def check_script_references(root: Path, files: list[Path], report: Report) -> None:
    """Scripts and check.py targets named in the docs exist."""
    valid_targets = set(check.GATES) | _COMMANDS
    for path in files:
        if path.suffix != ".md" or path.name in _UNCHECKED_LINK_FILES:
            continue
        text = path.read_text(encoding="utf-8")
        for name in sorted(set(_captures(_SCRIPT_RE, text))):
            if not (root / "scripts" / name).is_file():
                report.fail(_rel(root, path), f"names scripts/{name}, which does not exist")
        for target in sorted(set(_captures(_CHECK_TARGET_RE, text))):
            if target not in valid_targets:
                report.fail(_rel(root, path), f'"scripts/check.py {target}" is no target')


def glob_regex(pattern: str) -> re.Pattern[str]:
    """Translate a rule `paths` glob (`**`, `*`, `?`, `{a,b}`) into an anchored regex."""
    out: list[str] = []
    i = 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif pattern.startswith("**", i):
            out.append(".*")
            i += 2
        elif pattern[i] == "*":
            out.append("[^/]*")
            i += 1
        elif pattern[i] == "?":
            out.append("[^/]")
            i += 1
        elif pattern[i] == "{" and "}" in pattern[i:]:
            end = pattern.index("}", i)
            options = pattern[i + 1 : end].split(",")
            out.append("(?:" + "|".join(re.escape(option) for option in options) + ")")
            i = end + 1
        else:
            out.append(re.escape(pattern[i]))
            i += 1
    return re.compile("".join(out) + r"\Z")


def rule_globs(text: str) -> list[str]:
    """The `paths` globs of a rule's frontmatter, or [] for an always-loaded rule."""
    frontmatter = _FRONTMATTER_RE.match(text)
    if frontmatter is None:
        return []
    return _captures(_RULE_GLOB_RE, str(frontmatter.group(1)))


def check_rule_paths(root: Path, files: list[Path], report: Report) -> None:
    """Every path-scoped rule loads for at least one existing file."""
    relative = [_rel(root, path) for path in files]
    for rule in sorted((root / ".claude" / "rules").rglob("*.md")):
        globs = rule_globs(rule.read_text(encoding="utf-8"))
        if globs and not any(glob_regex(g).match(path) for g in globs for path in relative):
            report.fail(
                _rel(root, rule), f"no file matches its paths {globs}; the rule never loads"
            )


def check_links(root: Path, files: list[Path], report: Report) -> None:
    """Relative Markdown links outside code resolve to an existing file or directory."""
    for path in files:
        parts = set(path.relative_to(root).parts)
        if (
            path.suffix != ".md"
            or path.name in _UNCHECKED_LINK_FILES
            or parts & _UNCHECKED_LINK_DIRS
        ):
            continue
        text = _CODE_SPAN_RE.sub("", _FENCE_RE.sub("", path.read_text(encoding="utf-8")))
        for target in _captures(_LINK_RE, text):
            if re.match(r"[a-z][a-z0-9+.-]*:", target) or target.startswith("#"):
                continue
            if not (path.parent / target.split("#", 1)[0]).exists():
                report.fail(_rel(root, path), f"broken link {target}")


def check_skill_names(root: Path, report: Report) -> None:
    """A project skill's frontmatter name equals its directory, so /name is predictable."""
    for skill in sorted((root / ".claude" / "skills").glob("*/SKILL.md")):
        frontmatter = _FRONTMATTER_RE.match(skill.read_text(encoding="utf-8"))
        name = (
            re.search(r"^name:\s*(\S+)", frontmatter.group(1), re.MULTILINE)
            if frontmatter
            else None
        )
        if name is None or name.group(1) != skill.parent.name:
            found = name.group(1) if name else "missing"
            report.fail(_rel(root, skill), f"name {found} must equal {skill.parent.name}")


def run_checks(root: Path) -> Report:
    """Run every documentation check on the repository at `root`."""
    report = Report()
    files = repository_files(root)
    check_pins(root, report)
    check_gate_list(root, report)
    check_script_references(root, files, report)
    check_rule_paths(root, files, report)
    check_links(root, files, report)
    check_doc_references(root, files, report)
    check_skill_names(root, report)
    return report


def main() -> int:
    """Run the checks and report every drift."""
    parser = argparse.ArgumentParser(description=__doc__)
    _ = parser.add_argument("--root", type=Path, default=repo.ROOT, help="repository root to check")
    args = parser.parse_args()
    root: Path = args.root  # pyright: ignore[reportAny]  # argparse Namespace attributes are Any
    report = run_checks(root)
    for error in report.errors:
        repo.emit(f"✘ {error}")
    if report.errors:
        repo.emit(f"check_docs: {len(report.errors)} drift(s)")
        return 1
    repo.emit("check_docs: documentation matches the repository")
    return 0


if __name__ == "__main__":
    sys.exit(main())
