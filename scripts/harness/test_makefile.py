"""The pipeline is the `Makefile`, so the `Makefile` itself is checked.

Every consumer — the hooks, the checklists, CI, the editor tasks, the auditor — calls
`make <target>`. That only holds while the targets exist, run in the stated order, and fail
closed when the project environment is missing. Three drifts this catches: a target that
disappears and takes a hook's command with it; a `check` whose steps reorder so a slow
validator runs before a cheap one that would have failed first; and a recipe that reaches for
`uv` outside `setup`, which would sync the environment inside a gate (P4).
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Final

import pytest

if TYPE_CHECKING:
    from pathlib import Path

MAKEFILE: Final = "Makefile"
"""The one pipeline definition."""

TARGETS: Final[tuple[str, ...]] = (
    "setup",
    "check",
    "generate",
    "lint",
    "lint-staged",
    "types",
    "test-fast",
    "validate",
    "validate-cli",
    "test-slow",
    "versions",
    "fix",
    "fix-file",
    "clean",
    "help",
)
"""Every target §A7 defines, in the order the file declares them."""

CHECK_ORDER: Final[tuple[str, ...]] = (
    "generate",
    "lint",
    "types",
    "test-fast",
    "validate",
    "validate-cli",
    "test-slow",
)
"""`check`'s steps: generate first, bytes before parsing, types before tests, slow last."""

VENV_PREREQUISITE: Final = ".venv/bin/python"
"""The interpreter `PY` names; every target but `setup` waits for it to exist."""

VENV_TARGET: Final = "$(PY)"
"""How that file target is spelled, and the prerequisite every recipe carries."""

RULE: Final = re.compile(r"^(?P<target>[a-z][a-z-]*):(?P<rest>.*)$", re.MULTILINE)
"""One target's declaration line, with its prerequisites and any `##` comment."""


@pytest.fixture
def makefile(repo: Path) -> str:
    """Read the pipeline definition.

    Args:
        repo: The repository root.

    Returns:
        The file's text.
    """
    return (repo / MAKEFILE).read_text(encoding="utf-8")


def _rules(text: str) -> dict[str, str]:
    """Index the declaration lines by target.

    Args:
        text: The `Makefile`.

    Returns:
        The rest of each target's line, keyed by target.
    """
    return {match["target"]: match["rest"] for match in RULE.finditer(text)}


def _recipe(text: str, target: str) -> list[str]:
    """Read one target's recipe lines.

    Args:
        text: The `Makefile`.
        target: The target to read.

    Returns:
        The tab-indented lines under the declaration.
    """
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if line.startswith(f"{target}:"):
            recipe: list[str] = []
            for candidate in lines[index + 1 :]:
                if not candidate.startswith("\t"):
                    break
                recipe.append(candidate.strip())
            return recipe
    return []


@pytest.mark.parametrize("target", TARGETS)
def test_every_target_exists(makefile: str, target: str) -> None:
    """A missing target is a hook, a task or a checklist that stops working silently."""
    assert target in _rules(makefile)


@pytest.mark.parametrize("target", TARGETS)
def test_every_target_documents_itself(makefile: str, target: str) -> None:
    """`make help` is built from these comments, so an undocumented target is invisible."""
    assert "##" in _rules(makefile)[target], target


def test_help_lists_every_target(makefile: str) -> None:
    """The list a maintainer reads has to be the list the file defines."""
    documented = [target for target in _rules(makefile) if "##" in _rules(makefile)[target]]
    assert sorted(documented) == sorted(TARGETS)


def test_check_runs_its_steps_in_the_stated_order(makefile: str) -> None:
    """The order is the design: cheap and byte-level first, the slow suites last."""
    prerequisites = [
        word for word in _rules(makefile)["check"].split("##")[0].split() if word in CHECK_ORDER
    ]
    assert tuple(prerequisites) == CHECK_ORDER


def test_every_target_but_setup_waits_for_the_project_environment(makefile: str) -> None:
    """Without it the recipes fail with a message about a missing file, not a missing `.venv`."""
    rules = _rules(makefile)
    for target in TARGETS:
        if target in {"setup", "check", "help"}:
            continue
        assert VENV_TARGET in rules[target], target


def test_the_missing_environment_recipe_names_make_setup(makefile: str) -> None:
    """Fail closed with the one command that fixes it, the same rule the hooks follow."""
    assert f"PY := {VENV_PREREQUISITE}" in makefile
    recipe = " ".join(_recipe(makefile, VENV_TARGET))
    assert "make setup" in recipe
    assert "exit 2" in recipe


def test_only_setup_ever_calls_uv(makefile: str) -> None:
    """Syncing the environment inside a gate would change what the gate is testing (P4)."""
    for target in TARGETS:
        if target == "setup":
            continue
        assert "uv" not in " ".join(_recipe(makefile, target)).lower(), target


def test_no_recipe_uses_uv_run(makefile: str) -> None:
    """Recipes call `.venv/bin/*` so the hooks work under a `PATH` without `~/.local/bin`."""
    assert "uv run" not in makefile


def test_the_python_file_list_comes_from_git(makefile: str) -> None:
    """Ruff is never handed a directory: it would reformat the eval fixtures' fenced code."""
    assert "PY_FILES := $(shell git ls-files" in makefile


def test_types_runs_with_the_project_environment_first_on_path(makefile: str) -> None:
    """Basedpyright resolves imports from the first interpreter it finds."""
    recipe = " ".join(_recipe(makefile, "types"))
    assert 'PATH="$(CURDIR)/.venv/bin:$$PATH"' in recipe
    assert ".venv/bin/basedpyright" in recipe


def test_the_lint_targets_call_the_lint_entrypoint(makefile: str) -> None:
    """One entrypoint answers for the whole file set, so the hook and CI cannot diverge."""
    assert "scripts.lint.lint_files" in " ".join(_recipe(makefile, "lint"))
    assert "--staged" in " ".join(_recipe(makefile, "lint-staged"))
    assert "--fix" in " ".join(_recipe(makefile, "fix"))
    assert '--file "$(FILE)"' in " ".join(_recipe(makefile, "fix-file"))
