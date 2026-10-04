"""Shared helpers for the claude-essentials repository scripts.

Standard library only: the repository has no dependency manifest by design
(docs/adr/decisions/ADR_2026-10-03_validation-stack.md). Every Claude
Code fact used here is grounded in the official docs listed in CLAUDE.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import datetime as _dt
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
MARKETPLACE_FILE = ROOT / ".claude-plugin" / "marketplace.json"
PLUGINS_DIR = ROOT / "plugins"
MARKETPLACE_NAME = "claude-essentials"
REPOSITORY_SLUG = "nerymurillohnd/claude-essentials"
REPOSITORY_URL = f"https://github.com/{REPOSITORY_SLUG}"
DISCLAIMER = "not affiliated with or endorsed by Anthropic"

# Category taxonomy (docs/naming.md). Kept in one place; labels, the
# scaffold and the gates read it from here.
CATEGORIES: tuple[str, ...] = (
    "workflows",
    "agents",
    "audits",
    "code-review",
    "documentation",
    "development",
    "best-practices",
    "research",
    "model-behavior",
)

CATEGORY_DESCRIPTIONS: dict[str, str] = {
    "workflows": "Multi-step processes Claude carries out end to end",
    "agents": "Specialized subagents Claude delegates focused work to",
    "audits": "Systematic checks of code, configuration or content",
    "code-review": "Reviewing changes and pull requests",
    "documentation": "Writing and maintaining documentation",
    "development": "Day-to-day software development",
    "best-practices": "Conventions, standards and quality guidance",
    "research": "Deep web and source research",
    "model-behavior": "Output styles, guardrails and operating rules",
}

# Minimum Claude Code version for this repository's tooling and for new
# plugins (changelog review in CLAUDE.md: validator fixes up to 2.1.289).
MIN_CLAUDE_CODE = "2.1.289"

# Mods require Claude Code 2.1.287 or later (docs: plugins/mods/create).
MOD_MIN_CLAUDE_CODE = (2, 1, 287)

# Keep a Changelog 1.1.0 change types plus our mandatory Migration section.
CHANGE_TYPES: tuple[str, ...] = (
    "Added",
    "Changed",
    "Deprecated",
    "Removed",
    "Fixed",
    "Security",
    "Migration",
)

# Regular expression suggested by the SemVer 2.0.0 specification
# (https://semver.org/spec/v2.0.0.html, CC BY 3.0; see THIRD_PARTY_NOTICES.md).
_SEMVER_PATTERN = (
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
    r"(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
)
SEMVER_RE = re.compile(_SEMVER_PATTERN)

KEBAB_RE = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
MAX_NAME_LENGTH = 64

# Names `claude plugin validate` rejects or warns about as passing for
# Anthropic's own plugins (docs: plugins/manifest-reference#name), names
# whose skills no longer load (changelog 2.1.282), and our own reservation.
_RESERVED_PREFIXES = ("claude-", "anthropic-", "anthropics-", "cc-plugin-")
_RESERVED_EXACT = frozenset(
    {
        "claude",
        "anthropic",
        "anthropics",
        "claude-code",
        "claude-mods",
        "anthropic-skills",
        "claude-ai",
    }
)
# Repository areas: commit scopes and branch prefixes for non-plugin work
# (docs/releasing.md), so a plugin of the same name would be ambiguous.
_REPOSITORY_AREAS = frozenset({"marketplace", "scripts", "ci", "docs"})
_BRAND_WORDS = frozenset({"claude", "anthropic", "anthropics"})
_KEBAB_HINT = "lowercase letters, digits, single hyphens, starting with a letter"
_BRAND_HINT = "which reads as an Anthropic plugin"


# --------------------------------------------------------------------------
# Output and errors. The scripts are command-line tools: their report is
# their output, written to standard output.


def emit(text: str = "") -> None:
    """Write one line of command output and flush it immediately."""
    _ = sys.stdout.write(f"{text}\n")
    _ = sys.stdout.flush()


class InvalidVersionError(ValueError):
    """A version string is not valid SemVer."""

    def __init__(self, version: str) -> None:
        """Describe the invalid version."""
        super().__init__(f'"{version}" is not a valid SemVer version')


class UnknownBumpLevelError(ValueError):
    """A bump level is not `major`, `minor` or `patch`."""

    def __init__(self, level: str) -> None:
        """Describe the unknown level."""
        super().__init__(f'unknown bump level "{level}"')


class ToolFailedError(SystemExit):
    """An external tool the scripts depend on exited with an error."""

    def __init__(self, tool: str, detail: str) -> None:
        """Describe which tool failed and why."""
        super().__init__(f"{tool} failed: {detail}")


# --------------------------------------------------------------------------
# Names, versions and tags.


def plugin_name_problems(name: str) -> list[str]:
    """Return every reason a plugin name is not acceptable (empty when valid)."""
    problems: list[str] = []
    if not KEBAB_RE.match(name):
        problems.append(f'"{name}" is not kebab-case ({_KEBAB_HINT})')
    if len(name) > MAX_NAME_LENGTH:
        problems.append(f'"{name}" is longer than {MAX_NAME_LENGTH} characters')
    lowered = name.lower()
    if lowered in _RESERVED_EXACT:
        problems.append(f'"{name}" is a reserved name')
    if lowered in _REPOSITORY_AREAS:
        problems.append(f'"{name}" is a repository area (commit scope and branch prefix)')
    if lowered.startswith(_RESERVED_PREFIXES):
        problems.append(f'"{name}" starts with a prefix reserved for Anthropic plugins')
    words = set(re.split(r"[-_.]+", lowered))
    if words & _BRAND_WORDS:
        problems.append(f'"{name}" contains "claude" or "anthropic" as a word, {_BRAND_HINT}')
    return problems


def parse_semver(version: str) -> tuple[int, int, int] | None:
    """Return (major, minor, patch) for a valid SemVer string, else None."""
    match = SEMVER_RE.match(version)
    if match is None:
        return None
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def bump(version: str, level: str) -> str:
    """Bump a release version by `major`, `minor` or `patch`."""
    parsed = parse_semver(version)
    if parsed is None:
        raise InvalidVersionError(version)
    major, minor, patch = parsed
    if level == "major":
        return f"{major + 1}.0.0"
    if level == "minor":
        return f"{major}.{minor + 1}.0"
    if level == "patch":
        return f"{major}.{minor}.{patch + 1}"
    raise UnknownBumpLevelError(level)


def bump_level(old: str, new: str) -> str | None:
    """The level that turns `old` into `new` by one bump, or None if no single bump does."""
    for level in ("major", "minor", "patch"):
        if bump(old, level) == new:
            return level
    return None


def plugin_tag(name: str, version: str) -> str:
    """Tag name for a release, in the official `<name>--v<version>` format."""
    return f"{name}--v{version}"


TAG_RE = re.compile(r"^(?P<name>[a-z][a-z0-9-]*)--v(?P<version>\S+)$")


def split_tag(tag: str) -> tuple[str, str] | None:
    """Split `<name>--v<version>` into its parts, or return None."""
    match = TAG_RE.match(tag)
    if match is None or parse_semver(match.group("version")) is None:
        return None
    return match.group("name"), match.group("version")


# --------------------------------------------------------------------------
# JSON helpers. `JSON` is the recursive type of a decoded document, so an
# `isinstance` check narrows to a known type instead of `Unknown`.

type JSON = str | int | float | bool | list[JSON] | dict[str, JSON] | None


def load_json(path: Path) -> JSON:
    """Decode a JSON file into the `JSON` type."""
    with path.open(encoding="utf-8") as handle:
        # Verified false positive: typeshed declares json.load() -> Any, but the
        # json module only ever decodes to dict/list/str/int/float/bool/None
        # (https://docs.python.org/3/library/json.html#json-to-py-table),
        # which is exactly the JSON type above.
        data: JSON = json.load(handle)  # pyright: ignore[reportAny]
    return data


def dump_json(path: Path, data: JSON) -> None:
    """Write JSON and format it with Prettier, the repository's formatter."""
    _ = path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    format_files([path])


