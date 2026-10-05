#!/usr/bin/env python3
"""Repository gates that `claude plugin validate` does not cover.

Run: python3 scripts/check_repo.py [--root PATH]

Exit 0 when every gate passes, 1 when any gate fails. Each failure names the
file and the rule, so the fix is obvious. Rules and their reasons are in
docs/quality-bar.md and docs/adr/.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
import fnmatch
import os
from pathlib import Path
import re
import socket
import sys
from typing import TYPE_CHECKING

import repo

if TYPE_CHECKING:
    from repo import JSON

TEXT_SUFFIXES = frozenset(
    {
        ".md",
        ".json",
        ".yml",
        ".yaml",
        ".toml",
        ".txt",
        ".py",
        ".sh",
        ".js",
        ".mjs",
        ".cjs",
        ".ts",
        ".mts",
        ".cts",
        ".tsx",
        ".jsx",
        "",
    }
)

# Machine-specific path shapes (portability gate,
# docs/adr/decisions/ADR_2026-10-03_security-posture.md).
_ABSOLUTE_PATH_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("macOS home path", re.compile(r"/Users/[^/\s]+")),
    ("Linux home path", re.compile(r"/home/[^/\s]+")),
    ("Windows home path", re.compile(r"[A-Za-z]:\\+Users\\+", re.IGNORECASE)),
    ("home-relative path", re.compile(r"(?<![\w$}])~/")),
    ("macOS temporary path", re.compile(r"/(?:private/)?var/folders/|/private/tmp/")),
    ("root user path", re.compile(r"/root/")),
)

_SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "GitHub token",
        re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})"),
    ),
    ("Anthropic API key", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{10,}")),
    ("OpenAI-style API key", re.compile(r"\bsk-[A-Za-z0-9]{32,}")),
    ("AWS access key", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("Slack token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}")),
    ("private key", re.compile(r"-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----")),
)

_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@([A-Za-z0-9.-]+\.[A-Za-z]{2,})\b")
_ALLOWED_EMAIL_DOMAINS = (
    "example.com",
    "example.org",
    "example.net",
    "users.noreply.github.com",
)
_PARENT_ESCAPE_RE = re.compile(r"(?:^|[\s\"'`(=:,\[])\.\./")
# Placeholders left by the scaffold, `claude plugin init` or the templates.
_PLACEHOLDER_RE = re.compile(r"\bTODO\b|YYYY-MM-DD|\{\{[^}]+\}\}|<your-[^>]*>")
_PATH_TOKEN_RE = re.compile(r"(?<![\w}$])\.{0,2}/[\w./-]+")
# Paths built on Claude Code's plugin variables, quoted or not, are portable
# (docs: plugins/manifest-reference#environment-variables).
_ALLOWED_PATH_RE = re.compile(r'"?\$\{CLAUDE_(?:PLUGIN_ROOT|PLUGIN_DATA|PROJECT_DIR)\}"?[\w./-]*')
_URL_RE = re.compile(r"[a-z][a-z0-9+.-]*://\S+", re.IGNORECASE)
_PLUGIN_VARIABLES = "${CLAUDE_PLUGIN_ROOT} or ${CLAUDE_PLUGIN_DATA}"
_PORTABLE_ALTERNATIVE = "use ${CLAUDE_PLUGIN_ROOT} or a documented setting"
_EMAIL_ALTERNATIVE = 'use plugin.json "author.email" or an example.com address'
# User and host names shorter than this match too many ordinary words.
_MIN_MARKER_LENGTH = 4

_README_HEADINGS = tuple(
    repo.readme_heading(title)
    for _, title in repo.README_SECTIONS
    if title not in repo.CONDITIONAL_README_SECTIONS
)
_PERMISSIONS_HEADING = repo.readme_heading("Permissions")
_FAQ_HEADING = repo.readme_heading("FAQ")
_PRIVILEGED_WHAT = "plugins with hooks, MCP or LSP servers, bin/, monitors or mods"
_REQUIRED_MANIFEST_KEYS = (
    "name",
    "version",
    "description",
    "author",
    "license",
    "repository",
)
_PRIVILEGED_PATHS = ("hooks", ".mcp.json", ".lsp.json", "bin", "monitors")
_COMPONENT_KEYS = (
    "skills",
    "commands",
    "agents",
    "hooks",
    "mcpServers",
    "lspServers",
    "outputStyles",
    "workflows",
)


@dataclass
class Report:
    """Collected gate failures, each prefixed with the file it concerns."""

    errors: list[str] = field(default_factory=list)

    def fail(self, where: Path | str, message: str) -> None:
        """Record one failure."""
        self.errors.append(f"{where}: {message}")


def _rel(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _iter_text_files(base: Path) -> list[Path]:
    return [
        path
        for path in sorted(base.rglob("*"))
        if not path.is_symlink()
        and path.is_file()
        and ".mcpb-cache" not in path.parts
        and path.name != ".DS_Store"
        and path.suffix.lower() in TEXT_SUFFIXES
    ]


# --------------------------------------------------------------------------
# Marketplace


def _check_catalog_fields(data: dict[str, JSON], where: str, report: Report) -> None:
    if data.get("name") != repo.MARKETPLACE_NAME:
        report.fail(where, f'"name" must be "{repo.MARKETPLACE_NAME}"')
    description = repo.as_str(data.get("description")) or ""
    if repo.DISCLAIMER not in description:
        report.fail(where, f'"description" must state the project is "{repo.DISCLAIMER}"')
    metadata = repo.as_dict(data.get("metadata")) or {}
    if "version" in data or "version" in metadata:
        report.fail(where, 'the catalog has no "version"; only plugins are versioned')
    owner = repo.as_dict(data.get("owner"))
    if owner is None or not repo.as_str(owner.get("name")):
        report.fail(where, '"owner.name" is required')


def _check_entry_tags(entry: dict[str, JSON], label: str, report: Report) -> None:
    tags = repo.as_list(entry.get("tags"))
    if not tags:
        report.fail(label, '"tags" must be a non-empty array')
        return
    for tag in tags:
        tag_text = repo.as_str(tag)
        if tag_text is None or not repo.KEBAB_RE.match(tag_text):
            report.fail(label, f"tag {tag!r} must be a kebab-case string")


def _check_entry(name: str, entry: dict[str, JSON], label: str, report: Report) -> None:
    for problem in repo.plugin_name_problems(name):
        report.fail(label, problem)
    if entry.get("source") != f"./plugins/{name}":
        reason = "in-repo plugins only, ADR in-repo-plugins-only"
        report.fail(label, f'"source" must be "./plugins/{name}" ({reason})')
    if "version" in entry:
        report.fail(label, '"version" belongs only in plugin.json (ADR per-plugin-versioning)')
    if not repo.as_str(entry.get("description")):
        report.fail(label, '"description" is required')
    category = repo.as_str(entry.get("category"))
    if category not in repo.CATEGORIES:
        report.fail(label, f'"category" must be one of: {", ".join(repo.CATEGORIES)}')
    _check_entry_tags(entry, label, report)


def check_marketplace(root: Path, report: Report) -> dict[str, dict[str, JSON]]:
    """Validate marketplace.json and return its entries keyed by plugin name."""
    path = root / ".claude-plugin" / "marketplace.json"
    where = _rel(root, path)
    if not path.is_file():
        report.fail(where, "missing marketplace manifest")
        return {}
    data = repo.as_dict(repo.load_json(path))
    if data is None:
        report.fail(where, "must be a JSON object")
        return {}
    _check_catalog_fields(data, where, report)
    entries: dict[str, dict[str, JSON]] = {}
    plugins = repo.as_list(data.get("plugins"))
    if plugins is None:
        report.fail(where, '"plugins" must be an array')
        return entries
    for index, raw in enumerate(plugins):
        entry = repo.as_dict(raw)
        label = f"{where} plugins[{index}]"
        if entry is None:
            report.fail(label, "entry must be an object")
            continue
        name = repo.as_str(entry.get("name")) or ""
        if name in entries:
            report.fail(label, f'duplicate plugin name "{name}"')
        entries[name] = entry
        _check_entry(name, entry, label, report)
    names = list(entries)
    if names != sorted(names):
        report.fail(where, "plugin entries must be sorted by name")
    return entries


# --------------------------------------------------------------------------
# Plugins


def _manifest_component_paths(manifest: dict[str, JSON]) -> list[str]:
    paths: list[str] = []
    for key in _COMPONENT_KEYS:
        value = manifest.get(key)
        candidates: list[JSON] = []
        if isinstance(value, str):
            candidates = [value]
        elif isinstance(value, list):
            candidates = value
        paths.extend(
            candidate
            for candidate in candidates
            if isinstance(candidate, str) and not candidate.startswith("https://")
        )
    return paths


def _hook_files(plugin: Path, manifest: dict[str, JSON]) -> list[Path]:
    files = [
        plugin / "hooks" / "hooks.json",
        *(plugin / path for path in _manifest_component_paths({"hooks": manifest.get("hooks")})),
    ]
    return [f for f in files if f.is_file()]


def is_mod(plugin: Path, manifest: dict[str, JSON]) -> bool:
    """True when a hooks file declares `modules` (docs: plugins/mods/reference#files)."""
    for hook_file in _hook_files(plugin, manifest):
        data = repo.as_dict(repo.load_json(hook_file))
        if data is not None and "modules" in data:
            return True
    hooks = repo.as_dict(manifest.get("hooks"))
    return hooks is not None and "modules" in hooks


def _command_strings(value: JSON, key: str | None = None) -> list[str]:
    """Collect `command` and `args` strings from a hooks or MCP structure."""
    found: list[str] = []
    if isinstance(value, dict):
        for child_key, child in value.items():
            found.extend(_command_strings(child, child_key))
    elif isinstance(value, list):
        for child in value:
            if key == "args" and isinstance(child, str):
                found.append(child)
            else:
                found.extend(_command_strings(child, key))
    elif isinstance(value, str) and key == "command":
        found.append(value)
    return found


def _check_manifest_identity(
    name: str, manifest: dict[str, JSON], mwhere: str, report: Report
) -> None:
    for key in _REQUIRED_MANIFEST_KEYS:
        if key not in manifest:
            report.fail(mwhere, f'"{key}" is required')
    if manifest.get("name") != name:
        report.fail(mwhere, f'"name" must match the directory name "{name}"')
    if "$schema" in manifest:
        report.fail(
            mwhere,
            '"$schema" must be omitted: the published schema URL returns 404 (CLAUDE.md)',
        )
    version = repo.as_str(manifest.get("version")) or ""
    if repo.parse_semver(version) is None:
        report.fail(mwhere, f'"version" "{version}" is not a valid SemVer version')


def _check_manifest_ownership(manifest: dict[str, JSON], mwhere: str, report: Report) -> None:
    if manifest.get("license") != "MIT":
        report.fail(mwhere, '"license" must be "MIT" (repository license)')
    if manifest.get("repository") != repo.REPOSITORY_URL:
        report.fail(mwhere, f'"repository" must be "{repo.REPOSITORY_URL}"')
    author = repo.as_dict(manifest.get("author"))
    if author is None or not repo.as_str(author.get("name")):
        report.fail(mwhere, '"author.name" is required')


@dataclass(frozen=True)
class _PluginPlace:
    """A plugin directory and how failures name it and its manifest."""

    path: Path
    where: str
    mwhere: str


def _check_layout(
    place: _PluginPlace, manifest: dict[str, JSON], entry: dict[str, JSON] | None, report: Report
) -> None:
    plugin, where, mwhere = place.path, place.where, place.mwhere
    if entry is not None:
        category = repo.as_str(entry.get("category"))
        keywords = repo.as_list(manifest.get("keywords")) or []
        if category and category not in keywords:
            report.fail(mwhere, f'"keywords" must include the category "{category}"')
    for component in _manifest_component_paths(manifest):
        if component not in (".", "./") and not component.startswith("./"):
            report.fail(mwhere, f'component path "{component}" must start with "./"')
        resolved = (plugin / component).resolve()
        if not resolved.is_relative_to(plugin.resolve()):
            report.fail(mwhere, f'component path "{component}" escapes the plugin directory')
    if (plugin / "CLAUDE.md").exists():
        report.fail(
            where, "CLAUDE.md at a plugin root is never loaded; put instructions in a skill"
        )
    if (plugin / "SKILL.md").exists():
        report.fail(
            where,
            "root SKILL.md is the skills-directory layout; use skills/<name>/SKILL.md",
        )


def _is_privileged(plugin: Path, manifest: dict[str, JSON], *, mod: bool) -> bool:
    return (
        mod
        or any((plugin / p).exists() for p in _PRIVILEGED_PATHS)
        or any(key in manifest for key in ("hooks", "mcpServers", "lspServers"))
    )


def check_plugin(root: Path, plugin: Path, entry: dict[str, JSON] | None, report: Report) -> None:
    """Run every plugin-level gate on one plugin directory."""
    name = plugin.name
    where = _rel(root, plugin)
    if entry is None:
        report.fail(where, "plugin directory is not listed in marketplace.json")
    for problem in repo.plugin_name_problems(name):
        report.fail(where, problem)

    manifest_path = plugin / ".claude-plugin" / "plugin.json"
    if not manifest_path.is_file():
        report.fail(where, "missing .claude-plugin/plugin.json")
        return
    manifest = repo.as_dict(repo.load_json(manifest_path))
    mwhere = _rel(root, manifest_path)
    if manifest is None:
        report.fail(mwhere, "must be a JSON object")
        return
    _check_manifest_identity(name, manifest, mwhere, report)
    _check_manifest_ownership(manifest, mwhere, report)
    _check_layout(_PluginPlace(plugin, where, mwhere), manifest, entry, report)

    mod = is_mod(plugin, manifest)
    check_readme(root, plugin, report, privileged=_is_privileged(plugin, manifest, mod=mod))
    version = repo.as_str(manifest.get("version")) or ""
    check_plugin_changelog(root, plugin, version, report)
    check_plugin_license(root, plugin, report)
    if mod:
        check_mod(root, plugin, manifest, report)
    check_metadata(root, manifest_path, manifest, report)
    check_self_containment(root, plugin, manifest, report)
    check_portability(root, plugin, manifest, report)


def check_plugin_license(root: Path, plugin: Path, report: Report) -> None:
    """The plugin ships the MIT text of templates/license/LICENSE with a year and holder."""
    path = plugin / "LICENSE"
    where = _rel(root, path)
    if not path.is_file():
        report.fail(where, "missing plugin LICENSE (the plugin is copied without the repository)")
        return
    template = (root / "templates" / "license" / "LICENSE").read_text(encoding="utf-8")
    pattern = (
        re.escape(template)
        .replace(re.escape("{{YEAR}}"), r"\d{4}")
        .replace(re.escape("{{COPYRIGHT_HOLDER}}"), r"[^\s{][^\n{]*")
    )
    if not re.fullmatch(pattern, path.read_text(encoding="utf-8")):
        report.fail(where, "must be templates/license/LICENSE with the year and holder filled in")


def check_metadata(
    root: Path, manifest_path: Path, manifest: dict[str, JSON], report: Report
) -> None:
    """`metadata.minClaudeCodeVersion`, when present, is x.y.z."""
    metadata = repo.as_dict(manifest.get("metadata"))
    if metadata is None:
        return
    minimum = repo.as_str(metadata.get("minClaudeCodeVersion"))
    if minimum is not None and repo.parse_semver(minimum) is None:
        report.fail(_rel(root, manifest_path), '"metadata.minClaudeCodeVersion" must be x.y.z')


def check_mod(root: Path, plugin: Path, manifest: dict[str, JSON], report: Report) -> None:
    """Mods declare the minimum Claude Code version for mods and ship tests."""
    where = _rel(root, plugin)
    metadata = repo.as_dict(manifest.get("metadata")) or {}
    minimum = repo.parse_semver(repo.as_str(metadata.get("minClaudeCodeVersion")) or "")
    if minimum is None or minimum < repo.MOD_MIN_CLAUDE_CODE:
        required = ".".join(str(part) for part in repo.MOD_MIN_CLAUDE_CODE)
        report.fail(
            where,
            f'mods require "metadata.minClaudeCodeVersion" >= {required} in plugin.json',
        )
    tests = [p for p in plugin.rglob("*") if p.name.endswith((".test.ts", ".test.tsx"))]
    if not tests:
        report.fail(where, "mods must ship tests that `claude plugin test` runs (*.test.ts)")


def check_readme(root: Path, plugin: Path, report: Report, *, privileged: bool) -> None:
    """The plugin README has every required section and the install identifier."""
    readme = plugin / "README.md"
    where = _rel(root, readme)
    if not readme.is_file():
        report.fail(where, "missing plugin README.md")
        return
    text = readme.read_text(encoding="utf-8")
    for heading in _README_HEADINGS:
        if not re.search(rf"^{re.escape(heading)}\s*$", text, re.MULTILINE):
            report.fail(where, f'missing "{heading}" section')
    permissions = re.search(rf"^{re.escape(_PERMISSIONS_HEADING)}\s*$", text, re.MULTILINE)
    if privileged and not permissions:
        report.fail(where, f'"{_PERMISSIONS_HEADING}" section is required for {_PRIVILEGED_WHAT}')
    if f"@{repo.MARKETPLACE_NAME}" not in text:
        report.fail(
            where,
            f'installation instructions must use "<plugin>@{repo.MARKETPLACE_NAME}"',
        )
    _check_faq(text, where, report)


def _check_faq(text: str, where: str, report: Report) -> None:
    """The FAQ holds 3 to 5 questions and opens with the fixed one."""
    start = re.search(rf"^{re.escape(_FAQ_HEADING)}\s*$", text, re.MULTILINE)
    if start is None:
        return
    rest = text[start.end() :]
    following = re.search(r"^## ", rest, re.MULTILINE)
    section = rest[: following.start()] if following else rest
    questions = [
        str(found.group(1)).strip()
        for found in re.finditer(r"<summary>(.*?)</summary>", section, re.DOTALL)
    ]
    low, high = repo.FAQ_MIN_QUESTIONS, repo.FAQ_MAX_QUESTIONS
    if not low <= len(questions) <= high:
        found = len(questions)
        report.fail(where, f'"{_FAQ_HEADING}" needs {low} to {high} questions, found {found}')
    if questions and questions[0] != repo.FAQ_FIRST_QUESTION:
        report.fail(where, f'"{_FAQ_HEADING}" must open with "{repo.FAQ_FIRST_QUESTION}"')


def check_plugin_changelog(root: Path, plugin: Path, version: str, report: Report) -> None:
    """The plugin changelog is well formed and agrees with plugin.json."""
    path = plugin / "CHANGELOG.md"
    where = _rel(root, path)
    if not path.is_file():
        report.fail(where, "missing plugin CHANGELOG.md")
        return
    changelog = repo.parse_changelog(path.read_text(encoding="utf-8"))
    for problem in changelog.problems:
        report.fail(where, problem)
    if not changelog.releases:
        report.fail(where, "at least one released version is required")
    elif changelog.releases[0].version != version:
        report.fail(
            where,
            f'latest release is {changelog.releases[0].version} but plugin.json says "{version}"',
        )
    for index, release in enumerate(changelog.releases[:-1]):
        newer = repo.parse_semver(release.version)
        older = repo.parse_semver(changelog.releases[index + 1].version)
        is_major = bool(newer and older and newer[0] > older[0] and older[0] >= 1)
        if is_major and not repo.has_section_content(release.body, "Migration"):
            report.fail(
                where,
                f'major release {release.version} needs a non-empty "### Migration" section',
            )


def _check_symlinks(root: Path, plugin: Path, report: Report) -> None:
    plugin_root = plugin.resolve()
    for path in sorted(plugin.rglob("*")):
        if path.is_symlink() and not path.resolve().is_relative_to(plugin_root):
            report.fail(_rel(root, path), "symlink points outside the plugin directory")


def _check_parent_escapes(root: Path, plugin: Path, report: Report) -> None:
    for path in _iter_text_files(plugin):
        text = path.read_text(encoding="utf-8", errors="replace")
        for number, line in enumerate(text.splitlines(), start=1):
            if _PARENT_ESCAPE_RE.search(line):
                report.fail(
                    f"{_rel(root, path)}:{number}",
                    '"../" reference: plugins are copied alone to a cache',
                )


def _command_structures(plugin: Path, manifest: dict[str, JSON]) -> list[JSON]:
    structures: list[JSON] = [repo.load_json(f) for f in _hook_files(plugin, manifest)]
    mcp_file = plugin / ".mcp.json"
    if mcp_file.is_file():
        structures.append(repo.load_json(mcp_file))
    structures.append(manifest.get("hooks"))
    structures.append(manifest.get("mcpServers"))
    return structures


def _relative_command_paths(command: str) -> list[str]:
    cleaned = _ALLOWED_PATH_RE.sub("", _URL_RE.sub("", command))
    return [
        match.group(0)
        for match in _PATH_TOKEN_RE.finditer(cleaned)
        if match.group(0).startswith(("./", "../", "/"))
    ]


def check_self_containment(
    root: Path, plugin: Path, manifest: dict[str, JSON], report: Report
) -> None:
    """Nothing in the plugin reaches outside its directory."""
    _check_symlinks(root, plugin, report)
    _check_parent_escapes(root, plugin, report)
    for structure in _command_structures(plugin, manifest):
        for command in _command_strings(structure):
            for token in _relative_command_paths(command):
                report.fail(
                    _rel(root, plugin),
                    f'command path "{token}" in "{command}" must start with {_PLUGIN_VARIABLES}',
                )


def _machine_markers() -> list[tuple[str, str]]:
    """Strings that identify the machine running the gate (skipped in CI)."""
    if os.environ.get("CI"):
        return []
    markers: list[tuple[str, str]] = []
    home = str(Path.home())
    if len(home) > 1:
        markers.append(("home directory", home))
    user = os.environ.get("USER") or os.environ.get("USERNAME") or ""
    if len(user) >= _MIN_MARKER_LENGTH:
        markers.append(("user name", user))
    host = socket.gethostname().split(".")[0]
    if len(host) >= _MIN_MARKER_LENGTH:
        markers.append(("host name", host))
    return markers


def _email_problems(line: str, allowed_emails: set[str]) -> list[str]:
    problems: list[str] = []
    for match in _EMAIL_RE.finditer(line):
        email, domain = match.group(0), match.group(1).lower()
        if email not in allowed_emails and not domain.endswith(_ALLOWED_EMAIL_DOMAINS):
            problems.append(f'personal email "{email}"; {_EMAIL_ALTERNATIVE}')
    return problems


def _line_problems(
    line: str, allowed_emails: set[str], markers: list[tuple[str, str]]
) -> list[str]:
    problems = [
        f"{label} is machine-specific; {_PORTABLE_ALTERNATIVE}"
        for label, pattern in _ABSOLUTE_PATH_PATTERNS
        if pattern.search(line)
    ]
    problems.extend(
        f"possible {label}; secrets never belong in a plugin"
        for label, pattern in _SECRET_PATTERNS
        if pattern.search(line)
    )
    problems.extend(_email_problems(line, allowed_emails))
    # The canonical repository slug names the GitHub owner on purpose.
    scrubbed = line.replace(repo.REPOSITORY_SLUG, "")
    problems.extend(
        f"contains this machine's {label}"
        for label, marker in markers
        if re.search(rf"(?<![\w]){re.escape(marker)}(?![\w])", scrubbed, re.IGNORECASE)
    )
    if _PLACEHOLDER_RE.search(line):
        problems.append("unfinished placeholder (TODO or YYYY-MM-DD)")
    return problems


def check_portability(root: Path, plugin: Path, manifest: dict[str, JSON], report: Report) -> None:
    """No machine-specific paths, secrets, personal emails or placeholders in the plugin."""
    author = repo.as_dict(manifest.get("author")) or {}
    allowed_emails = {repo.as_str(author.get("email")) or ""}
    markers = _machine_markers()
    for path in _iter_text_files(plugin):
        text = path.read_text(encoding="utf-8", errors="replace")
        for number, line in enumerate(text.splitlines(), start=1):
            location = f"{_rel(root, path)}:{number}"
            for problem in _line_problems(line, allowed_emails, markers):
                report.fail(location, problem)


# --------------------------------------------------------------------------
# Repository-level consistency


def _yaml_tag_patterns(workflow: Path) -> list[str]:
    """Read `on.push.tags` patterns from a workflow without a YAML parser."""
    patterns: list[str] = []
    inside = False
    indent = -1
    for line in workflow.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped == "tags:":
            inside, indent = True, len(line) - len(line.lstrip())
            continue
        if inside:
            if stripped.startswith("#"):
                continue
            current = len(line) - len(line.lstrip())
            if stripped.startswith("- ") and current > indent:
                patterns.append(stripped[2:].strip().strip("'\""))
                continue
            if stripped:
                inside = False
    return patterns


# Local hooks pinned in .pre-commit-config.yaml and the CI pin in scripts/check.py
# that each must match: hook repository → pin constant.
_HOOK_PINS = {
    "https://github.com/astral-sh/ruff-pre-commit": ("RUFF_VERSION", "v"),
    "https://github.com/DetachHead/basedpyright-prek-mirror": ("BASEDPYRIGHT_VERSION", ""),
}


def check_hook_pins(root: Path, report: Report) -> None:
    """The local pre-commit hooks run the same tool versions as CI."""
    config = root / ".pre-commit-config.yaml"
    where = _rel(root, config)
    if not config.is_file():
        report.fail(where, "missing local hook configuration")
        return
    pattern = re.compile(r"^\s*- repo: (\S+)\n\s*rev: (\S+)$", re.MULTILINE)
    hooks = {
        str(match.group(1)): str(match.group(2))
        for match in pattern.finditer(config.read_text(encoding="utf-8"))
    }
    pins = (root / "scripts" / "check.py").read_text(encoding="utf-8")
    for url, (constant, prefix) in _HOOK_PINS.items():
        pin = re.search(rf'^{constant} = "([^"]+)"$', pins, re.MULTILINE)
        expected = f"{prefix}{pin.group(1)}" if pin else None
        if hooks.get(url) != expected:
            found = hooks.get(url, "missing")
            report.fail(where, f"{url} rev {found} must be {expected} ({constant} in check.py)")


def check_release_workflow(root: Path, entries: dict[str, dict[str, JSON]], report: Report) -> None:
    """The release workflow fires on every official tag and nothing else."""
    workflow = root / ".github" / "workflows" / "release.yml"
    where = _rel(root, workflow)
    if not workflow.is_file():
        report.fail(where, "missing release workflow")
        return
    patterns = _yaml_tag_patterns(workflow)
    if not patterns:
        report.fail(where, "no on.push.tags patterns found")
        return
    samples = [repo.plugin_tag(name, "1.2.3") for name in entries]
    for sample in samples:
        if not any(fnmatch.fnmatchcase(sample, pattern) for pattern in patterns):
            report.fail(
                where,
                f'tag "{sample}" (claude plugin tag format) matches no on.push.tags pattern',
            )
    for negative in ("v1.2.3", "name-v1.2.3"):
        if any(fnmatch.fnmatchcase(negative, pattern) for pattern in patterns):
            report.fail(
                where,
                f'tag "{negative}" matches an on.push.tags pattern but must not trigger a release',
            )


def check_labels(root: Path, entries: dict[str, dict[str, JSON]], report: Report) -> None:
    """Every required label exists and the labeler covers every plugin and category."""
    labels_file = root / ".github" / "labels.yml"
    labeler_file = root / ".github" / "labeler.yml"
    if not labels_file.is_file() or not labeler_file.is_file():
        report.fail(".github", "labels.yml and labeler.yml are required")
        return
    labels_text = labels_file.read_text(encoding="utf-8")
    defined = set(re.findall(r'^- name: "([^"]+)"', labels_text, re.MULTILINE))
    required = {f"category:{c}" for c in repo.CATEGORIES}
    required |= {f"plugin:{name}" for name in entries}
    required |= {f"semver:{level}" for level in ("major", "minor", "patch")}
    required |= {"status:needs-triage", "security-review"}
    # Labels that issue forms and the labeler apply must exist, or GitHub drops them.
    for form in sorted((root / ".github" / "ISSUE_TEMPLATE").glob("*.yml")):
        listed = re.search(r"^labels: \[(.*)\]$", form.read_text(encoding="utf-8"), re.MULTILINE)
        if listed:
            required |= set(re.findall(r'"([^"]+)"', listed.group(1)))
    labeler_keys = re.findall(
        r'^"([^"]+)":$', labeler_file.read_text(encoding="utf-8"), re.MULTILINE
    )
    required |= set(labeler_keys)
    for label in sorted(required - defined):
        report.fail(_rel(root, labels_file), f'label "{label}" is not defined')
    labeler_text = labeler_file.read_text(encoding="utf-8")
    for name, entry in entries.items():
        block = re.search(
            rf'^"plugin:{re.escape(name)}":\n(?:  .*\n)+',
            labeler_text + "\n",
            re.MULTILINE,
        )
        if block is None or f"plugins/{name}/**" not in block.group(0):
            report.fail(
                _rel(root, labeler_file),
                f'"plugin:{name}" must label changes to plugins/{name}/**',
            )
        category = repo.as_str(entry.get("category"))
        cblock = re.search(
            rf'^"category:{re.escape(category or "")}":\n(?:  .*\n)+',
            labeler_text + "\n",
            re.MULTILINE,
        )
        if category and (cblock is None or f"plugins/{name}/**" not in cblock.group(0)):
            report.fail(
                _rel(root, labeler_file),
                f'"category:{category}" must label changes to plugins/{name}/**',
            )


def check_root_changelog(root: Path, report: Report) -> None:
    """The catalog changelog is well formed, with dated sections newest first."""
    path = root / "CHANGELOG.md"
    where = _rel(root, path)
    if not path.is_file():
        report.fail(where, "missing catalog CHANGELOG.md")
        return
    for problem in repo.parse_dated_changelog(path.read_text(encoding="utf-8")).problems:
        report.fail(where, problem)


def run_checks(root: Path) -> Report:
    """Run every repository gate on the repository at `root`."""
    report = Report()
    entries = check_marketplace(root, report)
    plugins_dir = root / "plugins"
    seen: set[str] = set()
    if plugins_dir.is_dir():
        for plugin in sorted(p for p in plugins_dir.iterdir() if p.is_dir()):
            seen.add(plugin.name)
            check_plugin(root, plugin, entries.get(plugin.name), report)
    for name in sorted(set(entries) - seen):
        report.fail(
            ".claude-plugin/marketplace.json",
            f'plugin "{name}" has no directory plugins/{name}',
        )
    check_release_workflow(root, entries, report)
    check_labels(root, entries, report)
    check_root_changelog(root, report)
    check_hook_pins(root, report)
    return report


def main() -> int:
    """Run the gates and report every failure."""
    parser = argparse.ArgumentParser(description=__doc__)
    _ = parser.add_argument("--root", type=Path, default=repo.ROOT, help="repository root to check")
    args = parser.parse_args()
    root_arg: Path = args.root  # pyright: ignore[reportAny]  # argparse Namespace attributes are Any
    report = run_checks(root_arg.resolve())
    for error in report.errors:
        repo.emit(f"✘ {error}")
    if report.errors:
        repo.emit(f"\ncheck_repo: {len(report.errors)} problem(s) found")
        return 1
    repo.emit("check_repo: all repository gates passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
