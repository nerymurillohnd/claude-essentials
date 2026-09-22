"""The official CLI wrapper: what it runs, and what it does when the binary is gone."""

from __future__ import annotations

import shutil
from typing import TYPE_CHECKING

import pytest

from scripts.common.errors import ExecutableNotFoundError
from scripts.common.plugins import plugin_ids, repo_root
from scripts.plugin_validation.claude_cli import (
    CLI_NAME,
    MARKETPLACE_TARGET,
    STRICT_FLAG,
    executable,
    targets,
    validate,
)

if TYPE_CHECKING:
    from pathlib import Path


def test_the_marketplace_is_validated_before_its_plugins() -> None:
    """A broken catalog explains every plugin failure, so it is reported first."""
    root = repo_root()
    checked = targets(root, plugin_ids(root))
    ids = plugin_ids(root)
    assert checked[0] == MARKETPLACE_TARGET
    assert checked[1 : 1 + len(ids)] == [f"plugins/{plugin_id}" for plugin_id in ids]


def test_the_template_shapes_are_validated_like_plugins() -> None:
    """The official action validates every folder with a manifest, templates included."""
    root = repo_root()
    shapes = [
        target for target in targets(root, plugin_ids(root)) if target.startswith("templates/")
    ]
    assert shapes == [
        "templates/plugin-agent-only",
        "templates/plugin-bundle",
        "templates/plugin-skill-only",
    ]


def test_a_missing_binary_is_one_line_not_a_traceback(monkeypatch: pytest.MonkeyPatch) -> None:
    """`make validate-cli` on a machine without Claude Code has to say so plainly.

    Args:
        monkeypatch: pytest's attribute patcher.
    """

    def absent(_name: str, _mode: int = 0, _path: str | None = None) -> str | None:
        """Stand in for `shutil.which` on a machine without the CLI.

        Args:
            _name: The binary being looked for.
            _mode: Ignored; part of the signature being replaced.
            _path: Ignored; part of the signature being replaced.

        Returns:
            None, always.
        """
        return None

    monkeypatch.setattr(shutil, "which", absent)
    with pytest.raises(ExecutableNotFoundError) as caught:
        _ = executable()
    assert CLI_NAME in str(caught.value)


def test_the_strict_flag_is_always_passed() -> None:
    """Without `--strict` an unrecognized manifest field is only a warning."""
    assert STRICT_FLAG == "--strict"


@pytest.mark.slow
def test_the_cli_accepts_this_marketplace() -> None:
    """The published catalog and every plugin pass the official validator today."""
    if shutil.which(CLI_NAME) is None:
        pytest.skip(f"{CLI_NAME} is not on PATH")
    root = repo_root()
    for target in targets(root, plugin_ids(root)):
        ok, output = validate(root, target)
        assert ok, f"{target}: {output}"


@pytest.mark.slow
def test_a_broken_manifest_is_refused(tmp_path: Path) -> None:
    """The CLI owns manifest shape, and the wrapper reports its verdict unchanged.

    Args:
        tmp_path: pytest's per-test directory.
    """
    if shutil.which(CLI_NAME) is None:
        pytest.skip(f"{CLI_NAME} is not on PATH")
    manifest = tmp_path / "plugin" / ".claude-plugin"
    manifest.mkdir(parents=True)
    _ = (manifest / "plugin.json").write_text('{"description": "no name"}\n', encoding="utf-8")
    ok, output = validate(tmp_path, "plugin")
    assert not ok
    assert output
