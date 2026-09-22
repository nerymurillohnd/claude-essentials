"""The label taxonomy as code: what it must contain, and how it is reconciled with GitHub.

`.github/labels.json` is the source of truth for every label except `plugin: <id>`, which is
derived from `plugins/` so a new plugin cannot ship without its label (ADR-0004). This module
answers two questions and nothing else:

* **Is the taxonomy well formed and complete?** `validate` is the G1 half that reads only
  files: names inside GitHub's limits, six-digit colors, no duplicate name, no alias that
  collides with a name or with another alias, and every label the automations apply present.
* **What would it take to make GitHub match?** `plan` diffs the desired set against the live
  one and returns creates, updates, renames and prunes. A rename edits the existing label's
  `name` rather than creating a new one, so every issue already carrying it keeps it.

Pruning is planned but never applied by CI: deleting a label removes it from every issue it
was ever on, which no automated run should do on its own (ADR-0004).
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import TYPE_CHECKING, Final

from scripts.common.errors import Finding, MaintainerError
from scripts.common.jsontext import is_json_array, is_json_object
from scripts.common.plugins import as_str, load_json, plugin_ids
from scripts.marketplace.catalog import manifest_path
from scripts.versioning.version_plan import read_renames

if TYPE_CHECKING:
    from collections.abc import Collection, Iterable, Mapping, Sequence
    from pathlib import Path

LABELS_PATH: Final = ".github/labels.json"
"""Where the authored half of the taxonomy lives."""

MAX_NAME_LENGTH: Final = 50
"""GitHub's limit; `plugin: <id>` is why plugin names are capped at 42 (M6)."""

MAX_DESCRIPTION_LENGTH: Final = 100
"""GitHub's limit; a longer description is truncated rather than rejected."""

ELLIPSIS: Final = "…"
"""What a truncated description ends with."""

COLOR_RE: Final = re.compile(r"^[0-9a-f]{6}$")
"""Six lowercase hex digits, with no leading `#`, which is what the API accepts."""

PLUGIN_LABEL_PREFIX: Final = "plugin: "
"""The derived family; one label per directory under `plugins/`."""

PLUGIN_LABEL_COLOR: Final = "5319e7"
"""The color every derived plugin label carries."""

BUMP_LABEL_PREFIX: Final = "bump: "
"""The computed family `triage` recomputes on every push to a pull request."""

DEFERRED_LABEL: Final = "bump: deferred"
"""Maintainer-applied and never recomputed, so triage leaves it alone (§A11)."""

REQUIRED_LABELS: Final[tuple[str, ...]] = (
    "type: bug",
    "type: feature",
    "type: plugin-proposal",
    "type: docs",
    "type: maintenance",
    "type: security",
    "status: needs-triage",
    "status: needs-info",
    "status: accepted",
    "status: blocked",
    "status: stale",
    "priority: critical",
    "priority: high",
    "priority: low",
    "area: plugins",
    "area: catalog",
    "area: ci",
    "area: tooling",
    "area: templates",
    "area: docs",
    "area: community",
    "bump: major",
    "bump: minor",
    "bump: patch",
    "bump: prerelease",
    "bump: initial",
    "bump: none",
    "bump: removal",
    DEFERRED_LABEL,
    "help wanted",
)
"""Every label an automation applies, so none of them can reference something absent (G1).

`bump: removal` is the removal lifecycle case (§A11). `good first issue` is not in the
taxonomy at all (D5: this repository takes issues, not external pull requests); the `Labels`
workflow never prunes, so the live label stays until a maintainer runs `--prune`.
"""


@dataclass(frozen=True, slots=True)
class Label:
    """One label, as `.github/labels.json` writes it and as the API stores it.

    Attributes:
        name: The label text GitHub shows.
        color: Six lowercase hex digits, with no leading `#`.
        description: What it means, at most `MAX_DESCRIPTION_LENGTH` characters.
        aliases: Former names that should be renamed into this one rather than recreated.
    """

    name: str
    color: str
    description: str
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class LabelPlan:
    """What it would take to make GitHub match the taxonomy.

    Attributes:
        creates: Labels that do not exist remotely under any known name.
        updates: Labels whose color or description differs remotely.
        renames: Pairs of the remote name to edit and the label it becomes.
        prunes: Remote labels the taxonomy no longer contains; never applied by CI.
    """

    creates: tuple[Label, ...]
    updates: tuple[Label, ...]
    renames: tuple[tuple[str, Label], ...]
    prunes: tuple[str, ...]

    def is_empty(self) -> bool:
        """Report whether GitHub already matches the taxonomy.

        Returns:
            True when there is nothing to create, update, rename or prune.
        """
        return not (self.creates or self.updates or self.renames or self.prunes)


