"""What the harness actually loads: index entries, hook bindings, agents, rules, stale state.

The harness is the part of this repository Claude reads rather than runs: `CLAUDE.md` and its
nested files, `.claude/settings.json`, the skills' `hooks:` frontmatter, the subagents and the
rules. Nothing validates itself, so the defect this module exists to feed is the one P7 names:
an index that lists a file nobody ships, or a hook on disk that no index and no settings file
ever names, so it never fires and never says why.

This module only reads and reports. The tests beside it are what turn each reading into a
rule, and `--clean` is the one writer: it prunes the two state directories the hooks append
to, which otherwise grow for the lifetime of the checkout.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys
import time
from typing import TYPE_CHECKING, Final

from scripts.common.errors import ExitCode, MaintainerError, MissingPathError
from scripts.common.jsontext import is_json_array, is_json_object
from scripts.common.plugins import load_json, working_files
from scripts.plugin_validation import frontmatter

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping, Sequence

SETTINGS_PATH: Final = ".claude/settings.json"
"""Where the project's own hooks are wired."""

SKILLS_DIR: Final = ".claude/skills"
"""One directory per repository skill, each with a `SKILL.md`."""

AGENTS_DIR: Final = ".claude/agents"
"""One Markdown file per repository subagent."""

RULES_DIR: Final = ".claude/rules"
"""Working knowledge that loads with the files its `paths:` names."""

INDEX_COLUMNS: Final[tuple[str, str, str]] = ("name", "trigger", "purpose")
"""The three columns an index table carries; anything else is ordinary prose."""

STAMP_DIR: Final = ".claude/.cache/hooks"
"""Where `bash-stamp.sh` writes one file per session."""

STAMP_GLOB: Final = "bash-stamp-*"
"""The stamps `--clean` prunes."""

STAMP_MAX_AGE: Final = 7 * 24 * 60 * 60
"""A stamp older than a week belongs to a session that ended long ago."""

CHECKLIST_DIR: Final = ".claude/state/checklists"
"""Where the Stop-hook gate keeps a skill run's progress."""

CHECKLIST_GLOB: Final = "*.json"
"""The checklist records `--clean` prunes."""

CHECKLIST_MAX_AGE: Final = 30 * 24 * 60 * 60
"""A checklist untouched for a month is from a run nobody is going to finish."""


@dataclass(frozen=True, slots=True)
class IndexEntry:
    """One row of a `CLAUDE.md` index table.

    Attributes:
        source: The repository-relative `CLAUDE.md` the row came from.
        name: What the row points at, as written.
        trigger: When the thing loads or fires.
        purpose: What it is for.
    """

    source: str
    name: str
    trigger: str
    purpose: str


@dataclass(frozen=True, slots=True)
class HookBinding:
    """One hook command, and where it is wired.

    Attributes:
        source: The file that wires it.
        event: The hook event, for example `PreToolUse`.
        matcher: The matcher the event is scoped by, or None when there is none.
        command: The command line as written, `${CLAUDE_PROJECT_DIR}` and all.
    """

    source: str
    event: str
    matcher: str | None
    command: str


def index_files(root: Path) -> list[str]:
    """List the instruction files that may carry an index table.

    Args:
        root: The repository root.

    Returns:
        `CLAUDE.md` at the root and every nested one, sorted.
    """
    return sorted(rel for rel in working_files(root, "CLAUDE.md", "*/CLAUDE.md"))


def _row_cells(line: str) -> list[str] | None:
    """Split one Markdown table row into its cells.

    Args:
        line: A line of a Markdown file.

    Returns:
        The trimmed cells, or None when the line is not a table row.
    """
    stripped = line.strip()
    if not stripped.startswith("|") or not stripped.endswith("|"):
        return None
    return [cell.strip() for cell in stripped[1:-1].split("|")]


def _table_rows(lines: Sequence[str], start: int) -> Iterator[list[str]]:
    """Walk the body rows of the table whose header sits at `start`.

    Args:
        lines: Every line of the file.
        start: The index of the header row.

    Yields:
        The cells of each body row, skipping the `---` separator.
    """
    for index in range(start + 1, len(lines)):
        cells = _row_cells(lines[index])
        if cells is None:
            return
        if all(set(cell) <= {"-", ":"} for cell in cells):
            continue
        yield cells


