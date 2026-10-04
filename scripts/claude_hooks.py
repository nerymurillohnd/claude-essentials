#!/usr/bin/env python3
"""Claude Code hooks of this repository, registered in .claude/settings.json.

Run by Claude Code with the hook's JSON event on stdin:
  python3 scripts/claude_hooks.py guard-bash       PreToolUse Bash
  python3 scripts/claude_hooks.py guard-edit       PreToolUse Edit|Write
  python3 scripts/claude_hooks.py guard-sources    PreToolUse file, shell, web and GitHub tools
  python3 scripts/claude_hooks.py format           PostToolUse Edit|Write
  python3 scripts/claude_hooks.py session-status   SessionStart

The permission rules in .claude/settings.json are the hard boundary; these hooks
back them up where text rules cannot see (a push written as `git -C . push`),
and enforce repository rules no permission rule expresses: versions change only
through bump_version.py, generated README blocks only through sync_readmes.py,
and the forbidden sources listed in the untracked CLAUDE.local.md stay unread.
Decisions follow the hooks reference: JSON on stdout with a permissionDecision,
exit 0 (docs/adr/decisions/ADR_2026-10-04_claude-code-automation.md).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shlex
import shutil
import sys

import repo
from repo import JSON

# Global git options that take a separate value (git --help).
_GIT_OPTIONS_WITH_VALUE = frozenset(
    {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path", "--config-env"}
)
_SIGNING_BYPASS = (
    "--no-gpg-sign",
    "--no-verify",
    "commit.gpgsign=false",
    "tag.gpgsign=false",
    "core.hookspath",
)
# gh subcommands that publish or change something on GitHub.
_GH_PUBLISHING = {
    "pr": {"create", "merge", "edit", "close", "comment", "review", "reopen", "ready"},
    "release": {"create", "edit", "delete", "upload"},
    "repo": {"create", "edit", "delete", "rename", "archive", "fork"},
    "label": {"create", "edit", "delete", "clone"},
    "issue": {"create", "edit", "close", "comment", "delete", "reopen"},
    "workflow": {"run", "enable", "disable"},
    "secret": {"set", "delete"},
    "variable": {"set", "delete"},
}
_GH_API_WRITE_FLAGS = ("-f", "-F", "--field", "--raw-field", "--input")
_SEPARATORS = frozenset({";", "&&", "||", "|", "&", "(", ")", "\n"})
_GENERATED_RE = re.compile(
    r"<!-- BEGIN GENERATED: [\w-]+ -->.*?<!-- END GENERATED: [\w-]+ -->", re.DOTALL
)
_VERSION_RE = re.compile(r'"version"\s*:\s*"([^"]*)"')
_PRETTIER_SUFFIXES = frozenset({".md", ".json", ".yml", ".yaml"})
_BACKTICKED_RE = re.compile(r"`([^`]+)`")

# One-line reasons: Claude reads them as the explanation of a denied or asked call.
_SIGNING_REASON = "Commits and tags are always signed and hooks always run: fix the cause."
_PUSH_REASON = "A push leaves this machine: it needs the maintainer's approval for this push."
_GH_REASON = "`gh {group} {action}` changes GitHub: it needs the maintainer's approval."
_TAG_PUSH_REASON = "Pushing a release tag publishes it: it needs the maintainer's approval."
_VERSION_REASON = "Change versions only with `python3 scripts/bump_version.py` (docs/releasing.md)."
_GENERATED_REASON = "GENERATED blocks are written by `python3 scripts/sync_readmes.py`; run it."
_SOURCE_REASON = "{source} is a forbidden source (CLAUDE.local.md); the repo is clean-room."
_RULES_REMINDER = "Read repo files with Read, not cat: path-scoped rules load only on Read/Edit."
_FORMATTED_NOTE = "prettier reformatted {name}; re-read it before the next edit."
_NEWER_NOTE = "Claude Code {installed} is newer than the pin {pin}: run /cc-currency first."


# --------------------------------------------------------------------------
# Decisions


def decision(event: str, verdict: str, reason: str) -> dict[str, JSON]:
    """A PreToolUse permission decision in the hooks reference's JSON shape."""
    return {
        "hookSpecificOutput": {
            "hookEventName": event,
            "permissionDecision": verdict,
            "permissionDecisionReason": reason,
        }
    }