def truncate(text: str, limit: int = MAX_DESCRIPTION_LENGTH) -> str:
    """Shorten a description to what GitHub accepts, marking that it was cut.

    Args:
        text: The full description.
        limit: The maximum length, including the ellipsis.

    Returns:
        The text unchanged, or its first `limit - 1` characters plus an ellipsis.
    """
    if len(text) <= limit:
        return text
    return text[: limit - 1] + ELLIPSIS


def _label_from(entry: Mapping[str, object], *, path: Path) -> Label:
    """Narrow one parsed entry of `labels.json` into a label.

    Args:
        entry: The parsed object.
        path: The file it came from, named in the error.

    Returns:
        The label.

    Raises:
        UnexpectedShapeError: If a field is missing or of the wrong type.
    """
    raw_aliases = entry.get("aliases")
    aliases = (
        tuple(as_str(alias, path=path) for alias in raw_aliases)
        if is_json_array(raw_aliases)
        else ()
    )
    return Label(
        name=as_str(entry.get("name"), path=path),
        color=as_str(entry.get("color"), path=path),
        description=as_str(entry.get("description"), path=path),
        aliases=aliases,
    )


def load_labels(root: Path) -> tuple[Label, ...]:
    """Read the authored half of the taxonomy.

    Args:
        root: The repository root.

    Returns:
        Every label `.github/labels.json` declares, in file order.

    Raises:
        UnexpectedShapeError: If the file is not an array of well-formed objects.
        MalformedJsonError: If the file is not valid JSON.
    """
    path = root / LABELS_PATH
    parsed = load_json(path)
    if not is_json_array(parsed):
        return ()
    return tuple(_label_from(entry, path=path) for entry in parsed if is_json_object(entry))


def plugin_label_name(plugin_id: str) -> str:
    """Return the derived label of one plugin.

    Args:
        plugin_id: The plugin directory name.

    Returns:
        The label GitHub carries for that plugin.
    """
    return f"{PLUGIN_LABEL_PREFIX}{plugin_id}"


def derived_plugin_labels(root: Path) -> tuple[Label, ...]:
    """Build one label per plugin on disk, described by that plugin's own description.

    A plugin renamed in the catalog carries its former label as an alias, so the rename edits
    the existing label and every issue already tagged with it keeps the tag (§A11).

    Args:
        root: The repository root.

    Returns:
        One label per plugin directory, ordered by name.

    Raises:
        MaintainerError: If a manifest cannot be read or has the wrong shape.
    """
    renames = read_renames(root)
    backwards: dict[str, list[str]] = {}
    for old, new in renames.items():
        if new is not None:
            backwards.setdefault(new, []).append(old)
    labels: list[Label] = []
    for plugin_id in plugin_ids(root):
        path = manifest_path(root, plugin_id)
        manifest = load_json(path)
        description = ""
        if is_json_object(manifest):
            raw = manifest.get("description")
            description = raw if isinstance(raw, str) else ""
        labels.append(
            Label(
                name=plugin_label_name(plugin_id),
                color=PLUGIN_LABEL_COLOR,
                description=truncate(description),
                aliases=tuple(
                    plugin_label_name(old) for old in sorted(backwards.get(plugin_id, []))
                ),
            ),
        )
    return tuple(labels)


def desired_labels(root: Path) -> tuple[Label, ...]:
    """Build the whole taxonomy: the authored file plus the derived plugin labels.

    Args:
        root: The repository root.

    Returns:
        Every label GitHub should carry.

    Raises:
        MaintainerError: If the file or a manifest cannot be read.
    """
    return (*load_labels(root), *derived_plugin_labels(root))


def required_labels(root: Path) -> frozenset[str]:
    """Return every label name an automation depends on.

    Args:
        root: The repository root.

    Returns:
        The fixed families plus one `plugin: <id>` per plugin on disk.
    """
    return frozenset(REQUIRED_LABELS) | {
        plugin_label_name(plugin_id) for plugin_id in plugin_ids(root)
    }


def _shape_findings(labels: Sequence[Label]) -> list[Finding]:
    """Check names, colors and uniqueness across the taxonomy (G1).

    Args:
        labels: Every label the taxonomy declares.

    Returns:
        One finding per rule broken.
    """
    findings: list[Finding] = []
    seen: set[str] = set()
    for label in labels:
        if len(label.name) > MAX_NAME_LENGTH:
            findings.append(
                Finding(
                    "G1",
                    LABELS_PATH,
                    f"{label.name!r} is {len(label.name)} characters; GitHub allows "
                    f"{MAX_NAME_LENGTH}",
                ),
            )
        if COLOR_RE.match(label.color) is None:
            findings.append(
                Finding(
                    "G1",
                    LABELS_PATH,
                    f"{label.name!r} has color {label.color!r}, not six lowercase hex digits",
                ),
            )
        if len(label.description) > MAX_DESCRIPTION_LENGTH:
            findings.append(
                Finding(
                    "G1",
                    LABELS_PATH,
                    f"{label.name!r} has a {len(label.description)}-character description; "
                    f"GitHub allows {MAX_DESCRIPTION_LENGTH}",
                ),
            )
        if label.name in seen:
            findings.append(Finding("G1", LABELS_PATH, f"{label.name!r} is declared twice"))
        seen.add(label.name)
    return findings


