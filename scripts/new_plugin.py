#!/usr/bin/env python3
"""Scaffold a new compliant plugin under plugins/<name>/.

Usage:
  python3 scripts/new_plugin.py <name> --category <category> --description "<text>" \
      --author "<name>" [--display-name "<label>"] [--tags a,b] [--with skills agents ...]

It builds on the official generator instead of hand-written files: it runs
`claude plugin init` inside a throwaway HOME and CLAUDE_CONFIG_DIR, so nothing
touches the user's Claude Code configuration, then moves the result into
plugins/<name>/ and adapts it to the marketplace layout
(docs/adr/decisions/ADR_2026-10-03_sourcing-policy.md):

  * removes the skills-directory root SKILL.md and its `"skills": ["./"]` entry;
  * removes the `$schema` URL `claude plugin init` writes, which returns HTTP 404;
  * fills plugin.json metadata, README.md and CHANGELOG.md from templates/;
  * adds the marketplace entry, the `plugin:<name>` label and the labeler rules;
  * adds a dated note to the catalog CHANGELOG.md (the catalog has no version).

The result deliberately keeps TODO placeholders, which `python3 scripts/check.py` rejects
until the author replaces them with real content.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import datetime as dt
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
from typing import TYPE_CHECKING

import repo

if TYPE_CHECKING:
    from repo import JSON

INIT_COMPONENTS = ("skills", "agents", "hooks", "mcp", "lsp", "output-style", "channel")
PRIVILEGED_COMPONENTS = frozenset({"hooks", "mcp", "lsp", "channel"})
LABEL_COLOR = "c5def5"
CHANGED_FILES_RULE = "  - changed-files:\n      - any-glob-to-any-file:\n"
CONFIGURATION_SECTION = """## Configuration

<!-- BEGIN GENERATED: configuration -->
<!-- END GENERATED: configuration -->

"""
PERMISSIONS_SECTION = """## Permissions

TODO: explain why the plugin needs each item in the table below and what it does with the
installing user's files, network and accounts. See docs/security-review.md.

<!-- BEGIN GENERATED: runtime -->
<!-- END GENERATED: runtime -->

