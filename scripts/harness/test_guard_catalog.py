"""Tests for the catalog guard: the generated array is refused, everything else is allowed.

`marketplace.json`'s `plugins` array is generated from the manifests on disk (M7). An edit to
it survives `make generate` only until the next run, and in the meantime the catalog and the
manifests disagree about what this marketplace ships. The guard refuses the edit before it
happens, and its message has to name the generator and the command, because that is all the
maintainer sees.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Final

import pytest

from scripts.common.errors import ExitCode
from scripts.common.jsontext import canonical_json
from scripts.harness.conftest import BASH_BINARIES, edit_payload, payload, reason, run_hook

if TYPE_CHECKING:
    from pathlib import Path

HOOK: Final = "guard-marketplace-catalog.sh"
"""The hook under test."""

CATALOG: Final = ".claude-plugin/marketplace.json"
"""The one file this guard is about."""

GENERATOR: Final = "scripts/marketplace/generate_marketplace.py"
"""What actually writes the array; the deny text must name it."""

COMMAND: Final = "make generate"
"""What the maintainer runs instead; the deny text must name it too."""

DOCUMENT: Final[dict[str, object]] = {
    "name": "test-market",
    "owner": {"name": "Test"},
    "plugins": [{"name": "alpha", "source": "./plugins/alpha"}],
}
"""A catalog with one generated entry and one hand-editable field."""


def _catalog(root: Path) -> Path:
    """Write the fixture catalog into a tree.

    Args:
        root: The tree to write into.

    Returns:
        The catalog's path.
    """
    path = root / CATALOG
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text(canonical_json(DOCUMENT), encoding="utf-8")
    return path


@pytest.mark.slow
@pytest.mark.parametrize("binary", BASH_BINARIES)
def test_an_edit_to_the_generated_array_is_denied(tmp_path: Path, hooks: Path, binary: str) -> None:
    """A hand-edited entry disagrees with the manifests until the next `make generate`."""
    path = _catalog(tmp_path)
    completed = run_hook(
        hooks / HOOK,
        edit_payload(path, tmp_path, old_string='"alpha"', new_string='"renamed"'),
        binary=binary,
        cwd=tmp_path,
    )
    text = reason(completed)
    assert GENERATOR in text
    assert COMMAND in text


@pytest.mark.slow
@pytest.mark.parametrize("binary", BASH_BINARIES)
def test_an_edit_to_another_field_is_allowed(tmp_path: Path, hooks: Path, binary: str) -> None:
    """Only the array is generated; the rest of the catalog is written by hand."""
    path = _catalog(tmp_path)
    completed = run_hook(
        hooks / HOOK,
        edit_payload(path, tmp_path, old_string='"test-market"', new_string='"renamed-market"'),
        binary=binary,
        cwd=tmp_path,
    )
    assert completed.stdout == ""
    assert completed.returncode == int(ExitCode.OK)


@pytest.mark.slow
@pytest.mark.parametrize("binary", BASH_BINARIES)
def test_a_write_that_changes_the_array_is_denied(tmp_path: Path, hooks: Path, binary: str) -> None:
    """A whole-file Write is the other way the array could be replaced."""
    path = _catalog(tmp_path)
    replacement = dict(DOCUMENT)
    replacement["plugins"] = []
    completed = run_hook(
        hooks / HOOK,
        payload(
            tool_name="Write",
            tool_input={"file_path": str(path), "content": json.dumps(replacement)},
            cwd=str(tmp_path),
        ),
        binary=binary,
        cwd=tmp_path,
    )
    assert GENERATOR in reason(completed)


@pytest.mark.slow
@pytest.mark.parametrize("binary", BASH_BINARIES)
def test_another_file_is_never_this_guard_s_business(
    tmp_path: Path, hooks: Path, binary: str
) -> None:
    """Every Edit and Write passes through here; only one path may be refused."""
    _ = _catalog(tmp_path)
    other = tmp_path / "README.md"
    _ = other.write_text("# readme\n", encoding="utf-8")
    completed = run_hook(
        hooks / HOOK,
        edit_payload(other, tmp_path, old_string="readme", new_string="catalog"),
        binary=binary,
        cwd=tmp_path,
    )
    assert completed.stdout == ""


def test_the_deny_text_names_no_retired_tooling(hooks: Path) -> None:
    """The text is what a maintainer acts on, so it must not send them to a deleted script."""
    text = (hooks / HOOK).read_text(encoding="utf-8")
    assert GENERATOR in text
    assert f"`{COMMAND}`" in text
    assert ".mjs" not in text
    assert "npm run" not in text
