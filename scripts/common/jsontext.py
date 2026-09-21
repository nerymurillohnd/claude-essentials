"""Canonical JSON: the one serialisation every generated artifact in this repository uses.

Two decisions are recorded here rather than repeated at each writer (P1):

* **Indent two, no key sorting.** A generated file keeps the author's key order, so a diff
  shows what changed rather than a reshuffle.
* **`ensure_ascii=False` and a trailing newline.** Plugin descriptions carry em dashes and
  typographic quotes; escaping them to an ASCII escape sequence would make every catalog
  entry unreadable and would differ byte for byte from what a human would write.

`scripts/lint/json_files.py` (step 6) formats the tracked JSON files with the same function,
so "what `make generate` writes" and "what `make lint` accepts" can never drift apart.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import json
from typing import Final, TypeIs

JSON_INDENT: Final = 2
"""Spaces per nesting level, matching `.editorconfig` for JSON."""


def canonical_json(obj: object) -> str:
    """Render a JSON document the way every generator in this repository writes it.

    Args:
        obj: The document to serialise; anything `json.dumps` accepts.

    Returns:
        The text, indented two spaces, unescaped above ASCII, with a trailing newline.
    """
    return json.dumps(obj, indent=JSON_INDENT, ensure_ascii=False) + "\n"


def is_json_object(value: object) -> TypeIs[Mapping[str, object]]:
    """Report whether a parsed JSON value is an object, without touching its contents.

    JSON objects always have string keys, so the claim holds for anything a JSON or YAML
    parser produced. `scripts.common.plugins.as_mapping` is the raising variant, used where a
    bad shape must be reported against a file rather than turned into a finding.

    Args:
        value: The parsed value.

    Returns:
        True when the value is a mapping.
    """
    return isinstance(value, Mapping)


def is_json_array(value: object) -> TypeIs[Sequence[object]]:
    """Report whether a parsed JSON value is an array.

    Strings and byte strings are sequences too, so they are excluded explicitly.

    Args:
        value: The parsed value.

    Returns:
        True when the value is a list or another non-string sequence.
    """
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes))
