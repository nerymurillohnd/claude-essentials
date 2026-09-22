"""Tests for CI detection, including the local `GITHUB_ACTIONS=true` that motivated it."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from scripts.common.environment import ACTIONS_FLAG, RUN_MARKERS, in_github_actions

if TYPE_CHECKING:
    from _pytest.monkeypatch import MonkeyPatch


def _clear(monkeypatch: MonkeyPatch) -> None:
    """Start every case from an environment that claims nothing.

    Args:
        monkeypatch: pytest's environment patcher.
    """
    monkeypatch.delenv(ACTIONS_FLAG, raising=False)
    for name in RUN_MARKERS:
        monkeypatch.delenv(name, raising=False)


def test_a_bare_machine_is_not_a_runner(monkeypatch: MonkeyPatch) -> None:
    """The control: nothing set, nothing claimed."""
    _clear(monkeypatch)
    assert not in_github_actions()


def test_the_flag_alone_is_not_enough(monkeypatch: MonkeyPatch) -> None:
    """This maintainer's `~/.zshenv` exports it, so the flag alone would skip Q2 locally."""
    _clear(monkeypatch)
    monkeypatch.setenv(ACTIONS_FLAG, "true")
    assert not in_github_actions()


@pytest.mark.parametrize("marker", RUN_MARKERS)
def test_the_flag_with_a_run_identifier_is_a_runner(monkeypatch: MonkeyPatch, marker: str) -> None:
    """A real job always carries the run's own identifiers beside the flag."""
    _clear(monkeypatch)
    monkeypatch.setenv(ACTIONS_FLAG, "true")
    monkeypatch.setenv(marker, "12345")
    assert in_github_actions()


def test_a_run_identifier_without_the_flag_is_not_a_runner(monkeypatch: MonkeyPatch) -> None:
    """Both halves are required, so a stray variable cannot turn a laptop into CI."""
    _clear(monkeypatch)
    monkeypatch.setenv(RUN_MARKERS[0], "12345")
    assert not in_github_actions()