def format_files(paths: list[Path]) -> None:
    """Format files in place with Prettier so script output matches the format gate."""
    result = run(
        ["prettier", "--write", "--log-level", "warn", *[str(p) for p in paths]],
        check=False,
    )
    if result.returncode != 0:
        tool = "prettier"
        raise ToolFailedError(tool, result.stderr.strip())


def as_dict(value: JSON) -> dict[str, JSON] | None:
    """Return the value when it is a JSON object, else None."""
    return value if isinstance(value, dict) else None


def as_list(value: JSON) -> list[JSON] | None:
    """Return the value when it is a JSON array, else None."""
    return value if isinstance(value, list) else None


def as_str(value: JSON) -> str | None:
    """Return the value when it is a JSON string, else None."""
    return value if isinstance(value, str) else None


# --------------------------------------------------------------------------
# Changelog parsing (Keep a Changelog 1.1.0 layout).

_RELEASE_HEADING_RE = re.compile(r"^## \[(?P<version>[^\]]+)\] - (?P<date>\S+)\s*$")
_UNRELEASED_HEADING = "## [Unreleased]"
_SECTION_HEADING_RE = re.compile(r"^### (?P<kind>.+?)\s*$")


@dataclass
class Release:
    """One released version of a changelog."""

    version: str
    date: str
    body: str


