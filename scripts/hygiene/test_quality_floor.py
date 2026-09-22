"""Q1: the quality floor, everywhere. No second config, no downgraded rule, no escape hatch.

The defect: a seeded `extend-ignore`, a `reportAny = false`, a re-created `ruff.toml`. Each
one is a single line that makes the gate quieter while every command still exits 0, so the
repository looks green and checks less than it did the day before.

Three shapes of escape hatch are closed here. **A second configuration file** —
`.ruff.toml`, `ruff.toml` and `pyrightconfig.json` all take precedence over `pyproject.toml`,
so their existence alone replaces the policy. **A downgraded rule** — a `report* = false`, a
`diagnosticSeverityOverrides`, a `per-file-ignores`, an `ignore` outside the recorded list.
**A baseline** — `baselineFile` and `.basedpyright/` suppress every pre-existing error by
design and keep doing it as new ones arrive.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

import pytest

from scripts.common.jsontext import is_json_object
from scripts.hygiene.conftest import (
    PYPROJECT,
    SHELLCHECKRC,
    nested,
    shellcheck_directives,
    string_list,
    toml_document,
)

if TYPE_CHECKING:
    from pathlib import Path

COMPETING_CONFIGS: Final[tuple[str, ...]] = ("ruff.toml", ".ruff.toml", "pyrightconfig.json")
"""Each of these takes precedence over `pyproject.toml`, so each replaces the policy."""

FLOOR_FAMILIES: Final[tuple[str, ...]] = (
    "E",
    "W",
    "F",
    "I",
    "UP",
    "B",
    "BLE",
    "SIM",
    "C90",
    "ANN",
    "D",
    "N",
    "S",
    "PL",
    "TRY",
    "RUF",
    "PTH",
    "TC",
    "ARG",
)
"""The families the floor turns on; `select` has to carry every one of them."""

ALLOWED_IGNORES: Final[frozenset[str]] = frozenset(
    {
        # Formatter conflicts, exactly as Ruff's own documentation lists them.
        "W191",
        "E111",
        "E114",
        "E117",
        "D203",
        "D206",
        "D300",
        "Q000",
        "Q001",
        "Q002",
        "Q003",
        "Q004",
        "COM812",
        "COM819",
        "ISC002",
        # The recorded practical ignores, identical to the maintainer's global policy.
        "D100",
        "D104",
        "D213",
        "S101",
        "S603",
        "INP001",
    }
)
"""The closed ignore list. Anything else is a rule someone turned off in place."""

MAX_COMPLEXITY: Final = 8
"""The mccabe ceiling; a higher one would let a branchier function through."""

MAX_LINE_LENGTH: Final = 100
"""The line length the editor's ruler and `.editorconfig` also carry."""

ALLOWED_REPORT_KEY: Final = "reportImplicitStringConcatenation"
"""The one pre-declared downgrade: the check the Ruff floor itself ignores as `ISC002`."""

REQUIRED_BASEDPYRIGHT: Final[dict[str, object]] = {
    "typeCheckingMode": "all",
    "failOnWarnings": True,
    "enableTypeIgnoreComments": False,
    "allowedUntypedLibraries": [],
}
"""The settings that make basedpyright the strictest it can be, with no ignore comments."""

SHELLCHECK_ENABLES: Final[tuple[str, ...]] = (
    "add-default-case",
    "avoid-negated-conditions",
    "avoid-nullary-conditions",
    "check-extra-masked-returns",
    "check-set-e-suppressed",
    "check-unassigned-uppercase",
    "deprecate-which",
    "quote-safe-variables",
    "require-variable-braces",
    "useless-use-of-cat",
)
"""All ten optional checks the floor turns on."""


@pytest.mark.parametrize("name", COMPETING_CONFIGS)
def test_no_competing_configuration_file_exists(repo: Path, name: str) -> None:
    """Each of these silently replaces the policy, because each takes precedence over it."""
    assert not (repo / name).exists(), f"{name} would take precedence over {PYPROJECT}"


