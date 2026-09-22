"""Tests for the governance-docs generator: table order, markers, and drift on the real tree."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from scripts.common.errors import ExitCode, MissingPathError
from scripts.harness.governance_docs import (
    AREAS,
    MissingDocstringError,
    MissingMarkerError,
    UnparsableModuleError,
    main,
    module_rows,
    render,
    render_table,
    write,
)

if TYPE_CHECKING:
    from pathlib import Path

SKILL_PATH = ".claude/skills/marketplace-governance/SKILL.md"


def _write_module(root: Path, area: str, name: str, docstring: str) -> None:
    """Create one governed module with a given module docstring.

    Args:
        root: The scratch repository root.
        area: The `scripts/<area>` folder name.
        name: The module's bare file name.
        docstring: What its module docstring should say.
    """
    directory = root / "scripts" / area
    directory.mkdir(parents=True, exist_ok=True)
    _ = (directory / "__init__.py").write_text("", encoding="utf-8")
    _ = (directory / name).write_text(f'"""{docstring}\n\nMore detail.\n"""\n', encoding="utf-8")


def _write_skill(root: Path, body: str) -> None:
    """Write a minimal `marketplace-governance/SKILL.md` with one area's markers.

    Args:
        root: The scratch repository root.
        body: The text between the markers, verbatim.
    """
    path = root / SKILL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    header = "# Marketplace governance\n\n<!-- governance-docs:demo -->\n"
    footer = "<!-- /governance-docs:demo -->\n"
    _ = path.write_text(header + body + footer, encoding="utf-8")


def test_module_rows_orders_a_module_before_its_own_test(scratch_repo: Path) -> None:
    """`client.py` reads before `test_client.py`, so the pairing stays visible."""
    _write_module(scratch_repo, "demo", "test_client.py", "Tests for the client.")
    _write_module(scratch_repo, "demo", "client.py", "The client itself.")
    _write_module(scratch_repo, "demo", "labels.py", "The label taxonomy.")
    rows = module_rows(scratch_repo, "demo")
    assert [name for name, _ in rows] == ["client.py", "test_client.py", "labels.py"]


def test_module_rows_excludes_init(scratch_repo: Path) -> None:
    """The package marker carries no behaviour of its own, so it earns no row."""
    _write_module(scratch_repo, "demo", "client.py", "The client itself.")
    rows = module_rows(scratch_repo, "demo")
    assert "__init__.py" not in [name for name, _ in rows]


def test_module_rows_reads_the_first_docstring_line_only(scratch_repo: Path) -> None:
    """A second paragraph is detail for a reader of the source, not the table."""
    _write_module(scratch_repo, "demo", "client.py", "One line.")
    ((name, summary),) = module_rows(scratch_repo, "demo")
    assert name == "client.py"
    assert summary == "One line."


def test_module_rows_refuses_a_module_with_no_docstring(scratch_repo: Path) -> None:
    """A silently undocumented module would print an empty cell instead of failing the gate."""
    path = scratch_repo / "scripts" / "demo"
    path.mkdir(parents=True)
    _ = (path / "__init__.py").write_text("", encoding="utf-8")
    _ = (path / "client.py").write_text("x = 1\n", encoding="utf-8")
    with pytest.raises(MissingDocstringError):
        _ = module_rows(scratch_repo, "demo")


def test_module_rows_refuses_a_module_that_does_not_parse(scratch_repo: Path) -> None:
    """A syntax error names the file rather than surfacing a raw `SyntaxError`."""
    path = scratch_repo / "scripts" / "demo"
    path.mkdir(parents=True)
    _ = (path / "__init__.py").write_text("", encoding="utf-8")
    _ = (path / "client.py").write_text("def (:\n", encoding="utf-8")
    with pytest.raises(UnparsableModuleError):
        _ = module_rows(scratch_repo, "demo")


def test_render_table_shape() -> None:
    """The table is exactly the two-column form the skill embeds."""
    text = render_table([("a.py", "Does a."), ("b.py", "Does b.")])
    assert text == (
        "| File | Function |\n| --- | --- |\n| `a.py` | Does a. |\n| `b.py` | Does b. |"
    )


def test_render_table_of_no_rows() -> None:
    """An area that lost every module still renders a valid, empty table."""
    assert render_table([]) == "| File | Function |\n| --- | --- |"


def test_render_fills_the_marker_block(scratch_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The generated table replaces exactly what sits between the two markers.

    Args:
        scratch_repo: A scratch git working tree.
        monkeypatch: Narrows the generator to the one area this scratch tree has.
    """
    monkeypatch.setattr("scripts.harness.governance_docs.AREAS", ("demo",))
    _write_module(scratch_repo, "demo", "client.py", "The client itself.")
    _write_skill(scratch_repo, "stale content\n")
    text = render(scratch_repo)
    assert "stale content" not in text
    assert "| `client.py` | The client itself. |" in text
    assert text.startswith("# Marketplace governance")