@dataclass
class Changelog:
    """A parsed changelog and the structural problems found in it."""

    unreleased: str = ""
    releases: list[Release] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)


@dataclass
class _ChangelogScan:
    """Line-by-line state while parsing a changelog."""

    result: Changelog
    unreleased_lines: list[str] = field(default_factory=list)
    release_lines: list[list[str]] = field(default_factory=list)
    current: list[str] | None = None
    seen_unreleased: bool = False

    def feed(self, line: str) -> None:
        """Route one line to the section it belongs to."""
        if line.strip() == _UNRELEASED_HEADING:
            self._start_unreleased()
            return
        release = _RELEASE_HEADING_RE.match(line)
        if release:
            self.result.releases.append(
                Release(release.group("version"), release.group("date"), "")
            )
            self.current = []
            self.release_lines.append(self.current)
            return
        if line.startswith("## "):
            self.result.problems.append(f'unexpected heading "{line.strip()}"')
            self.current = None
            return
        section = _SECTION_HEADING_RE.match(line)
        if section and section.group("kind") not in CHANGE_TYPES:
            kind = section.group("kind")
            allowed = ", ".join(CHANGE_TYPES)
            self.result.problems.append(f'unknown change type "### {kind}" (allowed: {allowed})')
        if self.current is not None:
            self.current.append(line)

    def _start_unreleased(self) -> None:
        if self.seen_unreleased:
            self.result.problems.append('more than one "## [Unreleased]" section')
        if self.result.releases:
            self.result.problems.append('"## [Unreleased]" must come before every release')
        self.seen_unreleased = True
        self.current = self.unreleased_lines


def _release_problems(release: Release) -> list[str]:
    problems: list[str] = []
    if parse_semver(release.version) is None:
        problems.append(f'release "{release.version}" is not a valid SemVer version')
    try:
        _ = _dt.date.fromisoformat(release.date)
    except ValueError:
        problems.append(f'release {release.version} has date "{release.date}", expected YYYY-MM-DD')
    if not release.body:
        problems.append(f"release {release.version} has no entries")
    return problems


def parse_changelog(text: str) -> Changelog:
    """Parse a changelog and report structural problems instead of raising."""
    scan = _ChangelogScan(Changelog())
    result = scan.result
    lines = text.splitlines()
    if not lines or lines[0].strip() != "# Changelog":
        result.problems.append('first line must be "# Changelog"')
    for line in lines:
        scan.feed(line)
    if not scan.seen_unreleased:
        result.problems.append('missing "## [Unreleased]" section')
    result.unreleased = "\n".join(scan.unreleased_lines).strip()
    for release, body in zip(result.releases, scan.release_lines, strict=True):
        release.body = "\n".join(body).strip()
        result.problems.extend(_release_problems(release))
    versions = [parse_semver(r.version) for r in result.releases]
    valid = [v for v in versions if v is not None]
    if valid != sorted(valid, reverse=True) or len(set(valid)) != len(valid):
        result.problems.append("releases must be listed newest first, without duplicates")
    return result


# The catalog changelog has no versions: the marketplace is not versioned, so
# its sections are dated `## YYYY-MM-DD` (UTC), newest first.
_DATE_HEADING_RE = re.compile(r"^## (?P<date>\d{4}-\d{2}-\d{2})\s*$")


