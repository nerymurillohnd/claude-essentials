"""Rewrite the per-file tables of `marketplace-governance/SKILL.md` in place.

Each governance area's table used to be typed by hand and went stale the moment a module was
added, renamed or removed (DEBT-0038: the GitHub area's table was missing six of its
nineteen files). This reads the one-line summary every `scripts/<area>/*.py` module already
carries as the first line of its module docstring, and rewrites the table between that area's
`<!-- governance-docs:<area> --> … <!-- /governance-docs:<area> -->` marker pair. Everything
else in the file — the prose, the placement rule, the tree — is authored by hand and untouched.

`make generate` runs this and then `git diff --exit-code`, so a module added without a
docstring, or a table edited by hand, fails the gate rather than reaching a reader as a stale
map.
"""

from __future__ import annotations

import argparse
import ast
import sys
from typing import TYPE_CHECKING, Final

from scripts.common.errors import ExitCode, MaintainerError, MissingPathError
from scripts.common.plugins import repo_root, working_files

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

SKILL_PATH: Final = ".claude/skills/marketplace-governance/SKILL.md"
"""The file whose generated tables this module owns."""

AREAS: Final[tuple[str, ...]] = (
    "github",
    "versioning",
    "marketplace",
    "plugin_validation",
    "lint",
    "harness",
    "common",
    "hygiene",
)
"""Every `scripts/<area>/` folder the placement rule defines, in `SKILL.md` order."""

_MARKER: Final = "governance-docs"


class MissingMarkerError(MaintainerError):
    """A governance area has no `governance-docs` marker pair in the skill file."""

    def __init__(self, area: str) -> None:
        """Record which area's marker pair is missing or out of order.

        Args:
            area: The `scripts/<area>` folder name.
        """
        block = f"{_start_marker(area)} … {_end_marker(area)}"
        super().__init__(f"{SKILL_PATH}: no {block} block for area {area!r}, or out of order")


class MissingDocstringError(MaintainerError):
    """A governed module has no module docstring to summarize."""

    def __init__(self, path: str) -> None:
        """Record which file has nothing to read.

        Args:
            path: The repository-relative path of the module.
        """
        super().__init__(f"{path}: has no module docstring")


class UnparsableModuleError(MaintainerError):
    """A governed module could not be parsed to read its docstring."""

    def __init__(self, path: str, detail: str) -> None:
        """Record which file failed to parse and why.

        Args:
            path: The repository-relative path of the module.
            detail: What the parser complained about.
        """
        super().__init__(f"{path}: cannot parse for its docstring: {detail}")


def _start_marker(area: str) -> str:
    """Build the opening marker of one area's generated block.

    Args:
        area: The `scripts/<area>` folder name.

    Returns:
        The literal marker text.
    """
    return f"<!-- {_MARKER}:{area} -->"


def _end_marker(area: str) -> str:
    """Build the closing marker of one area's generated block.

    Args:
        area: The `scripts/<area>` folder name.

    Returns:
        The literal marker text.
    """
    return f"<!-- /{_MARKER}:{area} -->"


