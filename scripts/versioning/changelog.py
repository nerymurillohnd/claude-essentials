"""Parsing and the three CHANGELOG invariants: P3 (entry), C1 (links) and C2 (immutability).

A plugin's `CHANGELOG.md` is the release notes Claude Code shows for a tagged version, so it
is checked like code rather than like prose. Three defects are caught here:

* **P3** — a manifest version with no dated `## [X.Y.Z] - YYYY-MM-DD` section: the release
  ships with no notes at all.
* **C1** — mixed footer link styles. The first released version links to `tree/<tag>`; every
  later one links to `compare/<previous tag>...<tag>`, and `[Unreleased]` compares the latest
  tag with `HEAD`. Three plugins currently link a second release with `tree/`, which sends a
  reader to a snapshot instead of to the diff they asked for.
* **C2** — a released section rewritten after its tag. The tag is immutable, so the notes a
  user reads for `0.1.0` must be the notes that shipped with `0.1.0`; corrections belong under
  `## [Unreleased]` in an `### Errata` block, and only the footer links may be repaired.

Nothing here runs git except `released_body_at_tag`, so the parser and both text checks are
pure functions a test can drive with a string.
"""

from __future__ import annotations

from dataclasses import dataclass
import datetime as dt
import re
from typing import TYPE_CHECKING, Final

from scripts.common.errors import Finding
from scripts.common.plugins import git_output_or_none
from scripts.versioning.semver import is_valid, parse

if TYPE_CHECKING:
    from collections.abc import Collection, Sequence
    from pathlib import Path

UNRELEASED_LABEL: Final = "Unreleased"
"""The label of the section that holds changes with no version yet."""

ERRATA_HEADING: Final = "### Errata"
"""Where a correction to an already released section is written instead (C2)."""

DEPRECATION_HEADING: Final = "### Deprecated"
"""What a deprecation release must announce before the plugin may be removed."""

SECTION_PATTERN: Final = re.compile(
    r"^## \[(?P<label>[^\]]+)\](?: - (?P<date>\d{4}-\d{2}-\d{2}))?\s*$",
)
"""A `## [Unreleased]` or `## [X.Y.Z] - YYYY-MM-DD` heading."""

LINK_PATTERN: Final = re.compile(r"^\[(?P<label>[^\]]+)\]: (?P<url>\S+)\s*$")
"""One footer reference definition."""

_TREE_MARKER: Final = "/tree/"
_COMPARE_MARKER: Final = "/compare/"


@dataclass(frozen=True, slots=True)
class Section:
    """One `##` section of a CHANGELOG.

    Attributes:
        label: `Unreleased`, or the version between the brackets.
        date: The `YYYY-MM-DD` after the heading, or None when the heading carries none.
        body: Everything under the heading up to the next one, with blank edges removed.
        line: The 1-based line number of the heading, for a finding a reader can jump to.
    """

    label: str
    date: str | None
    body: str
    line: int


@dataclass(frozen=True, slots=True)
class Changelog:
    """A parsed CHANGELOG.

    Attributes:
        sections: Every `##` section in file order.
        links: The trailing footer reference definitions, in file order.
    """

    sections: tuple[Section, ...]
    links: tuple[tuple[str, str], ...]

    def unreleased(self) -> Section | None:
        """Return the `## [Unreleased]` section.

        Returns:
            The section, or None when the file has none.
        """
        return self.find(UNRELEASED_LABEL)

    def released(self) -> tuple[Section, ...]:
        """Return the version sections, oldest first.

        Returns:
            Every section whose label parses as a canonical version, in ascending order.
        """
        versions = [section for section in self.sections if is_valid(section.label)]
        return tuple(sorted(versions, key=lambda section: parse(section.label).sort_key()))

    def find(self, label: str) -> Section | None:
        """Return the section carrying a label.

        Args:
            label: `Unreleased` or a version string.

        Returns:
            The section, or None when no heading carries that label.
        """
        for section in self.sections:
            if section.label == label:
                return section
        return None

    def link(self, label: str) -> str | None:
        """Return the footer URL defined for a label.

        Args:
            label: `Unreleased` or a version string.

        Returns:
            The URL, or None when the footer defines none.
        """
        for defined, url in self.links:
            if defined == label:
                return url
        return None