"""


class ScaffoldError(SystemExit):
    """The scaffold cannot continue; the message says why."""


class InitFailedError(ScaffoldError):
    """`claude plugin init` exited with an error."""

    def __init__(self, code: int) -> None:
        """Report the exit code."""
        super().__init__(f"claude plugin init failed with exit code {code}")


class InitOutputMissingError(ScaffoldError):
    """`claude plugin init` did not create the expected directory."""

    def __init__(self, path: Path) -> None:
        """Name the missing directory."""
        super().__init__(f"claude plugin init did not create {path}")


class InvalidPluginNameError(ScaffoldError):
    """The plugin name breaks the naming rules."""

    def __init__(self, problems: list[str]) -> None:
        """List every naming problem."""
        super().__init__("invalid plugin name:\n  " + "\n  ".join(problems))


class PluginExistsError(ScaffoldError):
    """A plugin directory with this name already exists."""

    def __init__(self, path: Path) -> None:
        """Name the existing directory."""
        super().__init__(f"{path} already exists")


class InvalidTagsError(ScaffoldError):
    """Some tags are not kebab-case."""

    def __init__(self, tags: list[str]) -> None:
        """List the invalid tags."""
        super().__init__(f"tags must be kebab-case: {', '.join(tags)}")


class ScaffoldLeftoverError(ScaffoldError):
    """The temporary scaffold directory survived its context manager."""

    def __init__(self, path: str) -> None:
        """Name the leftover directory."""
        super().__init__(f"temporary scaffold directory {path} was not removed")


@dataclass(frozen=True)
class PluginSpec:
    """Everything the scaffold needs to know about the new plugin."""

    name: str
    display_name: str
    description: str
    author: str
    category: str
    tags: list[str]
    components: list[str]

    @property
    def target(self) -> Path:
        """The plugin directory in the repository."""
        return repo.PLUGINS_DIR / self.name


def run_init(name: str, description: str, components: list[str], workdir: Path) -> Path:
    """Run the official scaffold in an isolated config and return its output directory."""
    home = workdir / "home"
    config = home / ".claude"
    config.mkdir(parents=True)
    env = dict(os.environ)
    env["HOME"] = str(home)
    env["CLAUDE_CONFIG_DIR"] = str(config)
    args = ["claude", "plugin", "init", name, "--description", description]
    if components:
        args += ["--with", *components]
    result = repo.run(args, env=env, cwd=workdir, check=False)
    _ = sys.stdout.write(result.stdout)
    if result.returncode != 0:
        _ = sys.stderr.write(result.stderr)
        raise InitFailedError(result.returncode)
    output = config / "skills" / name
    if not output.is_dir():
        raise InitOutputMissingError(output)
    return output


def adapt_manifest(path: Path, spec: PluginSpec) -> None:
    """Rewrite the generated plugin.json with the marketplace metadata."""
    data = repo.as_dict(repo.load_json(path)) or {}
    manifest: dict[str, JSON] = {
        "name": spec.name,
        "displayName": spec.display_name,
        "version": "0.1.0",
        "description": spec.description,
        "author": {"name": spec.author},
        "homepage": f"{repo.REPOSITORY_URL}/tree/main/plugins/{spec.name}",
        "repository": repo.REPOSITORY_URL,
        "license": "MIT",
        "keywords": [spec.category, *[tag for tag in spec.tags if tag != spec.category]],
        "metadata": {"minClaudeCodeVersion": repo.MIN_CLAUDE_CODE},
    }
    for key, value in data.items():
        if key in ("$schema", "name", "version", "description", "author", "skills"):
            continue
        _ = manifest.setdefault(key, value)
    repo.dump_json(path, manifest)


def render(template: Path, values: dict[str, str]) -> str:
    """Fill `{{key}}` placeholders in a template file."""
    text = template.read_text(encoding="utf-8")
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", value)
    return text


def add_marketplace_entry(spec: PluginSpec) -> None:
    """Add the plugin to marketplace.json, keeping entries sorted by name."""
    data = repo.as_dict(repo.load_json(repo.MARKETPLACE_FILE)) or {}
    plugins = repo.as_list(data.get("plugins")) or []
    tags: list[JSON] = [*spec.tags]
    entry: dict[str, JSON] = {
        "name": spec.name,
        "source": f"./plugins/{spec.name}",
        "description": spec.description,
        "category": spec.category,
        "tags": tags,
    }
    plugins.append(entry)

    def sort_key(item: JSON) -> str:
        entry_dict = repo.as_dict(item) or {}
        return repo.as_str(entry_dict.get("name")) or ""

    data["plugins"] = sorted(plugins, key=sort_key)
    repo.dump_json(repo.MARKETPLACE_FILE, data)


def add_labels(spec: PluginSpec) -> None:
    """Add the `plugin:<name>` label and the labeler rules for the plugin and its category."""
    labels = repo.ROOT / ".github" / "labels.yml"
    label_entry = (
        f'- name: "plugin:{spec.name}"\n'
        f'  color: "{LABEL_COLOR}"\n'
        f'  description: "{spec.display_name} plugin"\n'
    )
    text = labels.read_text(encoding="utf-8").rstrip("\n")
    _ = labels.write_text(f"{text}\n{label_entry}", encoding="utf-8")

    labeler = repo.ROOT / ".github" / "labeler.yml"
    text = labeler.read_text(encoding="utf-8").rstrip("\n") + "\n"
    glob_line = f"          - plugins/{spec.name}/**\n"
    text += f'\n"plugin:{spec.name}":\n{CHANGED_FILES_RULE}{glob_line}'
    category_heading = f'"category:{spec.category}":\n{CHANGED_FILES_RULE}'
    category_block = re.search(f"^{re.escape(category_heading)}", text, re.MULTILINE)
    if category_block:
        insert_at = category_block.end()
        text = text[:insert_at] + glob_line + text[insert_at:]
    else:
        text += f"\n{category_heading}{glob_line}"
    _ = labeler.write_text(text, encoding="utf-8")


def _parse_args() -> PluginSpec:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    _ = parser.add_argument("name", help="kebab-case plugin name; permanent once published")
    _ = parser.add_argument("--category", required=True, choices=repo.CATEGORIES)
    _ = parser.add_argument("--description", required=True, help="one sentence shown in /plugin")
    _ = parser.add_argument("--author", required=True, help="plugin author shown to users")
    _ = parser.add_argument("--display-name", default="", help="label shown in the UI")
    _ = parser.add_argument("--tags", default="", help="comma-separated kebab-case search tags")
    _ = parser.add_argument(
        "--with",
        dest="components",
        nargs="*",
        default=["skills"],
        choices=INIT_COMPONENTS,
    )
    args = parser.parse_args()
    name: str = args.name  # pyright: ignore[reportAny]  # argparse Namespace attributes are Any
    category: str = args.category  # pyright: ignore[reportAny]  # argparse Namespace attributes are Any
    description: str = args.description  # pyright: ignore[reportAny]  # argparse Namespace attributes are Any
    author: str = args.author  # pyright: ignore[reportAny]  # argparse Namespace attributes are Any
    display_arg: str = args.display_name  # pyright: ignore[reportAny]  # argparse Namespace attributes are Any
    tags_arg: str = args.tags  # pyright: ignore[reportAny]  # argparse Namespace attributes are Any
    components: list[str] = args.components  # pyright: ignore[reportAny]  # argparse Namespace attributes are Any
    tags = [tag.strip() for tag in tags_arg.split(",") if tag.strip()] or [category]
    display_name = display_arg or " ".join(part.capitalize() for part in name.split("-"))
    return PluginSpec(name, display_name, description, author, category, tags, components)


def _check_spec(spec: PluginSpec) -> None:
    problems = repo.plugin_name_problems(spec.name)
    if problems:
        raise InvalidPluginNameError(problems)
    if spec.target.exists():
        raise PluginExistsError(spec.target)
    bad_tags = [tag for tag in spec.tags if not repo.KEBAB_RE.match(tag)]
    if bad_tags:
        raise InvalidTagsError(bad_tags)


def _scaffold(spec: PluginSpec) -> None:
    with tempfile.TemporaryDirectory(prefix="new-plugin-") as tmp:
        generated = run_init(spec.name, spec.description, spec.components, Path(tmp))
        spec.target.parent.mkdir(parents=True, exist_ok=True)
        _ = shutil.copytree(generated, spec.target)
    if Path(tmp).exists():
        raise ScaffoldLeftoverError(tmp)
    root_skill = spec.target / "SKILL.md"
    if root_skill.exists():
        root_skill.unlink()
    adapt_manifest(spec.target / ".claude-plugin" / "plugin.json", spec)


def _write_docs(spec: PluginSpec) -> None:
    privileged = bool(PRIVILEGED_COMPONENTS & set(spec.components))
    manifest = repo.as_dict(repo.load_json(spec.target / ".claude-plugin" / "plugin.json"))
    has_config = bool(manifest and manifest.get("userConfig"))
    optional = (CONFIGURATION_SECTION if has_config else "") + (
        PERMISSIONS_SECTION if privileged else ""
    )
    values = {"display_name": spec.display_name, "optional_sections": optional}
    _ = (spec.target / "README.md").write_text(
        render(repo.ROOT / "templates" / "readme" / "plugin.md", values),
        encoding="utf-8",
    )
    changelog = render(repo.ROOT / "templates" / "changelog" / "CHANGELOG.md", {})
    changelog = changelog.replace("YYYY-MM-DD", dt.datetime.now(dt.UTC).date().isoformat())
    _ = (spec.target / "CHANGELOG.md").write_text(changelog, encoding="utf-8")
    # The plugin is copied alone into the user's cache, so the MIT notice travels with it.
    year = str(dt.datetime.now(dt.UTC).year)
    license_text = render(
        repo.ROOT / "templates" / "license" / "LICENSE",
        {"YEAR": year, "COPYRIGHT_HOLDER": spec.author},
    )
    _ = (spec.target / "LICENSE").write_text(license_text, encoding="utf-8")


def add_catalog_note(spec: PluginSpec) -> None:
    """Record the new plugin under today's date in the catalog changelog."""
    path = repo.ROOT / "CHANGELOG.md"
    today = dt.datetime.now(dt.UTC).date().isoformat()
    note = f"`{spec.name}`: {spec.description}"
    text = repo.add_dated_note(path.read_text(encoding="utf-8"), today, "Added", note)
    _ = path.write_text(text, encoding="utf-8")


def _finish(spec: PluginSpec) -> None:
    repo.format_files([spec.target])
    synced = repo.run([sys.executable, str(repo.ROOT / "scripts" / "sync_readmes.py")], check=False)
    repo.emit(synced.stdout.strip() or synced.stderr.strip())
    validation = repo.run(
        ["claude", "plugin", "validate", str(spec.target), "--strict"], check=False
    )
    repo.emit(validation.stdout.strip())
    steps = [
        f"Created plugins/{spec.name}. Next steps:",
        "  1. Replace every TODO (skills, agents, README) with real content.",
        "  2. Run `python3 scripts/check.py` until it passes.",
        f"  3. Commit with `feat({spec.name}): add {spec.name} plugin` and open a pull request.",
    ]
    repo.emit("\n" + "\n".join(steps))


def main() -> int:
    """Scaffold the plugin and register it in the catalog, labels and READMEs."""
    spec = _parse_args()
    _check_spec(spec)
    _scaffold(spec)
    _write_docs(spec)
    add_marketplace_entry(spec)
    add_catalog_note(spec)
    add_labels(spec)
    _finish(spec)
    return 0


if __name__ == "__main__":
    sys.exit(main())
