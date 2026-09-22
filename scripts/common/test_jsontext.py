"""Tests for the canonical JSON serialisation shared by every generator."""

from __future__ import annotations

from scripts.common.jsontext import canonical_json


def test_indents_two_spaces_and_ends_with_a_newline() -> None:
    """The shape `.editorconfig` and every tracked artifact already use."""
    assert canonical_json({"a": [1]}) == '{\n  "a": [\n    1\n  ]\n}\n'


def test_keeps_the_author_s_key_order() -> None:
    """Sorting keys would reshuffle a hand-written file on its first regeneration."""
    assert canonical_json({"b": 1, "a": 2}) == '{\n  "b": 1,\n  "a": 2\n}\n'


def test_keeps_characters_above_ascii_verbatim() -> None:
    """A plugin description full of ASCII escape sequences is unreadable in a catalog."""
    assert canonical_json({"d": "a — b"}) == '{\n  "d": "a — b"\n}\n'
