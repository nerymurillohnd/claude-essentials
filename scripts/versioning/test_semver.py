"""Tests for canonical version parsing, ordering and the bump level (M5)."""

from __future__ import annotations

import itertools
import re

import pytest

from scripts.versioning.semver import (
    BumpLevel,
    InvalidVersionError,
    Version,
    bump_level,
    is_valid,
    parse,
)

ASCENDING = (
    "0.1.0",
    "0.2.0",
    "0.10.0",
    "1.0.0-beta.1",
    "1.0.0-beta.2",
    "1.0.0-beta.10",
    "1.0.0-rc.1",
    "1.0.0-rc.2",
    "1.0.0",
    "1.0.1",
    "1.1.0",
    "2.0.0",
)
"""Every ordering rule in one table: prereleases below their release, beta below rc, numbers
compared as integers rather than as text."""


def test_parse_reads_a_plain_release() -> None:
    """The three components arrive as integers, with no prerelease."""
    assert parse("1.2.3") == Version(1, 2, 3)


def test_parse_reads_a_prerelease() -> None:
    """The prerelease identifier keeps its number as an integer."""
    assert parse("2.0.0-rc.11") == Version(2, 0, 0, ("rc", 11))


def test_str_round_trips_every_version_in_the_table() -> None:
    """A version renders exactly as the manifest and the tag spell it."""
    for text in ASCENDING:
        assert str(parse(text)) == text


@pytest.mark.parametrize(
    ("lower", "higher"),
    list(itertools.combinations(ASCENDING, 2)),
)
def test_ordering_follows_semver_org(lower: str, higher: str) -> None:
    """Every pair of the table orders the way semver.org says it must."""
    first, second = parse(lower), parse(higher)
    assert first < second
    assert second > first
    assert first <= second
    assert second >= first
    assert first != second


def test_equal_versions_compare_both_ways() -> None:
    """`<=` and `>=` hold for two spellings of the same version."""
    assert parse("1.0.0") <= parse("1.0.0")
    assert parse("1.0.0") >= parse("1.0.0")
    assert not parse("1.0.0") < parse("1.0.0")


@pytest.mark.parametrize(
    "text",
    [
        "v1.0.0",
        "1.0",
        "1",
        "1.0.0.0",
        "1.0.0+build.1",
        "1.0.0-rc.1+build.1",
        "1.0.0-alpha.1",
        "1.0.0-beta",
        "1.0.0-beta.01",
        "01.0.0",
        "1.0.0 ",
        " 1.0.0",
        "1.0.0\n",
        "",
        "latest",
    ],
)
def test_parse_rejects_everything_outside_the_grammar(text: str) -> None:
    """The defect M5 names: the official CLI accepts shapes this repository must not."""
    assert not is_valid(text)
    with pytest.raises(InvalidVersionError, match=re.escape("is not a canonical version")):
        _ = parse(text)


def test_the_rejection_message_quotes_what_was_rejected() -> None:
    """A gate line has to say which string failed, not only that one did."""
    with pytest.raises(InvalidVersionError, match=re.escape("'1.0'")):
        _ = parse("1.0")


@pytest.mark.parametrize(
    ("old", "new", "expected"),
    [
        ("1.2.3", "1.2.3", "none"),
        ("1.2.3", "2.0.0", "major"),
        ("1.2.3", "1.3.0", "minor"),
        ("1.2.3", "1.2.4", "patch"),
        ("0.1.0", "0.2.0", "minor"),
        ("1.0.0-beta.1", "1.0.0-beta.2", "prerelease"),
        ("1.0.0-beta.2", "1.0.0-rc.1", "prerelease"),
        ("1.0.0-rc.1", "1.0.0", "prerelease"),
        ("1.0.0", "2.0.0-rc.1", "major"),
        ("1.2.3", "1.2.2", "invalid"),
        ("2.0.0", "1.9.9", "invalid"),
        ("1.0.0", "1.0.0-rc.1", "invalid"),
    ],
)
def test_bump_level_classifies_the_move(old: str, new: str, expected: BumpLevel) -> None:
    """The label a pull request carries comes from this classification."""
    assert bump_level(parse(old), parse(new)) == expected


def test_a_decrease_is_invalid_rather_than_a_level() -> None:
    """ADR-0003 never lowers a published version; the gate has to say so, not pick a level."""
    assert bump_level(parse("0.1.2"), parse("0.1.1")) == "invalid"
