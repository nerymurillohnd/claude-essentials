"""Rewrite the **Affected plugin** dropdown of every issue form, and nothing else.

An issue form is hand-written YAML with comments, blank lines and deliberate wording. Parsing
it and dumping it back would reformat all of that, so this generator edits text: it finds the
`options:` block that belongs to the `id: plugin` dropdown, replaces the option lines at the
indentation they already use, and leaves every other byte of the file untouched. A test
asserts exactly that, by rewriting a form with a changed option list and comparing everything
outside the block.

`make generate` runs this and then `git diff --exit-code`, so adding a plugin without
regenerating fails the gate rather than leaving a reporter unable to name it.
"""

from __future__ import annotations

import argparse
import re
import sys
from typing import TYPE_CHECKING, Final

from scripts.common.errors import ExitCode, MaintainerError
from scripts.common.plugins import repo_root
from scripts.github.issue_forms import (
    ISSUE_TEMPLATE_DIR,
    PLUGIN_DROPDOWN_ID,
    expected_options,
    form_paths,
)

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

DROPDOWN_ID_LINE: Final = re.compile(rf"^(?P<indent>\s*)id:\s*{PLUGIN_DROPDOWN_ID}\s*$")
"""The line that names the dropdown this generator owns."""

OPTIONS_LINE: Final = re.compile(r"^(?P<indent>\s*)options:\s*$")
"""The key whose block is replaced."""

OPTION_ITEM: Final = re.compile(r"^(?P<indent>\s*)-\s")
"""One option of a YAML block sequence."""

QUOTE_CHARACTERS: Final = ":#{}[],&*!|>%@`\"'"
"""Characters that make a plain YAML scalar ambiguous, so the option is quoted instead."""


def render_option(value: str) -> str:
    """Render one option as YAML, quoting it only when a plain scalar would be ambiguous.

    Args:
        value: The option text.

    Returns:
        The scalar to write after the dash.
    """
    if any(character in value for character in QUOTE_CHARACTERS) or value != value.strip():
        escaped = value.replace('"', '\\"')
        return f'"{escaped}"'
    return value


def rewrite(text: str, options: Sequence[str]) -> str:
    """Replace the option lines of the `id: plugin` dropdown, keeping everything else.

    Args:
        text: The whole form.
        options: The options to write, in order.

    Returns:
        The rewritten form; the input unchanged when it carries no such dropdown.
    """
    lines = text.splitlines(keepends=True)
    start = _dropdown_options_index(lines)
    if start is None:
        return text
    indent = _option_indent(lines, start)
    end = start + 1
    while end < len(lines) and _is_option_line(lines[end], indent):
        end += 1
    replacement = [f"{indent}- {render_option(option)}\n" for option in options]
    return "".join([*lines[: start + 1], *replacement, *lines[end:]])


def _dropdown_options_index(lines: Sequence[str]) -> int | None:
    """Find the `options:` line of the `id: plugin` dropdown.

    Args:
        lines: The form's lines.

    Returns:
        The index of that line, or None when the form has no such dropdown.
    """
    for index, line in enumerate(lines):
        if DROPDOWN_ID_LINE.match(line) is None:
            continue
        for candidate in range(index + 1, len(lines)):
            if OPTIONS_LINE.match(lines[candidate]) is not None:
                return candidate
            if DROPDOWN_ID_LINE.match(lines[candidate]) is not None:
                break
    return None


def _option_indent(lines: Sequence[str], options_index: int) -> str:
    """Return the indentation the existing option lines use.

    Args:
        lines: The form's lines.
        options_index: The index of the `options:` line.

    Returns:
        The leading whitespace of the first option, or two spaces deeper than `options:`.
    """
    following = lines[options_index + 1] if options_index + 1 < len(lines) else ""
    match = OPTION_ITEM.match(following)
    if match is not None:
        return match["indent"]
    key = OPTIONS_LINE.match(lines[options_index])
    base = "" if key is None else key["indent"]
    return f"{base}  "


def _is_option_line(line: str, indent: str) -> bool:
    """Report whether a line is one of the options being replaced.

    Args:
        line: The line to test.
        indent: The indentation the block uses.

    Returns:
        True for a dash item at exactly that indentation.
    """
    match = OPTION_ITEM.match(line)
    return match is not None and match["indent"] == indent


def write(root: Path) -> list[str]:
    """Rewrite every form whose dropdown is stale.

    Args:
        root: The repository root.

    Returns:
        The repository-relative paths that changed.

    Raises:
        MaintainerError: If a plugin directory cannot be listed.
    """
    options = expected_options(root)
    changed: list[str] = []
    for path in form_paths(root):
        text = path.read_text(encoding="utf-8")
        rewritten = rewrite(text, options)
        if rewritten != text:
            _ = path.write_text(rewritten, encoding="utf-8")
            changed.append(f"{ISSUE_TEMPLATE_DIR}/{path.name}")
    return changed


def main(argv: Sequence[str] | None = None) -> int:
    """Regenerate the dropdowns.

    Args:
        argv: Arguments without the program name; `sys.argv[1:]` when None.

    Returns:
        0 when the forms are written or already current, 2 when the inputs are unusable.
    """
    parser = argparse.ArgumentParser(
        prog="python -m scripts.github.generate_issue_forms",
        description="Regenerate the Affected plugin dropdown of every issue form.",
    )
    _ = parser.parse_args(argv)
    try:
        changed = write(repo_root())
    except (MaintainerError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return int(ExitCode.USAGE)
    if not changed:
        print(f"{ISSUE_TEMPLATE_DIR}: dropdowns unchanged")
    for rel in changed:
        print(f"{rel} rewritten")
    return int(ExitCode.OK)


if __name__ == "__main__":
    raise SystemExit(main())
