"""The Stop-hook checklists are readable, complete, and their verifications can run.

A checklist is the definition of done for a skill, and the gate reads it from the committed
template rather than from the editable state. Three ways that goes wrong without anything
saying so: the template does not parse, so the gate cannot read an item; an item has no id,
so `checklist.sh check <id>` can never mark it; or a verification names a command the machine
does not have, so the item can never pass and the turn can never end.

The `make`-or-`git`-only rule for verifications arrives with the rewritten skills at step 10;
what this file pins today is that every verification's command exists.
"""

from __future__ import annotations

import re
import shutil
from typing import TYPE_CHECKING, Final

import pytest

from scripts.common.jsontext import is_json_array, is_json_object
from scripts.common.plugins import load_json, working_files

if TYPE_CHECKING:
    from pathlib import Path

CHECKLISTS: Final = ".claude/skills/*/checklist.json"
"""Every skill's committed template."""

REQUIRED_KEYS: Final[tuple[str, ...]] = ("id", "text")
"""What an item needs: an id to mark it by, and the text the gate shows Claude."""

ASSIGNMENT: Final = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=(?P<value>.*)$")
"""A shell variable assignment, which is how several verifications open."""

SUBSTITUTION: Final = re.compile(r"^\$\((?P<command>[^\s)]+)")
"""A command substitution, so `f=$(ls …)` is read as a call to `ls`."""

BUILTINS: Final[frozenset[str]] = frozenset(
    {"[", "cd", "echo", "exit", "for", "if", "printf", "test", "while"}
)
"""Shell builtins and keywords, which resolve without being on `PATH`."""


def _checklists(repo: Path) -> list[str]:
    """List the checklist templates this repository ships.

    Args:
        repo: The repository root.

    Returns:
        Sorted repository-relative paths.
    """
    return sorted(working_files(repo, CHECKLISTS))


def _items(repo: Path, rel: str) -> list[dict[str, object]]:
    """Read one template's items.

    Args:
        repo: The repository root.
        rel: The template's repository-relative path.

    Returns:
        One mapping per item.
    """
    document = load_json(repo / rel)
    assert is_json_object(document), rel
    items = document.get("items")
    assert is_json_array(items), rel
    return [
        {str(key): value for key, value in item.items()} for item in items if is_json_object(item)
    ]


def first_command(verify: str) -> str:
    """Read the command a verification actually starts by running.

    Several verifications open with an assignment whose value is a command substitution
    (`h=$(gh pr list …)`), so the first word alone would be the variable name.

    Args:
        verify: The verification command line.

    Returns:
        The executable name, or an empty string when the line starts with nothing runnable.
    """
    word = verify.strip().split(maxsplit=1)[0] if verify.strip() else ""
    assignment = ASSIGNMENT.match(word)
    if assignment is not None:
        substitution = SUBSTITUTION.match(assignment["value"])
        return substitution["command"] if substitution is not None else ""
    return word


def _verifications(repo: Path) -> list[tuple[str, str, str]]:
    """Collect every verification in every template.

    Args:
        repo: The repository root.

    Returns:
        One `(template, item id, command)` triple per verification.
    """
    found: list[tuple[str, str, str]] = []
    for rel in _checklists(repo):
        for item in _items(repo, rel):
            verify = item.get("verify")
            identifier = item.get("id")
            if isinstance(verify, str) and isinstance(identifier, str):
                found.append((rel, identifier, verify))
    return found


def test_this_repository_ships_checklists(repo: Path) -> None:
    """The rest of this file says nothing if the glob silently matches nothing."""
    assert _checklists(repo)


def test_every_template_parses_and_has_items(repo: Path) -> None:
    """A template the gate cannot read is a gate that lets every turn end."""
    for rel in _checklists(repo):
        assert _items(repo, rel), rel


def test_every_item_can_be_marked_and_shown(repo: Path) -> None:
    """Without an id nothing can check the item; without text Claude is told nothing."""
    for rel in _checklists(repo):
        for index, item in enumerate(_items(repo, rel)):
            for key in REQUIRED_KEYS:
                value = item.get(key)
                assert isinstance(value, str), f"{rel} item {index} has no {key}"
                assert value, f"{rel} item {index} has an empty {key}"


def test_item_ids_are_unique_within_a_template(repo: Path) -> None:
    """Two items with one id means marking either marks both, so one is never really done."""
    for rel in _checklists(repo):
        ids = [item["id"] for item in _items(repo, rel)]
        assert len(ids) == len(set(ids)), rel


def test_every_verification_names_a_command_that_exists(repo: Path) -> None:
    """A verification whose command is missing can never pass, so the turn can never end."""
    for rel, identifier, verify in _verifications(repo):
        command = first_command(verify)
        assert command, f"{rel}:{identifier} starts with nothing runnable"
        resolved = command in BUILTINS or shutil.which(command) is not None
        assert resolved, f"{rel}:{identifier} runs `{command}`, which is not on PATH"


@pytest.mark.parametrize(
    ("verify", "expected"),
    [
        ("npm run validate --silent", "npm"),
        ('h=$(gh pr list --json x); test -n "$h"', "gh"),
        ("for m in plugins/*/x.json; do :; done", "for"),
        ('[ -z "$(git status --porcelain)" ]', "["),
    ],
)
def test_the_command_reader_looks_through_an_assignment(verify: str, expected: str) -> None:
    """Reading the first word alone would call a variable name a missing command."""
    assert first_command(verify) == expected