def index_entries(root: Path) -> list[IndexEntry]:
    """Read every index table the instruction files carry.

    Args:
        root: The repository root.

    Returns:
        One entry per row, in file and then document order.
    """
    entries: list[IndexEntry] = []
    for rel in index_files(root):
        lines = (root / rel).read_text(encoding="utf-8").splitlines()
        for number, line in enumerate(lines):
            cells = _row_cells(line)
            if cells is None or tuple(cell.lower() for cell in cells[:3]) != INDEX_COLUMNS:
                continue
            entries.extend(
                IndexEntry(rel, row[0], row[1], row[2])
                for row in _table_rows(lines, number)
                if len(row) >= len(INDEX_COLUMNS)
            )
    return entries


def _commands(value: object) -> list[str]:
    """Pull the `command` of every handler in one `hooks:` list.

    Args:
        value: The list a matcher's `hooks` key holds.

    Returns:
        Every command string found, in order.
    """
    if not is_json_array(value):
        return []
    found: list[str] = []
    for handler in value:
        if is_json_object(handler):
            command = handler.get("command")
            if isinstance(command, str):
                found.append(command)
    return found


def _event_bindings(source: str, event: str, value: object) -> list[HookBinding]:
    """Read one event's list of matcher groups.

    Args:
        source: The file being read.
        event: The event name.
        value: The list the event key holds.

    Returns:
        One binding per handler.
    """
    if not is_json_array(value):
        return []
    bindings: list[HookBinding] = []
    for group in value:
        if not is_json_object(group):
            continue
        raw = group.get("matcher")
        matcher = raw if isinstance(raw, str) else None
        bindings.extend(
            HookBinding(source, event, matcher, command)
            for command in _commands(group.get("hooks"))
        )
    return bindings


def _bindings_from(source: str, hooks: Mapping[str, object]) -> list[HookBinding]:
    """Read a whole `hooks` mapping, whatever file it came from.

    Args:
        source: The file being read.
        hooks: The mapping, keyed by event.

    Returns:
        Every binding, sorted by event then command.
    """
    bindings: list[HookBinding] = []
    for event, value in hooks.items():
        bindings.extend(_event_bindings(source, event, value))
    return sorted(bindings, key=lambda binding: (binding.event, binding.command))


def settings_hooks(root: Path) -> list[HookBinding]:
    """Read the hooks `.claude/settings.json` wires.

    Args:
        root: The repository root.

    Returns:
        Every binding the settings file declares.

    Raises:
        MalformedJsonError: If the settings file is not valid JSON.
    """
    path = root / SETTINGS_PATH
    if not path.is_file():
        return []
    document = load_json(path)
    if not is_json_object(document):
        return []
    hooks = document.get("hooks")
    if not is_json_object(hooks):
        return []
    return _bindings_from(SETTINGS_PATH, hooks)


def skill_files(root: Path) -> list[str]:
    """List the repository skills' `SKILL.md` files.

    Args:
        root: The repository root.

    Returns:
        Sorted repository-relative paths.
    """
    return sorted(working_files(root, f"{SKILLS_DIR}/*/SKILL.md"))


def skill_hooks(root: Path) -> list[HookBinding]:
    """Read the hooks the repository skills wire through their frontmatter.

    Args:
        root: The repository root.

    Returns:
        Every binding a `SKILL.md` declares.
    """
    bindings: list[HookBinding] = []
    for rel in skill_files(root):
        hooks = frontmatter.read(root / rel).data.get("hooks")
        if is_json_object(hooks):
            bindings.extend(_bindings_from(rel, hooks))
    return bindings


def hook_bindings(root: Path) -> list[HookBinding]:
    """Read every hook this repository wires, wherever it is wired.

    Args:
        root: The repository root.

    Returns:
        The settings bindings followed by the skill bindings.
    """
    return [*settings_hooks(root), *skill_hooks(root)]


def agent_files(root: Path) -> list[str]:
    """List the repository subagents.

    Args:
        root: The repository root.

    Returns:
        Sorted repository-relative paths.
    """
    return sorted(working_files(root, f"{AGENTS_DIR}/*.md"))