def test_the_selected_families_cover_the_floor(repo: Path) -> None:
    """A family left out of `select` is a whole class of finding nothing reports."""
    document = toml_document(repo / PYPROJECT)
    selected = set(string_list(nested(document, "tool", "ruff", "lint", "select")))
    assert [family for family in FLOOR_FAMILIES if family not in selected] == []


def test_nothing_outside_the_recorded_list_is_ignored(repo: Path) -> None:
    """An ignore added in place is a rule turned off with no record of why."""
    document = toml_document(repo / PYPROJECT)
    ignored = set(string_list(nested(document, "tool", "ruff", "lint", "ignore")))
    assert sorted(ignored - ALLOWED_IGNORES) == []


def test_there_are_no_per_file_ignores(repo: Path) -> None:
    """A per-file ignore is an exemption with no expiry and no owner."""
    document = toml_document(repo / PYPROJECT)
    assert nested(document, "tool", "ruff", "lint", "per-file-ignores") is None


def test_the_thresholds_are_at_or_below_the_floor(repo: Path) -> None:
    """A raised ceiling lets in exactly what the ceiling existed to keep out."""
    document = toml_document(repo / PYPROJECT)
    assert nested(document, "tool", "ruff", "lint", "mccabe", "max-complexity") == MAX_COMPLEXITY
    assert nested(document, "tool", "ruff", "line-length") == MAX_LINE_LENGTH


def test_the_ruff_version_floor_is_pinned(repo: Path) -> None:
    """Without `required-version`, an older Ruff quietly applies fewer rules."""
    required = nested(toml_document(repo / PYPROJECT), "tool", "ruff", "required-version")
    assert isinstance(required, str)
    assert required.startswith(">=")


@pytest.mark.parametrize(("key", "value"), sorted(REQUIRED_BASEDPYRIGHT.items()))
def test_basedpyright_runs_at_its_strictest(repo: Path, key: str, value: object) -> None:
    """`all` plus `failOnWarnings` is the floor; anything less is a quieter gate."""
    assert nested(toml_document(repo / PYPROJECT), "tool", "basedpyright", key) == value


def test_only_the_pre_declared_rule_is_downgraded(repo: Path) -> None:
    """One downgrade is a decision; a second is a habit, and it would not be recorded."""
    section = nested(toml_document(repo / PYPROJECT), "tool", "basedpyright")
    assert is_json_object(section)
    disabled = {
        key for key, value in section.items() if value is False and key.startswith("report")
    }
    assert disabled <= {ALLOWED_REPORT_KEY}, sorted(disabled - {ALLOWED_REPORT_KEY})


def test_no_severity_override_and_no_baseline(repo: Path) -> None:
    """A baseline suppresses every pre-existing error by design and keeps doing it."""
    section = nested(toml_document(repo / PYPROJECT), "tool", "basedpyright")
    assert is_json_object(section)
    assert "diagnosticSeverityOverrides" not in section
    assert "baselineFile" not in section


def test_no_basedpyright_baseline_directory_exists(repo: Path) -> None:
    """`--writebaseline` creates it; its presence alone makes the gate report less."""
    assert not (repo / ".basedpyright").exists()


def test_the_shellcheck_policy_disables_nothing(repo: Path) -> None:
    """A repository-wide `disable=` turns a whole class of shell defect invisible."""
    directives = shellcheck_directives((repo / SHELLCHECKRC).read_text(encoding="utf-8"))
    assert [line for line in directives if line.startswith("disable=")] == []


@pytest.mark.parametrize("check", SHELLCHECK_ENABLES)
def test_every_optional_shellcheck_check_is_on(repo: Path, check: str) -> None:
    """The optional checks are the half of ShellCheck that is off by default."""
    directives = shellcheck_directives((repo / SHELLCHECKRC).read_text(encoding="utf-8"))
    assert f"enable={check}" in directives