def _first_docstring_line(source: str, path: str) -> str:
    """Read the one-line summary a module's docstring opens with.

    Args:
        source: The module's source text.
        path: Its repository-relative path, for the error message.

    Returns:
        The docstring's first line, trimmed.

    Raises:
        UnparsableModuleError: If the source is not valid Python.
        MissingDocstringError: If the module has no docstring.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError as error:
        raise UnparsableModuleError(path, str(error)) from error
    doc = ast.get_docstring(tree)
    if not doc:
        raise MissingDocstringError(path)
    return doc.strip().splitlines()[0]


def _sort_key(filename: str) -> tuple[str, bool]:
    """Order one area's files: a module immediately before its own test, then alphabetical.

    Args:
        filename: A file's bare name, for example `client.py` or `test_client.py`.

    Returns:
        A key that sorts `client.py` before `test_client.py`, and both before `labels.py`.
    """
    base = filename.removesuffix(".py")
    is_test = base.startswith("test_")
    return (base.removeprefix("test_") if is_test else base, is_test)


def module_rows(root: Path, area: str) -> list[tuple[str, str]]:
    """List every module of one governance area with its one-line summary.

    Args:
        root: The repository root.
        area: The `scripts/<area>` folder name.

    Returns:
        `(filename, summary)` pairs, `__init__.py` excluded, each module immediately followed
        by its own test file, otherwise alphabetical.

    Raises:
        UnparsableModuleError: If a module is not valid Python.
        MissingDocstringError: If a module has no docstring.
    """
    rels = working_files(root, f"scripts/{area}/*.py")
    names = sorted(
        (rel.rsplit("/", 1)[-1] for rel in rels if not rel.endswith("/__init__.py")),
        key=_sort_key,
    )
    rows: list[tuple[str, str]] = []
    for name in names:
        rel = f"scripts/{area}/{name}"
        source = (root / rel).read_text(encoding="utf-8")
        rows.append((name, _first_docstring_line(source, rel)))
    return rows


def render_table(rows: Sequence[tuple[str, str]]) -> str:
    """Render one area's rows as the Markdown table the skill embeds.

    Args:
        rows: `(filename, summary)` pairs, in the order to print them.

    Returns:
        The table text, no trailing newline.
    """
    lines = ["| File | Function |", "| --- | --- |"]
    lines.extend(f"| `{name}` | {summary} |" for name, summary in rows)
    return "\n".join(lines)


def render(root: Path) -> str:
    """Build `marketplace-governance/SKILL.md` with every generated table current.

    Args:
        root: The repository root.

    Returns:
        The whole file text.

    Raises:
        MissingPathError: If the skill file is missing.
        MissingMarkerError: If an area has no marker pair, or its markers are out of order.
        UnparsableModuleError: If a governed module is not valid Python.
        MissingDocstringError: If a governed module has no docstring.
    """
    path = root / SKILL_PATH
    if not path.is_file():
        raise MissingPathError(path, "the marketplace-governance skill")
    text = path.read_text(encoding="utf-8")
    for area in AREAS:
        start, end = _start_marker(area), _end_marker(area)
        start_index = text.find(start)
        end_index = text.find(end, start_index + len(start)) if start_index != -1 else -1
        if start_index == -1 or end_index == -1:
            raise MissingMarkerError(area)
        body_start = start_index + len(start)
        table = render_table(module_rows(root, area))
        text = f"{text[:body_start]}\n{table}\n{text[end_index:]}"
    return text


def write(root: Path) -> bool:
    """Write the skill file if the generated document differs from what is on disk.

    Args:
        root: The repository root.

    Returns:
        True when the file was rewritten.

    Raises:
        MissingPathError: If the skill file is missing.
        MissingMarkerError: If an area has no marker pair, or its markers are out of order.
        UnparsableModuleError: If a governed module is not valid Python.
        MissingDocstringError: If a governed module has no docstring.
    """
    path = root / SKILL_PATH
    rendered = render(root)
    if path.read_text(encoding="utf-8") == rendered:
        return False
    _ = path.write_text(rendered, encoding="utf-8")
    return True


def parse_args(argv: Sequence[str] | None) -> bool:
    """Parse the command line.

    Args:
        argv: Arguments without the program name; `sys.argv[1:]` when None.

    Returns:
        True when the caller asked for a dry run.

    Raises:
        SystemExit: If argparse refuses the arguments.
    """
    parser = argparse.ArgumentParser(
        prog="python -m scripts.harness.governance_docs",
        description="Regenerate the per-file tables of marketplace-governance/SKILL.md.",
    )
    _ = parser.add_argument(
        "--dry-run",
        action="store_true",
        help="report whether the skill file is stale without writing it",
    )
    values: dict[str, object] = vars(parser.parse_args(argv))
    return bool(values["dry_run"])


def main(argv: Sequence[str] | None = None) -> int:
    """Regenerate the skill file.

    Args:
        argv: Arguments without the program name; `sys.argv[1:]` when None.

    Returns:
        0 when the file is written or already current, 2 when the inputs are unusable.
    """
    dry_run = parse_args(argv)
    try:
        root = repo_root()
        if dry_run:
            stale = render(root) != (root / SKILL_PATH).read_text(encoding="utf-8")
            print(f"{SKILL_PATH} {'is stale' if stale else 'is current'}")
            return int(ExitCode.OK)
        changed = write(root)
    except (MaintainerError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return int(ExitCode.USAGE)
    print(f"{SKILL_PATH} {'rewritten' if changed else 'unchanged'}")
    return int(ExitCode.OK)


if __name__ == "__main__":
    raise SystemExit(main())