def rule_paths(root: Path) -> dict[str, list[str]]:
    """Read which files each rule loads with.

    A rule with no `paths:` loads in every session; it maps to an empty list.

    Args:
        root: The repository root.

    Returns:
        One entry per rule file, keyed by repository-relative path.
    """
    rules: dict[str, list[str]] = {}
    for rel in sorted(working_files(root, f"{RULES_DIR}/*.md")):
        value = frontmatter.read(root / rel).data.get("paths")
        globs = [item for item in value if isinstance(item, str)] if is_json_array(value) else []
        rules[rel] = globs
    return rules


def _older_than(path: Path, seconds: float, now: float) -> bool:
    """Report whether a file has not been touched for a given span.

    Args:
        path: The file to measure.
        seconds: The span.
        now: The current time, passed in so a test can choose it.

    Returns:
        True when the file is older.
    """
    return now - path.stat().st_mtime > seconds


def stale_state(root: Path, now: float | None = None) -> list[str]:
    """List the state files `--clean` would prune.

    Args:
        root: The repository root.
        now: The current time; `time.time()` when None.

    Returns:
        Sorted repository-relative paths.
    """
    moment = time.time() if now is None else now
    found: list[str] = []
    for directory, pattern, age in (
        (STAMP_DIR, STAMP_GLOB, STAMP_MAX_AGE),
        (CHECKLIST_DIR, CHECKLIST_GLOB, CHECKLIST_MAX_AGE),
    ):
        base = root / directory
        if not base.is_dir():
            continue
        found.extend(
            f"{directory}/{path.name}"
            for path in base.glob(pattern)
            if path.is_file() and _older_than(path, age, moment)
        )
    return sorted(found)


def clean(root: Path, *, apply: bool = False, now: float | None = None) -> list[str]:
    """Prune the stale state the hooks leave behind.

    Args:
        root: The repository root.
        apply: When true, delete; otherwise only report.
        now: The current time; `time.time()` when None.

    Returns:
        Sorted repository-relative paths that were removed, or would be.
    """
    stale = stale_state(root, now)
    if apply:
        for rel in stale:
            (root / rel).unlink(missing_ok=True)
    return stale


def inventory_lines(root: Path) -> list[str]:
    """Render what the harness loads, for a maintainer reading the output alone.

    Args:
        root: The repository root.

    Returns:
        One line per fact, grouped by kind.
    """
    lines = [f"index entry  {entry.source}  {entry.name}" for entry in index_entries(root)]
    lines.extend(
        f"hook         {binding.source}  {binding.event}  {binding.command}"
        for binding in hook_bindings(root)
    )
    lines.extend(f"agent        {rel}" for rel in agent_files(root))
    lines.extend(
        f"rule         {rel}  {' '.join(globs) or '(always)'}"
        for rel, globs in rule_paths(root).items()
    )
    return lines


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    """Parse the command line.

    Args:
        argv: Arguments without the program name; `sys.argv[1:]` when None.

    Returns:
        The parsed arguments.

    Raises:
        SystemExit: If argparse refuses the arguments.
    """
    parser = argparse.ArgumentParser(
        prog="python -m scripts.harness.inventory",
        description="Report what the harness loads, and prune the state the hooks leave.",
    )
    _ = parser.add_argument("--root", default=None, help="read this tree instead of this one")
    _ = parser.add_argument("--clean", action="store_true", help="prune stale hook state")
    _ = parser.add_argument("--apply", action="store_true", help="with --clean: actually delete")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Report the inventory, or prune the stale state.

    Args:
        argv: Arguments without the program name; `sys.argv[1:]` when None.

    Returns:
        0 on success, 2 on unusable inputs.
    """
    options = parse_args(argv)
    values: dict[str, object] = vars(options)
    raw_root = values["root"]
    try:
        root = Path(raw_root) if isinstance(raw_root, str) else Path.cwd()
        if not (root / ".claude").is_dir():
            raise MissingPathError(root / ".claude", "the harness directory")
        if values["clean"]:
            apply = values["apply"] is True
            removed = clean(root, apply=apply)
            verb = "removed" if apply else "would remove"
            for rel in removed:
                print(f"{verb} {rel}")
            print(f"clean: {len(removed)} file(s)")
            return int(ExitCode.OK)
        for line in inventory_lines(root):
            print(line)
    except (MaintainerError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return int(ExitCode.USAGE)
    return int(ExitCode.OK)


if __name__ == "__main__":
    raise SystemExit(main())
