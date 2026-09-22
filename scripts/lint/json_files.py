"""L2: every tracked or new `.json` file is in the repository's one canonical form.

The defect this catches: two writers of the same file disagreeing about whitespace, so a
generated artifact and a hand-edited one produce a diff that is pure noise and hides the one
line that actually changed. `scripts.common.jsontext.canonical_json` is that single form, and
`make generate` writes it, so "what a generator writes" and "what the gate accepts" cannot
drift (P1).

Two kinds of file are never parsed here. JSON with comments (`*.jsonc`, and `tsconfig*.json`,
which VS Code and TypeScript both treat as JSONC) is not JSON, so a strict parser would only
report it as broken. And the paths in `JSON_EXCLUDED` are files this repository does not own
the formatting of.
"""

from __future__ import annotations

import fnmatch
from typing import TYPE_CHECKING, Final

from scripts.common.errors import Finding, MalformedJsonError
from scripts.common.jsontext import canonical_json
from scripts.common.plugins import parse_json

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

INVARIANT: Final = "L2"
"""The ID every message in this module starts with."""

JSON_SUFFIX: Final = ".json"
"""What makes a path a candidate at all."""

JSONC_PATTERNS: Final[tuple[str, ...]] = ("*.jsonc", "tsconfig*.json", "*/tsconfig*.json")
"""JSON with comments: never parsed, because a strict parser would call every one broken."""

JSON_EXCLUDED: Final[tuple[str, ...]] = (
    # Vendored verbatim from SchemaStore and byte-pinned by X2: reformatting would break the
    # hash and lose the "unmodified except one `$comment`" claim.
    ".github/schemas/*",
)
"""The one exclusion list. Everything else that parses as JSON is held to the canonical form."""


def is_jsonc(rel: str) -> bool:
    """Report whether a path is JSON with comments rather than JSON.

    Args:
        rel: The repository-relative path.

    Returns:
        True when the file may carry comments and must not be parsed.
    """
    return any(fnmatch.fnmatchcase(rel, pattern) for pattern in JSONC_PATTERNS)


def is_excluded(rel: str) -> bool:
    """Report whether this repository owns the formatting of a path.

    Args:
        rel: The repository-relative path.

    Returns:
        True when the file is vendored or belongs to the Node toolchain being removed.
    """
    return any(fnmatch.fnmatchcase(rel, pattern) for pattern in JSON_EXCLUDED)


def select(paths: Sequence[str]) -> list[str]:
    """Keep the JSON files this gate formats out of a candidate list.

    Args:
        paths: Repository-relative candidate paths.

    Returns:
        The paths that end in `.json`, are not JSONC and are not excluded.
    """
    return [
        rel
        for rel in paths
        if rel.endswith(JSON_SUFFIX) and not is_jsonc(rel) and not is_excluded(rel)
    ]


def canonical_form(root: Path, rel: str) -> str | Finding:
    """Render one file the way this repository writes JSON.

    Args:
        root: The repository root.
        rel: The repository-relative path.

    Returns:
        The canonical text, or a finding when the file does not parse as JSON.
    """
    text = (root / rel).read_text(encoding="utf-8")
    try:
        parsed = parse_json(text, path=root / rel)
    except MalformedJsonError as error:
        return Finding(INVARIANT, rel, f"is not valid JSON: {error}")
    return canonical_json(parsed)


def check(root: Path, paths: Sequence[str]) -> list[Finding]:
    """Report every JSON file that is not in canonical form.

    Args:
        root: The repository root.
        paths: Repository-relative candidate paths; anything else is ignored.

    Returns:
        One finding per file that would change, or that cannot be parsed.
    """
    findings: list[Finding] = []
    for rel in select(paths):
        rendered = canonical_form(root, rel)
        if isinstance(rendered, Finding):
            findings.append(rendered)
        elif rendered != (root / rel).read_text(encoding="utf-8"):
            findings.append(
                Finding(INVARIANT, rel, "is not in canonical JSON form; run `make fix`")
            )
    return findings


def fix(root: Path, paths: Sequence[str], *, dry_run: bool = False) -> list[str]:
    """Rewrite every JSON file that is not in canonical form.

    A file that does not parse is left alone: guessing at broken JSON would destroy it.

    Args:
        root: The repository root.
        paths: Repository-relative candidate paths; anything else is ignored.
        dry_run: When true, report what would change and write nothing.

    Returns:
        The repository-relative paths that were rewritten, or would be.
    """
    changed: list[str] = []
    for rel in select(paths):
        rendered = canonical_form(root, rel)
        if isinstance(rendered, Finding):
            continue
        path = root / rel
        if rendered != path.read_text(encoding="utf-8"):
            if not dry_run:
                _ = path.write_text(rendered, encoding="utf-8")
            changed.append(rel)
    return changed
