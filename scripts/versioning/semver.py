"""Canonical SemVer for plugin versions: parsing, ordering and the bump level (M5).

The repository accepts exactly `X.Y.Z` and `X.Y.Z-beta.N` / `X.Y.Z-rc.N`. A `v` prefix,
a two-part version, build metadata (`+…`) and any other prerelease tag are rejected, because
the official CLI accepts shapes Claude Code then orders differently from semver.org. Ordering
follows semver.org: a prerelease sorts below its release, and `beta` sorts below `rc`, with the
prerelease number compared as an integer rather than as text.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Final, Literal, override

from scripts.common.errors import MaintainerError

BumpLevel = Literal["major", "minor", "patch", "prerelease", "none", "invalid"]
"""How far a version moved, or why it could not move that way."""

PRERELEASE_TAGS: Final = ("beta", "rc")
"""The only prerelease identifiers this marketplace publishes, in ascending order."""

VERSION_PATTERN: Final = re.compile(
    (
        r"^(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)"
        r"(?:-(?P<tag>beta|rc)\.(?P<number>0|[1-9]\d*))?\Z"
    ),
)
"""The whole grammar, anchored with `\\Z` rather than `$`.

`$` also matches before a trailing newline, which would make `"1.0.0\\n"` a valid version.
"""


class InvalidVersionError(MaintainerError):
    """A version string is not canonical SemVer as this marketplace defines it."""

    def __init__(self, text: str) -> None:
        """Record the rejected text and restate the grammar.

        Args:
            text: The version string that could not be parsed.
        """
        super().__init__(
            (
                f"{text!r} is not a canonical version: expected X.Y.Z, X.Y.Z-beta.N or "
                f"X.Y.Z-rc.N, with no `v` prefix and no build metadata"
            ),
        )


@dataclass(frozen=True, slots=True)
class Version:
    """One canonical plugin version.

    Attributes:
        major: The first component.
        minor: The second component.
        patch: The third component.
        prerelease: The prerelease identifier and its number, or None for a release.
    """

    major: int
    minor: int
    patch: int
    prerelease: tuple[str, int] | None = None

    @override
    def __str__(self) -> str:
        """Render the version the way a manifest and a tag spell it.

        Returns:
            The canonical text, which `parse` reads back unchanged.
        """
        core = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease is None:
            return core
        tag, number = self.prerelease
        return f"{core}-{tag}.{number}"

    def sort_key(self) -> tuple[int, int, int, int, int, int]:
        """Return the tuple that puts versions in semver.org order.

        The fourth element is 1 for a release and 0 for a prerelease, which is what makes
        `1.0.0-rc.1` sort below `1.0.0`. The last two are meaningless for a release and are
        held at zero so the tuples stay comparable.

        Returns:
            A tuple ordered exactly like the versions it stands for.
        """
        if self.prerelease is None:
            return (self.major, self.minor, self.patch, 1, 0, 0)
        tag, number = self.prerelease
        return (self.major, self.minor, self.patch, 0, PRERELEASE_TAGS.index(tag), number)

    def __lt__(self, other: Version) -> bool:
        """Report whether this version precedes another.

        Args:
            other: The version to compare against.

        Returns:
            True when this version is older.
        """
        return self.sort_key() < other.sort_key()

    def __le__(self, other: Version) -> bool:
        """Report whether this version precedes another or equals it.

        Args:
            other: The version to compare against.

        Returns:
            True when this version is not newer.
        """
        return self.sort_key() <= other.sort_key()

    def __gt__(self, other: Version) -> bool:
        """Report whether this version follows another.

        Args:
            other: The version to compare against.

        Returns:
            True when this version is newer.
        """
        return self.sort_key() > other.sort_key()

    def __ge__(self, other: Version) -> bool:
        """Report whether this version follows another or equals it.

        Args:
            other: The version to compare against.

        Returns:
            True when this version is not older.
        """
        return self.sort_key() >= other.sort_key()


def parse(text: str) -> Version:
    """Parse a canonical version string.

    Args:
        text: The version as a manifest or a tag spells it.

    Returns:
        The parsed version.

    Raises:
        InvalidVersionError: If the text is not canonical SemVer for this marketplace.
    """
    matched = VERSION_PATTERN.match(text)
    if matched is None:
        raise InvalidVersionError(text)
    tag = matched.group("tag")
    number = matched.group("number")
    prerelease = None if tag is None else (tag, int(number))
    return Version(
        major=int(matched.group("major")),
        minor=int(matched.group("minor")),
        patch=int(matched.group("patch")),
        prerelease=prerelease,
    )


def is_valid(text: str) -> bool:
    """Report whether a string is a canonical version, without raising.

    Args:
        text: The candidate version.

    Returns:
        True when `parse` would succeed.
    """
    return VERSION_PATTERN.match(text) is not None


def bump_level(old: Version, new: Version) -> BumpLevel:
    """Classify the move from one version to another.

    A decrease is `invalid`: ADR-0003 never lowers a published version, because a lower
    number would re-serve an older cache key to users who already hold the higher one. A move
    confined to the prerelease line (including the promotion of `1.0.0-rc.1` to `1.0.0`) is
    `prerelease`, since the release line itself did not move.

    Args:
        old: The version currently published, normally the latest tag.
        new: The version in the manifest.

    Returns:
        The level of the move.
    """
    if new == old:
        return "none"
    if new < old:
        return "invalid"
    if new.major != old.major:
        return "major"
    if new.minor != old.minor:
        return "minor"
    if new.patch != old.patch:
        return "patch"
    return "prerelease"
