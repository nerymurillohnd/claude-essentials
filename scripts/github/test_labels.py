"""Tests for the label taxonomy: shape, completeness, and the diff against GitHub (G1)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from scripts.common.jsontext import canonical_json
from scripts.common.plugins import repo_root
from scripts.github.labels import (
    DEFERRED_LABEL,
    LABELS_PATH,
    MAX_DESCRIPTION_LENGTH,
    PLUGIN_LABEL_COLOR,
    REQUIRED_LABELS,
    Label,
    derived_plugin_labels,
    desired_labels,
    load_labels,
    missing_required,
    plan,
    plan_lines,
    plugin_label_name,
    replaced_bump_labels,
    required_labels,
    truncate,
    validate,
)
from scripts.marketplace.conftest import PLUGIN_ID, write_file

if TYPE_CHECKING:
    from pathlib import Path


def label(name: str, *, color: str = "ededed", aliases: tuple[str, ...] = ()) -> Label:
    """Build a label for a fixture.

    Args:
        name: The label name.
        color: Six lowercase hex digits.
        aliases: Former names.

    Returns:
        The label.
    """
    return Label(name=name, color=color, description=f"{name} description", aliases=aliases)


def write_labels(root: Path, labels: list[dict[str, object]]) -> None:
    """Write a fixture taxonomy file.

    Args:
        root: The fixture repository root.
        labels: The entries to write.
    """
    write_file(root / LABELS_PATH, canonical_json(labels))


def test_truncate_marks_a_cut_description() -> None:
    """GitHub rejects a longer description, so it is cut rather than refused."""
    cut = truncate("x" * 200)
    assert len(cut) == MAX_DESCRIPTION_LENGTH
    assert cut.endswith("…")


def test_truncate_leaves_a_short_description_alone() -> None:
    """Most descriptions fit and must stay byte-identical."""
    assert truncate("short") == "short"


@pytest.mark.slow
def test_the_tracked_taxonomy_parses() -> None:
    """Every entry of `.github/labels.json` has the four fields this module reads."""
    assert len(load_labels(repo_root())) > 0


@pytest.mark.slow
def test_the_tracked_taxonomy_is_valid() -> None:
    """Names, colors, descriptions, aliases and completeness all pass on the real file."""
    assert validate(repo_root()) == []


@pytest.mark.slow
def test_no_required_label_is_missing() -> None:
    """Every label an automation applies is declared, `bump: removal` included."""
    assert missing_required(repo_root()) == []


@pytest.mark.slow
def test_the_taxonomy_no_longer_invites_pull_requests() -> None:
    """D5: `good first issue` implies an outside pull request, which is closed on arrival."""
    assert "good first issue" not in {label.name for label in load_labels(repo_root())}


@pytest.mark.slow
def test_the_derived_plugin_labels_cover_every_plugin() -> None:
    """A plugin cannot ship without the label issues and pull requests are filtered by."""
    root = repo_root()
    names = {item.name for item in derived_plugin_labels(root)}
    assert names <= required_labels(root)
    assert all(item.color == PLUGIN_LABEL_COLOR for item in derived_plugin_labels(root))


def test_a_derived_label_description_fits_github(tree: Path) -> None:
    """A plugin description is longer than a label description may be."""
    for item in derived_plugin_labels(tree):
        assert len(item.description) <= MAX_DESCRIPTION_LENGTH


def test_a_renamed_plugin_keeps_its_old_label_as_an_alias(tree: Path) -> None:
    """The rename edits the existing label, so issues already tagged keep the tag."""
    write_file(
        tree / ".claude-plugin" / "marketplace.json",
        canonical_json(
            {
                "name": "test-market",
                "owner": {"name": "Test"},
                "renames": {"old-name": PLUGIN_ID},
                "plugins": [],
            },
        ),
    )
    derived = derived_plugin_labels(tree)
    assert derived[0].aliases == (plugin_label_name("old-name"),)


def test_a_long_name_is_refused(tree: Path) -> None:
    """GitHub's limit is 50 characters, which is why a plugin name is capped at 42."""
    write_labels(tree, [{"name": "x" * 51, "color": "ededed", "description": ""}])
    assert any("characters" in finding.message for finding in validate(tree))


def test_a_bad_color_is_refused(tree: Path) -> None:
    """The API takes six hex digits with no leading `#`."""
    write_labels(tree, [{"name": "type: bug", "color": "#FFF", "description": ""}])
    assert any("hex digits" in finding.message for finding in validate(tree))