def _commands(command: str) -> list[list[str]]:
    """Split a shell command line into simple commands (best effort, no expansion)."""
    lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|()")
    lexer.whitespace_split = True
    lexer.commenters = ""
    try:
        tokens = list(lexer)
    except ValueError:
        tokens = command.split()
    commands: list[list[str]] = [[]]
    for token in tokens:
        if token in _SEPARATORS:
            commands.append([])
        else:
            commands[-1].append(token)
    return [words for words in commands if words]


def _program_index(words: list[str], name: str) -> int | None:
    """Where `name` runs in a simple command, skipping VAR=value, env and command."""
    for index, word in enumerate(words):
        if re.fullmatch(r"\w+=.*", word) or word in {"env", "command", "exec", "sudo"}:
            continue
        return index if Path(word).name == name else None
    return None


def _git_subcommand(words: list[str], start: int) -> tuple[str | None, list[str]]:
    """The git subcommand after global options, and the global options seen."""
    options: list[str] = []
    index = start + 1
    while index < len(words):
        word = words[index]
        if word in _GIT_OPTIONS_WITH_VALUE:
            options += words[index : index + 2]
            index += 2
        elif word.startswith("-"):
            options.append(word)
            index += 1
        else:
            return word, options
    return None, options


def bash_decision(command: str) -> dict[str, JSON] | None:
    """Deny signing or hook bypasses; ask before anything that publishes."""
    for words in _commands(command):
        lowered = [word.lower() for word in words]
        git = _program_index(words, "git")
        if git is not None:
            if any(flag in word for word in lowered for flag in _SIGNING_BYPASS):
                return decision("PreToolUse", "deny", _SIGNING_REASON)
            subcommand, _options = _git_subcommand(words, git)
            if subcommand == "push":
                return decision("PreToolUse", "ask", _PUSH_REASON)
        gh = _program_index(words, "gh")
        if gh is not None and len(words) > gh + 1:
            group = words[gh + 1]
            action = words[gh + 2] if len(words) > gh + 2 else ""
            writes_api = group == "api" and (
                any(flag in words for flag in _GH_API_WRITE_FLAGS)
                or re.search(r"(?:-X|--method)[ =]?(?:POST|PUT|PATCH|DELETE)", " ".join(words))
            )
            if action in _GH_PUBLISHING.get(group, set()) or writes_api:
                return decision("PreToolUse", "ask", _GH_REASON.format(group=group, action=action))
        claude = _program_index(words, "claude")
        if claude is not None and "tag" in words and "--push" in words:
            return decision("PreToolUse", "ask", _TAG_PUSH_REASON)
    return None


def _generated_spans(text: str) -> list[tuple[int, int]]:
    return [(match.start(), match.end()) for match in _GENERATED_RE.finditer(text)]


def edit_decision(tool: str, tool_input: dict[str, JSON], root: Path) -> dict[str, JSON] | None:
    """Versions and generated README blocks change only through their scripts."""
    path = Path(repo.as_str(tool_input.get("file_path")) or "")
    current = path.read_text(encoding="utf-8") if path.is_file() else ""
    old = repo.as_str(tool_input.get("old_string")) or ""
    new = repo.as_str(tool_input.get("new_string")) or ""
    content = repo.as_str(tool_input.get("content"))
    after = content if tool == "Write" and content is not None else current.replace(old, new, 1)
    try:
        relative = path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return None
    if re.fullmatch(r"plugins/[^/]+/\.claude-plugin/plugin\.json", relative):
        before_version = _VERSION_RE.search(current)
        after_version = _VERSION_RE.search(after)
        if (before_version and before_version.group(1)) != (
            after_version and after_version.group(1)
        ):
            return decision("PreToolUse", "deny", _VERSION_REASON)
    if [current[a:b] for a, b in _generated_spans(current)] != [
        after[a:b] for a, b in _generated_spans(after)
    ]:
        return decision("PreToolUse", "deny", _GENERATED_REASON)
    return None


def forbidden_sources(root: Path) -> tuple[list[Path], list[str]]:
    """Local paths and GitHub slugs listed in the untracked CLAUDE.local.md."""
    notes = root / "CLAUDE.local.md"
    if not notes.is_file():
        return [], []
    text = notes.read_text(encoding="utf-8")
    paths: list[Path] = []
    slugs: list[str] = []
    for line in text.splitlines():
        values = [str(match.group(1)) for match in _BACKTICKED_RE.finditer(line)]
        if line.startswith("- Local:"):
            paths += [Path(value).expanduser() for value in values]
        elif line.startswith("- GitHub:"):
            slugs += values
    return paths, slugs


