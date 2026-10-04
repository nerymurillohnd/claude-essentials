"""Shared helpers for the claude-essentials repository scripts.

Standard library only: the repository has no dependency manifest by design
(docs/adr/0008-validation-stack.md). Every Claude Code fact used here is
grounded in the official docs listed in CLAUDE.md.
"""

from __future__ import annotations

import datetime as _dt
import json
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

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

# Tag formats. Plugin tags use the official `claude plugin tag` format
# `<name>--v<version>` (docs: plugins/cli-reference#plugin-tag). The
# marketplace uses the same shape under the reserved name `marketplace`.
MARKETPLACE_TAG_NAME = "marketplace"

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
SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
)

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
        MARKETPLACE_TAG_NAME,
    }
)
_BRAND_WORDS = frozenset({"claude", "anthropic", "anthropics"})


def plugin_name_problems(name: str) -> list[str]:
    """Return every reason a plugin name is not acceptable (empty when valid)."""
    problems: list[str] = []
    if not KEBAB_RE.match(name):
        problems.append(
            f'"{name}" is not kebab-case (lowercase letters, digits, single hyphens, starting with a letter)'
        )
    if len(name) > MAX_NAME_LENGTH:
        problems.append(f'"{name}" is longer than {MAX_NAME_LENGTH} characters')
    lowered = name.lower()
    if lowered in _RESERVED_EXACT:
        problems.append(f'"{name}" is a reserved name')
    if lowered.startswith(_RESERVED_PREFIXES):
        problems.append(f'"{name}" starts with a prefix reserved for Anthropic plugins')
    words = set(re.split(r"[-_.]+", lowered))
    if words & _BRAND_WORDS:
        problems.append(
            f'"{name}" contains "claude" or "anthropic" as a word, which reads as an Anthropic plugin'
        )
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
        raise ValueError(f'"{version}" is not a valid SemVer version')
    major, minor, patch = parsed
    if level == "major":
        return f"{major + 1}.0.0"
    if level == "minor":
        return f"{major}.{minor + 1}.0"
    if level == "patch":
        return f"{major}.{minor}.{patch + 1}"
    raise ValueError(f'unknown bump level "{level}"')


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

type JSON = str | int | float | bool | None | list[JSON] | dict[str, JSON]


def load_json(path: Path) -> JSON:
    with path.open(encoding="utf-8") as handle:
        # Verified false positive: typeshed declares json.load() -> Any, but the
        # json module only ever decodes to dict/list/str/int/float/bool/None
        # (https://docs.python.org/3/library/json.html#json-to-py-table),
        # which is exactly the JSON type above.
        data: JSON = json.load(handle)  # pyright: ignore[reportAny]
    return data


def dump_json(path: Path, data: JSON) -> None:
    """Write JSON and format it with Prettier, the repository's formatter."""
    _ = path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    format_files([path])


def format_files(paths: list[Path]) -> None:
    """Format files in place with Prettier so script output matches the format gate."""
    result = run(
        ["prettier", "--write", "--log-level", "warn", *[str(p) for p in paths]],
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit(f"prettier failed: {result.stderr.strip()}")


def as_dict(value: JSON) -> dict[str, JSON] | None:
    return value if isinstance(value, dict) else None


def as_list(value: JSON) -> list[JSON] | None:
    return value if isinstance(value, list) else None


def as_str(value: JSON) -> str | None:
    return value if isinstance(value, str) else None


# --------------------------------------------------------------------------
# Changelog parsing (Keep a Changelog 1.1.0 layout).

_RELEASE_HEADING_RE = re.compile(r"^## \[(?P<version>[^\]]+)\] - (?P<date>\S+)\s*$")
_UNRELEASED_HEADING = "## [Unreleased]"
_SECTION_HEADING_RE = re.compile(r"^### (?P<kind>.+?)\s*$")


@dataclass
class Release:
    version: str
    date: str
    body: str


@dataclass
class Changelog:
    unreleased: str = ""
    releases: list[Release] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)


def parse_changelog(text: str) -> Changelog:
    """Parse a changelog and report structural problems instead of raising."""
    result = Changelog()
    lines = text.splitlines()
    if not lines or lines[0].strip() != "# Changelog":
        result.problems.append('first line must be "# Changelog"')
    current: list[str] | None = None
    unreleased_lines: list[str] = []
    seen_unreleased = False
    release_lines: dict[int, list[str]] = {}
    for line in lines:
        if line.strip() == _UNRELEASED_HEADING:
            if seen_unreleased:
                result.problems.append('more than one "## [Unreleased]" section')
            if result.releases:
                result.problems.append(
                    '"## [Unreleased]" must come before every release'
                )
            seen_unreleased = True
            current = unreleased_lines
            continue
        release = _RELEASE_HEADING_RE.match(line)
        if release:
            result.releases.append(
                Release(release.group("version"), release.group("date"), "")
            )
            current = release_lines.setdefault(len(result.releases) - 1, [])
            continue
        if line.startswith("## "):
            result.problems.append(f'unexpected heading "{line.strip()}"')
            current = None
            continue
        section = _SECTION_HEADING_RE.match(line)
        if section and section.group("kind") not in CHANGE_TYPES:
            result.problems.append(
                f'unknown change type "### {section.group("kind")}" (allowed: {", ".join(CHANGE_TYPES)})'
            )
        if current is not None:
            current.append(line)
    if not seen_unreleased:
        result.problems.append('missing "## [Unreleased]" section')
    result.unreleased = "\n".join(unreleased_lines).strip()
    for index, release_entry in enumerate(result.releases):
        release_entry.body = "\n".join(release_lines.get(index, [])).strip()
        if parse_semver(release_entry.version) is None:
            result.problems.append(
                f'release "{release_entry.version}" is not a valid SemVer version'
            )
        try:
            _ = _dt.date.fromisoformat(release_entry.date)
        except ValueError:
            result.problems.append(
                f'release {release_entry.version} has date "{release_entry.date}", expected YYYY-MM-DD'
            )
        if not release_entry.body:
            result.problems.append(f"release {release_entry.version} has no entries")
    versions = [parse_semver(r.version) for r in result.releases]
    valid = [v for v in versions if v is not None]
    if valid != sorted(valid, reverse=True) or len(set(valid)) != len(valid):
        result.problems.append(
            "releases must be listed newest first, without duplicates"
        )
    return result


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
    if not PLUGINS_DIR.is_dir():
        return []
    return sorted(
        p for p in PLUGINS_DIR.iterdir() if p.is_dir() and not p.name.startswith(".")
    )