def _split_footer(lines: Sequence[str]) -> tuple[list[str], list[tuple[str, str]]]:
    """Separate the trailing block of reference definitions from the body of the file.

    The footer is the run of link definitions and blank lines at the end of the file, so a
    link written inside a section stays part of that section's body.

    Args:
        lines: Every line of the file, without line endings.

    Returns:
        The lines before the footer, and the footer's definitions in file order.
    """
    index = len(lines)
    links: list[tuple[str, str]] = []
    while index > 0:
        matched = LINK_PATTERN.match(lines[index - 1])
        if matched is not None:
            links.append((matched.group("label"), matched.group("url")))
        elif lines[index - 1].strip():
            break
        index -= 1
    links.reverse()
    return list(lines[:index]), links


def parse_changelog(text: str) -> Changelog:
    """Parse a CHANGELOG into its sections and its footer links.

    Args:
        text: The whole file.

    Returns:
        The parsed document.
    """
    lines = text.splitlines()
    body_lines, links = _split_footer(lines)
    sections: list[Section] = []
    label: str | None = None
    date: str | None = None
    heading_line = 0
    collected: list[str] = []
    for number, line in enumerate(body_lines, start=1):
        matched = SECTION_PATTERN.match(line)
        if matched is None:
            if label is not None:
                collected.append(line)
            continue
        if label is not None:
            sections.append(Section(label, date, "\n".join(collected).strip("\n"), heading_line))
        label = matched.group("label")
        date = matched.group("date")
        heading_line = number
        collected = []
    if label is not None:
        sections.append(Section(label, date, "\n".join(collected).strip("\n"), heading_line))
    return Changelog(tuple(sections), tuple(links))


def read_changelog(path: Path) -> Changelog:
    """Parse the CHANGELOG at a path.

    Args:
        path: The file to read.

    Returns:
        The parsed document.

    Raises:
        OSError: If the file cannot be read.
    """
    return parse_changelog(path.read_text(encoding="utf-8"))


def tag_name(version: str, *, names: Sequence[str], known_tags: Collection[str]) -> str:
    """Resolve which `<name>--v<version>` tag holds a version.

    A renamed plugin keeps the tags it was released under, so the candidates are the plugin's
    current name first and then its predecessors, newest first.

    Args:
        version: The version to resolve.
        names: The plugin's name followed by its predecessors.
        known_tags: The tags that exist; an empty collection means "assume the current name".

    Returns:
        The tag name, falling back to the current name when none of the candidates exists.
    """
    candidates = [f"{name}--v{version}" for name in names]
    for candidate in candidates:
        if candidate in known_tags:
            return candidate
    return candidates[0]


def _is_iso_date(text: str) -> bool:
    """Report whether a `YYYY-MM-DD` string is a real calendar date.

    Args:
        text: The date from a heading.

    Returns:
        True when the date exists; `2026-02-30` does not.
    """
    try:
        _ = dt.date.fromisoformat(text)
    except ValueError:
        return False
    return True


def check_entry(changelog: Changelog, *, version: str, path: str) -> list[Finding]:
    """Check P3: the manifest version has a dated section of its own.

    Args:
        changelog: The parsed CHANGELOG.
        version: The version in `plugin.json`.
        path: The repository-relative path of the CHANGELOG, named in the finding.

    Returns:
        Zero or one finding.
    """
    section = changelog.find(version)
    if section is None:
        return [
            Finding(
                "P3", path, f"no `## [{version}] - YYYY-MM-DD` section for the manifest version"
            )
        ]
    if section.date is None:
        return [Finding("P3", path, f"`## [{version}]` carries no ` - YYYY-MM-DD` date")]
    if not _is_iso_date(section.date):
        return [
            Finding("P3", path, f"`## [{version}] - {section.date}` is not a real calendar date")
        ]
    return []


def _base_url(url: str) -> str | None:
    """Return the repository URL a CHANGELOG link is built on.

    Args:
        url: A `tree/` or `compare/` link.

    Returns:
        Everything before the marker, or None when the link is neither shape.
    """
    for marker in (_COMPARE_MARKER, _TREE_MARKER):
        head, found, _ = url.partition(marker)
        if found:
            return head
    return None


def _expected_links(
    changelog: Changelog,
    *,
    base: str,
    names: Sequence[str],
    known_tags: Collection[str],
) -> list[tuple[str, str]]:
    """Build the footer every CHANGELOG of this repository must carry.

    Args:
        changelog: The parsed CHANGELOG.
        base: The repository URL every link is built on.
        names: The plugin's name followed by its predecessors.
        known_tags: The tags that exist.

    Returns:
        Label and URL pairs, newest first, the order the footer is written in.
    """
    released = changelog.released()
    tags = [tag_name(section.label, names=names, known_tags=known_tags) for section in released]
    expected: list[tuple[str, str]] = []
    if changelog.unreleased() is not None and tags:
        expected.append((UNRELEASED_LABEL, f"{base}{_COMPARE_MARKER}{tags[-1]}...HEAD"))
    for index in reversed(range(len(released))):
        tag = tags[index]
        if index == 0:
            expected.append((released[index].label, f"{base}{_TREE_MARKER}{tag}"))
        else:
            url = f"{base}{_COMPARE_MARKER}{tags[index - 1]}...{tag}"
            expected.append((released[index].label, url))
    return expected