def _alias_findings(labels: Sequence[Label]) -> list[Finding]:
    """Check that no alias collides with a name or with another alias (G1).

    Args:
        labels: Every label the taxonomy declares.

    Returns:
        One finding per collision.
    """
    names = {label.name for label in labels}
    findings: list[Finding] = []
    owner: dict[str, str] = {}
    for label in labels:
        for alias in label.aliases:
            if alias in names:
                findings.append(
                    Finding(
                        "G1",
                        LABELS_PATH,
                        f"{label.name!r} aliases {alias!r}, which is itself a label",
                    ),
                )
            if alias in owner:
                findings.append(
                    Finding(
                        "G1",
                        LABELS_PATH,
                        f"{alias!r} is an alias of both {owner[alias]!r} and {label.name!r}",
                    ),
                )
            owner[alias] = label.name
    return findings


def validate(root: Path) -> list[Finding]:
    """Check the taxonomy's shape and completeness (G1, the file half).

    The cross-check against the issue forms lives in `issue_forms.validate_forms`, which is
    the module that already parses them.

    Args:
        root: The repository root.

    Returns:
        One finding per rule broken.
    """
    try:
        labels = desired_labels(root)
    except MaintainerError as error:
        return [Finding("G1", LABELS_PATH, str(error))]
    findings = [*_shape_findings(labels), *_alias_findings(labels)]
    declared = {label.name for label in labels}
    missing = sorted(required_labels(root) - declared)
    findings.extend(
        Finding("G1", LABELS_PATH, f"{name!r} is applied by an automation but not declared")
        for name in missing
    )
    return findings


def missing_required(root: Path) -> list[str]:
    """Return the required labels the taxonomy does not declare yet.

    Args:
        root: The repository root.

    Returns:
        The missing names, sorted.

    Raises:
        MaintainerError: If the taxonomy cannot be read.
    """
    declared = {label.name for label in desired_labels(root)}
    return sorted(required_labels(root) - declared)


def plan(local: Iterable[Label], remote: Iterable[Label]) -> LabelPlan:
    """Diff the taxonomy against the labels GitHub currently carries.

    Args:
        local: The desired taxonomy.
        remote: The labels read from the API.

    Returns:
        What to create, update, rename and prune to make the two match.
    """
    remote_by_name = {label.name: label for label in remote}
    consumed: set[str] = set()
    creates: list[Label] = []
    updates: list[Label] = []
    renames: list[tuple[str, Label]] = []
    for label in local:
        existing = remote_by_name.get(label.name)
        if existing is not None:
            consumed.add(label.name)
            if (existing.color, existing.description) != (label.color, label.description):
                updates.append(label)
            continue
        former = next((alias for alias in label.aliases if alias in remote_by_name), None)
        if former is None:
            creates.append(label)
        else:
            consumed.add(former)
            renames.append((former, label))
    prunes = tuple(sorted(name for name in remote_by_name if name not in consumed))
    return LabelPlan(
        creates=tuple(creates),
        updates=tuple(updates),
        renames=tuple(renames),
        prunes=prunes,
    )


def plan_lines(label_plan: LabelPlan) -> list[str]:
    """Render a plan for a maintainer reading a dry run.

    Args:
        label_plan: The plan to render.

    Returns:
        One line per action, or a single line saying there is nothing to do.
    """
    if label_plan.is_empty():
        return ["labels: GitHub already matches the taxonomy"]
    lines = [f"create {label.name}" for label in label_plan.creates]
    lines.extend(f"update {label.name}" for label in label_plan.updates)
    lines.extend(f"rename {old} -> {label.name}" for old, label in label_plan.renames)
    lines.extend(f"prune  {name}" for name in label_plan.prunes)
    return lines


def replaced_bump_labels(current: Collection[str], desired: str | None) -> list[str]:
    """Return the `bump:` labels a triage run removes from a pull request.

    `bump: deferred` is maintainer-applied and PR-wide, so it is never removed (§A11).

    Args:
        current: The labels the pull request carries now.
        desired: The computed `bump:` label, or None when none could be computed.

    Returns:
        The labels to remove, sorted.
    """
    return sorted(
        name
        for name in current
        if name.startswith(BUMP_LABEL_PREFIX) and name not in {DEFERRED_LABEL, desired}
    )