def _mentions_path(text: str, forbidden: Path) -> bool:
    home = str(Path.home())
    target = str(forbidden)
    spellings = {target, target.replace(home, "~", 1), target.replace(home, "$HOME", 1)}
    return any(
        re.search(re.escape(spelling) + r"(?![\w.-])", text) is not None for spelling in spellings
    )


def sources_decision(tool_input: dict[str, JSON], root: Path) -> dict[str, JSON] | None:
    """Deny any tool call that would read a forbidden source (clean room)."""
    paths, slugs = forbidden_sources(root)
    text = json.dumps(tool_input)
    owner_repo = (
        f"{repo.as_str(tool_input.get('owner')) or ''}/{repo.as_str(tool_input.get('repo')) or ''}"
    )
    for forbidden in paths:
        if _mentions_path(text, forbidden):
            return decision("PreToolUse", "deny", _SOURCE_REASON.format(source=forbidden))
    for slug in slugs:
        pattern = r"(?<![\w.-])" + re.escape(slug) + r"(?![\w.-])"
        if re.search(pattern, text) or owner_repo == slug:
            return decision("PreToolUse", "deny", _SOURCE_REASON.format(source=slug))
    return None


# --------------------------------------------------------------------------
# Post-edit formatting and session context


def format_file(path: Path, root: Path) -> dict[str, JSON] | None:
    """Run prettier on an edited Markdown, JSON or YAML file inside the repository."""
    prettier = shutil.which("prettier")
    try:
        _ = path.resolve().relative_to(root.resolve())
    except ValueError:
        return None
    if prettier is None or path.suffix not in _PRETTIER_SUFFIXES or not path.is_file():
        return None
    before = path.read_text(encoding="utf-8")
    result = repo.run(
        [prettier, "--write", "--log-level", "warn", str(path)], cwd=root, check=False
    )
    if result.returncode != 0:
        return {
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": f"prettier failed on {path.name}: {result.stderr.strip()}",
            }
        }
    if path.read_text(encoding="utf-8") != before:
        return {
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": _FORMATTED_NOTE.format(name=path.name),
            }
        }
    return None


def _version(text: str) -> tuple[int, ...]:
    match = re.search(r"(\d+)\.(\d+)\.(\d+)", text)
    return tuple(int(part) for part in match.groups()) if match else ()


def session_status(root: Path) -> str:
    """A few lines of repository state for the start of a session."""
    lines: list[str] = []
    branch = repo.run(["git", "status", "--short", "--branch"], cwd=root, check=False).stdout
    first, *changes = branch.splitlines() or ["## unknown"]
    lines.append(f"claude-essentials: {first.removeprefix('## ')}, {len(changes)} changed file(s)")
    installed = repo.run(["claude", "--version"], cwd=root, check=False).stdout.strip()
    pin = _version(repo.MIN_CLAUDE_CODE)
    if _version(installed) > pin:
        version = installed.split()[0]
        lines.append(_NEWER_NOTE.format(installed=version, pin=repo.MIN_CLAUDE_CODE))
    lines.append(_RULES_REMINDER)
    return "\n".join(lines)


# --------------------------------------------------------------------------
# Entry point


def handle(name: str, event: dict[str, JSON], root: Path) -> dict[str, JSON] | str | None:
    """Dispatch one hook event to its handler."""
    tool = repo.as_str(event.get("tool_name")) or ""
    tool_input = repo.as_dict(event.get("tool_input")) or {}
    if name == "guard-bash":
        return bash_decision(repo.as_str(tool_input.get("command")) or "")
    if name == "guard-edit":
        return edit_decision(tool, tool_input, root)
    if name == "guard-sources":
        return sources_decision(tool_input, root)
    if name == "format":
        return format_file(Path(repo.as_str(tool_input.get("file_path")) or ""), root)
    if name == "session-status":
        return session_status(root)
    msg = f"unknown hook {name}"
    raise SystemExit(msg)


def main() -> int:
    """Read the event from stdin, print the hook's answer, always exit 0."""
    name = sys.argv[1] if len(sys.argv) > 1 else ""
    raw = sys.stdin.read()
    event = repo.as_dict(json.loads(raw)) if raw.strip() else {}  # pyright: ignore[reportAny]  # json.loads decodes only JSON types
    root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or repo.ROOT)
    answer = handle(name, event or {}, root)
    if isinstance(answer, str):
        _ = sys.stdout.write(answer + "\n")
    elif answer is not None:
        _ = sys.stdout.write(json.dumps(answer) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