def check_links(
    changelog: Changelog,
    *,
    path: str,
    names: Sequence[str],
    known_tags: Collection[str] = (),
) -> list[Finding]:
    """Check C1: the footer uses one link style, in the one order this repository publishes.

    Args:
        changelog: The parsed CHANGELOG.
        path: The repository-relative path of the CHANGELOG, named in the findings.
        names: The plugin's name followed by its predecessors, for a renamed plugin's tags.
        known_tags: The tags that exist; empty means "assume the current name".

    Returns:
        One finding per label whose link is missing, misshapen or built on another base URL.
    """
    bases = {base for _, url in changelog.links if (base := _base_url(url)) is not None}
    unknown = [label for label, url in changelog.links if _base_url(url) is None]
    findings = [
        Finding("C1", path, f"[{label}] is neither a `tree/` nor a `compare/` link")
        for label in unknown
    ]
    if len(bases) > 1:
        joined = ", ".join(sorted(bases))
        findings.append(Finding("C1", path, f"footer links are built on several bases: {joined}"))
    if not bases:
        return findings
    base = min(bases)
    expected = _expected_links(changelog, base=base, names=names, known_tags=known_tags)
    for label, url in expected:
        actual = changelog.link(label)
        if actual is None:
            findings.append(Finding("C1", path, f"the footer defines no link for [{label}]"))
        elif actual != url:
            findings.append(Finding("C1", path, f"[{label}] should link to {url}, not {actual}"))
    defined = {label for label, _ in changelog.links}
    findings.extend(
        Finding("C1", path, f"the footer defines [{label}], which has no section")
        for label in sorted(defined - {label for label, _ in expected})
    )
    return findings


def released_body_at_tag(
    root: Path,
    name: str,
    version: str,
    *,
    tag: str | None = None,
    directory: str | None = None,
) -> str | None:
    """Return the body a released section had when its tag was created.

    Args:
        root: The repository root.
        name: The plugin's current directory name.
        version: The released version to read.
        tag: The tag to read from; `<name>--v<version>` by default.
        directory: The plugin directory at that tag; `name` by default (a rename differs).

    Returns:
        The section body at the tag, or None when the tag, the file or the section is absent.
    """
    reference = tag if tag is not None else f"{name}--v{version}"
    where = directory if directory is not None else name
    text = git_output_or_none(root, ["show", f"{reference}:plugins/{where}/CHANGELOG.md"])
    if text is None:
        return None
    section = parse_changelog(text).find(version)
    return None if section is None else section.body


def check_released_bodies(
    root: Path,
    changelog: Changelog,
    *,
    path: str,
    names: Sequence[str],
    known_tags: Collection[str] = (),
) -> list[Finding]:
    """Check C2: every released section still reads as it did at its own tag.

    A section with no tag yet is skipped: it has not been published, so nothing is frozen.

    Args:
        root: The repository root.
        changelog: The parsed CHANGELOG from the working tree.
        path: The repository-relative path of the CHANGELOG, named in the findings.
        names: The plugin's name followed by its predecessors.
        known_tags: The tags that exist.

    Returns:
        One finding per released section whose body no longer matches its tag.
    """
    findings: list[Finding] = []
    for section in changelog.released():
        tag = tag_name(section.label, names=names, known_tags=known_tags)
        directory = tag.rsplit(f"--v{section.label}", 1)[0]
        at_tag = released_body_at_tag(root, names[0], section.label, tag=tag, directory=directory)
        if at_tag is None:
            continue
        if at_tag != section.body:
            findings.append(
                Finding(
                    "C2",
                    path,
                    (
                        f"the body of `## [{section.label}]` differs from its text at {tag}; "
                        f"corrections go under `## [{UNRELEASED_LABEL}]` in an `{ERRATA_HEADING}` "
                        f"block, and only the footer links may be repaired"
                    ),
                ),
            )
    return findings


def announces_deprecation(body: str) -> bool:
    """Report whether a released section announced a deprecation.

    Args:
        body: The section body.

    Returns:
        True when the body carries a `### Deprecated` block.
    """
    return any(line.strip() == DEPRECATION_HEADING for line in body.splitlines())