def test_a_duplicate_name_is_refused(tree: Path) -> None:
    """Two entries with one name make the applied description depend on file order."""
    entry: dict[str, object] = {"name": "type: bug", "color": "ededed", "description": ""}
    write_labels(tree, [entry, dict(entry)])
    assert any("declared twice" in finding.message for finding in validate(tree))


def test_an_alias_that_is_also_a_label_is_refused(tree: Path) -> None:
    """The rename would delete a label that is still part of the taxonomy."""
    write_labels(
        tree,
        [
            {"name": "type: bug", "color": "ededed", "description": "", "aliases": ["bug"]},
            {"name": "bug", "color": "ededed", "description": ""},
        ],
    )
    assert any("itself a label" in finding.message for finding in validate(tree))


def test_an_alias_shared_by_two_labels_is_refused(tree: Path) -> None:
    """Which label the rename lands on would depend on file order."""
    write_labels(
        tree,
        [
            {"name": "type: bug", "color": "ededed", "description": "", "aliases": ["old"]},
            {"name": "type: docs", "color": "ededed", "description": "", "aliases": ["old"]},
        ],
    )
    assert any("alias of both" in finding.message for finding in validate(tree))


def test_a_missing_required_label_is_refused(tree: Path) -> None:
    """An automation that applies a label the taxonomy never declares creates drift."""
    write_labels(tree, [])
    messages = [finding.message for finding in validate(tree)]
    assert any(REQUIRED_LABELS[0] in message for message in messages)


def test_plan_creates_what_github_does_not_have() -> None:
    """A brand-new label is created, not renamed."""
    result = plan([label("bump: removal")], [])
    assert [item.name for item in result.creates] == ["bump: removal"]


def test_plan_updates_a_label_whose_text_moved() -> None:
    """A description edit in the file reaches GitHub on the next sync."""
    remote = Label(name="type: bug", color="ededed", description="old")
    result = plan([label("type: bug")], [remote])
    assert [item.name for item in result.updates] == ["type: bug"]


def test_plan_leaves_an_identical_label_alone() -> None:
    """A clean dry run says so and sends nothing."""
    identical = label("type: bug")
    assert plan([identical], [identical]).is_empty()


def test_plan_renames_through_an_alias() -> None:
    """Renaming keeps the label on every issue that already carries it."""
    remote = Label(name="bug", color="ededed", description="old")
    result = plan([label("type: bug", aliases=("bug",))], [remote])
    assert result.renames == (("bug", result.renames[0][1]),)
    assert result.creates == ()


def test_plan_prunes_what_the_taxonomy_dropped() -> None:
    """Pruning is planned so it can be reviewed; CI never applies it."""
    result = plan([], [label("wontfix")])
    assert result.prunes == ("wontfix",)


def test_plan_lines_say_there_is_nothing_to_do() -> None:
    """The line a clean dry run prints."""
    assert plan_lines(plan([], [])) == ["labels: GitHub already matches the taxonomy"]


def test_plan_lines_name_every_action() -> None:
    """One line per action, so a dry run is reviewable."""
    result = plan([label("a"), label("b", aliases=("old-b",))], [label("c")])
    lines = plan_lines(result)
    assert any(line.startswith("create a") for line in lines)
    assert any(line.startswith("prune") for line in lines)


@pytest.mark.parametrize(
    ("current", "desired", "expected"),
    [
        ({"bump: patch"}, "bump: minor", ["bump: patch"]),
        ({"bump: none"}, "bump: none", []),
        ({DEFERRED_LABEL, "bump: patch"}, "bump: none", ["bump: patch"]),
        ({DEFERRED_LABEL}, "bump: none", []),
        ({"area: docs"}, "bump: none", []),
        ({"bump: patch"}, None, ["bump: patch"]),
    ],
)
def test_the_computed_bump_replaces_every_other_one_but_deferred(
    current: set[str], desired: str | None, expected: list[str]
) -> None:
    """`bump: deferred` is maintainer-applied and PR-wide, so triage never removes it."""
    assert replaced_bump_labels(current, desired) == expected


@pytest.mark.slow
def test_desired_labels_is_the_file_plus_the_derived_family() -> None:
    """The one list `sync_labels` diffs against GitHub."""
    root = repo_root()
    assert len(desired_labels(root)) == len(load_labels(root)) + len(derived_plugin_labels(root))