@dataclass
class DatedChangelog:
    """A parsed catalog changelog: dated sections and the problems found in it."""

    sections: list[Release] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)


def _dated_line_problem(line: str) -> str | None:
    if line.startswith("## "):
        return f'unexpected heading "{line.strip()}", expected "## YYYY-MM-DD"'
    section = _SECTION_HEADING_RE.match(line)
    if section and section.group("kind") not in CHANGE_TYPES:
        allowed = ", ".join(CHANGE_TYPES)
        return f'unknown change type "### {section.group("kind")}" (allowed: {allowed})'
    return None


def _dated_section_problems(entry: Release) -> list[str]:
    problems: list[str] = []
    try:
        _ = _dt.date.fromisoformat(entry.date)
    except ValueError:
        problems.append(f'"## {entry.date}" is not a valid date')
    if not entry.body:
        problems.append(f"## {entry.date} has no entries")
    return problems


def parse_dated_changelog(text: str) -> DatedChangelog:
    """Parse the catalog changelog, whose sections are `## YYYY-MM-DD`."""
    result = DatedChangelog()
    lines = text.splitlines()
    if not lines or lines[0].strip() != "# Changelog":
        result.problems.append('first line must be "# Changelog"')
    bodies: list[list[str]] = []
    for line in lines:
        heading = _DATE_HEADING_RE.match(line)
        if heading:
            result.sections.append(Release("", heading.group("date"), ""))
            bodies.append([])
            continue
        problem = _dated_line_problem(line)
        if problem:
            result.problems.append(problem)
        elif bodies:
            bodies[-1].append(line)
    for entry, body in zip(result.sections, bodies, strict=True):
        entry.body = "\n".join(body).strip()
        result.problems.extend(_dated_section_problems(entry))
    dates = [entry.date for entry in result.sections]
    if dates != sorted(dates, reverse=True) or len(set(dates)) != len(dates):
        result.problems.append("dated sections must be listed newest first, without duplicates")
    return result


def add_dated_note(text: str, date: str, kind: str, note: str) -> str:
    """Add `- note` under `### kind` in the `## date` section, creating either if missing."""
    lines = text.rstrip("\n").splitlines()
    heading = f"## {date}"
    if heading not in lines:
        first = next((i for i, line in enumerate(lines) if line.startswith("## ")), len(lines))
        lines[first:first] = [heading, "", f"### {kind}", "", f"- {note}", ""]
    else:
        start = lines.index(heading)
        end = next(
            (i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines)
        )
        kind_heading = f"### {kind}"
        if kind_heading in lines[start:end]:
            items = lines.index(kind_heading, start, end) + 2
            while items < end and lines[items].startswith("- "):
                items += 1
            lines.insert(items, f"- {note}")
        else:
            while lines[end - 1].strip() == "":
                end -= 1
            lines[end:end] = ["", kind_heading, "", f"- {note}"]
    return "\n".join(lines).rstrip("\n") + "\n"


def has_section_content(body: str, kind: str) -> bool:
    """True when `### <kind>` exists in `body` and has at least one non-empty line."""
    lines = body.splitlines()
    inside = False
    for line in lines:
        heading = _SECTION_HEADING_RE.match(line)
        if heading:
            inside = heading.group("kind") == kind
            continue
        if inside and line.strip():
            return True
    return False


# --------------------------------------------------------------------------
# Git and process helpers.


def run(
    args: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    check: bool = True,
    input_text: str | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run a command with captured text output; raise on failure when `check`."""
    return subprocess.run(
        args,
        cwd=cwd or ROOT,
        env=env,
        check=check,
        capture_output=True,
        text=True,
        input=input_text,
    )


def git_show(ref: str, path: str) -> str | None:
    """File content at `ref`, or None when it does not exist there."""
    result = run(["git", "show", f"{ref}:{path}"], check=False)
    return result.stdout if result.returncode == 0 else None


def plugin_dirs() -> list[Path]:
    """Every plugin directory under plugins/, sorted by name."""
    if not PLUGINS_DIR.is_dir():
        return []
    return sorted(p for p in PLUGINS_DIR.iterdir() if p.is_dir() and not p.name.startswith("."))