def test_render_is_idempotent(scratch_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A second run changes nothing, so `make generate` leaves a clean tree.

    Args:
        scratch_repo: A scratch git working tree.
        monkeypatch: Narrows the generator to the one area this scratch tree has.
    """
    monkeypatch.setattr("scripts.harness.governance_docs.AREAS", ("demo",))
    _write_module(scratch_repo, "demo", "client.py", "The client itself.")
    _write_skill(scratch_repo, "stale content\n")
    assert write(scratch_repo) is True
    assert write(scratch_repo) is False


def test_render_refuses_an_area_with_no_marker_pair(
    scratch_repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A marker the skill file dropped fails the gate instead of silently keeping stale text.

    Args:
        scratch_repo: A scratch git working tree.
        monkeypatch: Narrows the generator to an area no marker names.
    """
    monkeypatch.setattr("scripts.harness.governance_docs.AREAS", ("missing",))
    _write_skill(scratch_repo, "no markers for the missing area here\n")
    with pytest.raises(MissingMarkerError):
        _ = render(scratch_repo)


def test_render_refuses_a_tree_without_the_skill_file(tmp_path: Path) -> None:
    """The generator names the missing file instead of raising `FileNotFoundError`.

    Args:
        tmp_path: pytest's per-test temporary directory.
    """
    with pytest.raises(MissingPathError):
        _ = render(tmp_path)


@pytest.mark.slow
def test_every_real_area_has_exactly_one_marker_pair(repo: Path) -> None:
    """`render` fails closed the day an area's markers go missing or get duplicated."""
    text = (repo / SKILL_PATH).read_text(encoding="utf-8")
    for area in AREAS:
        assert text.count(f"<!-- governance-docs:{area} -->") == 1, area
        assert text.count(f"<!-- /governance-docs:{area} -->") == 1, area


@pytest.mark.slow
def test_the_real_skill_file_is_current(repo: Path) -> None:
    """The tracked tables already match what every module's docstring says right now.

    Compares `render()`'s output against the file on disk without writing anything: `write()`
    would fix a real drift as a side effect of running the test, which is exactly the silent
    self-repair `make generate`'s own `git diff --exit-code` exists to catch instead.
    """
    assert render(repo) == (repo / SKILL_PATH).read_text(encoding="utf-8")


@pytest.mark.slow
def test_main_outside_a_repository_is_one_line(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Running the generator outside a working tree prints a sentence, not a traceback.

    Args:
        tmp_path: pytest's per-test temporary directory.
        capsys: Captures what the entrypoint printed.
        monkeypatch: Moves the process outside any git working tree.
    """
    monkeypatch.chdir(tmp_path)
    assert main([]) == int(ExitCode.USAGE)
    captured = capsys.readouterr()
    assert captured.err.startswith("error: ")
    assert "Traceback" not in captured.err
