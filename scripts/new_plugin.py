# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Scaffold a new compliant plugin under plugins/<name>/.

Usage:
  uv run scripts/new_plugin.py <name> --category <category> --description "<text>" \
      --author "<name>" [--display-name "<label>"] [--tags a,b] [--with skills agents ...]

It builds on the official generator instead of hand-written files: it runs
`claude plugin init` inside a throwaway HOME and CLAUDE_CONFIG_DIR, so nothing
touches the user's Claude Code configuration, then moves the result into
plugins/<name>/ and adapts it to the marketplace layout (docs/adr/0004-sourcing-policy.md):

  * removes the skills-directory root SKILL.md and its `"skills": ["./"]` entry;
  * removes the `$schema` URL `claude plugin init` writes, which returns HTTP 404;
  * fills plugin.json metadata, README.md and CHANGELOG.md from templates/;
  * adds the marketplace entry, the `plugin:<name>` label and the labeler rules.

The result deliberately keeps TODO placeholders, which `make check` rejects
until the author replaces them with real content.
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

import repo
from repo import JSON

INIT_COMPONENTS = ("skills", "agents", "hooks", "mcp", "lsp", "output-style", "channel")
PRIVILEGED_COMPONENTS = frozenset({"hooks", "mcp", "lsp", "channel"})
LABEL_COLOR = "c5def5"
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


def _min_claude_code() -> str:
    """Minimum Claude Code version for new plugins (repo.MIN_CLAUDE_CODE)."""
    return repo.MIN_CLAUDE_CODE


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
        raise SystemExit(
            f"claude plugin init failed with exit code {result.returncode}"
        )
    output = config / "skills" / name
    if not output.is_dir():
        raise SystemExit(f"claude plugin init did not create {output}")
    return output


def adapt_manifest(
    path: Path,
    name: str,
    display_name: str,
    description: str,
    author: str,
    category: str,
    tags: list[str],
) -> None:
    data = repo.as_dict(repo.load_json(path)) or {}
    manifest: dict[str, JSON] = {
        "name": name,
        "displayName": display_name,
        "version": "0.1.0",
        "description": description,
        "author": {"name": author},
        "homepage": f"{repo.REPOSITORY_URL}/tree/main/plugins/{name}",
        "repository": repo.REPOSITORY_URL,
        "license": "MIT",
        "keywords": [category, *[tag for tag in tags if tag != category]],
        "metadata": {"minClaudeCodeVersion": _min_claude_code()},
    }
    for key, value in data.items():
        if key in ("$schema", "name", "version", "description", "author", "skills"):
            continue
        _ = manifest.setdefault(key, value)
    repo.dump_json(path, manifest)


def render(template: Path, values: dict[str, str]) -> str:
    text = template.read_text(encoding="utf-8")
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", value)
    return text


def add_marketplace_entry(
    name: str, description: str, category: str, tags: list[str]
) -> None:
    data = repo.as_dict(repo.load_json(repo.MARKETPLACE_FILE)) or {}
    plugins = repo.as_list(data.get("plugins")) or []
    entry: dict[str, JSON] = {
        "name": name,
        "source": f"./plugins/{name}",
        "description": description,
        "category": category,
        "tags": list[JSON](tags),
    }
    plugins.append(entry)

    def sort_key(item: JSON) -> str:
        entry_dict = repo.as_dict(item) or {}
        return repo.as_str(entry_dict.get("name")) or ""

    data["plugins"] = sorted(plugins, key=sort_key)
    repo.dump_json(repo.MARKETPLACE_FILE, data)


def add_labels(name: str, display_name: str, category: str) -> None:
    labels = repo.ROOT / ".github" / "labels.yml"
    text = labels.read_text(encoding="utf-8").rstrip("\n")
    text += f'\n- name: "plugin:{name}"\n  color: "{LABEL_COLOR}"\n  description: "{display_name} plugin"\n'
    _ = labels.write_text(text, encoding="utf-8")

    labeler = repo.ROOT / ".github" / "labeler.yml"
    text = labeler.read_text(encoding="utf-8").rstrip("\n") + "\n"
    glob_line = f"          - plugins/{name}/**\n"
    text += f'\n"plugin:{name}":\n  - changed-files:\n      - any-glob-to-any-file:\n{glob_line}'
    category_block = re.search(
        rf'^"category:{re.escape(category)}":\n  - changed-files:\n      - any-glob-to-any-file:\n',
        text,
        re.MULTILINE,
    )
    if category_block:
        insert_at = category_block.end()
        text = text[:insert_at] + glob_line + text[insert_at:]
    else:
        text += f'\n"category:{category}":\n  - changed-files:\n      - any-glob-to-any-file:\n{glob_line}'
    _ = labeler.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    _ = parser.add_argument(
        "name", help="kebab-case plugin name; permanent once published"
    )
    _ = parser.add_argument("--category", required=True, choices=repo.CATEGORIES)
    _ = parser.add_argument(
        "--description", required=True, help="one sentence shown in /plugin"
    )
    _ = parser.add_argument(
        "--author", required=True, help="plugin author shown to users"
    )
    _ = parser.add_argument("--display-name", default="", help="label shown in the UI")
    _ = parser.add_argument(
        "--tags", default="", help="comma-separated kebab-case search tags"
    )
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

    problems = repo.plugin_name_problems(name)
    if problems:
        raise SystemExit("invalid plugin name:\n  " + "\n  ".join(problems))
    target = repo.PLUGINS_DIR / name
    if target.exists():
        raise SystemExit(f"{target} already exists")
    tags = [tag.strip() for tag in tags_arg.split(",") if tag.strip()] or [category]
    bad_tags = [tag for tag in tags if not repo.KEBAB_RE.match(tag)]
    if bad_tags:
        raise SystemExit(f"tags must be kebab-case: {', '.join(bad_tags)}")
    display_name = display_arg or " ".join(
        part.capitalize() for part in name.split("-")
    )

    with tempfile.TemporaryDirectory(prefix="new-plugin-") as tmp:
        generated = run_init(name, description, components, Path(tmp))
        target.parent.mkdir(parents=True, exist_ok=True)
        _ = shutil.copytree(generated, target)

    root_skill = target / "SKILL.md"
    if root_skill.exists():
        root_skill.unlink()
    adapt_manifest(
        target / ".claude-plugin" / "plugin.json",
        name,
        display_name,
        description,
        author,
        category,
        tags,
    )

    privileged = bool(PRIVILEGED_COMPONENTS & set(components))
    manifest = repo.as_dict(repo.load_json(target / ".claude-plugin" / "plugin.json"))
    has_config = bool(manifest and manifest.get("userConfig"))
    optional = (CONFIGURATION_SECTION if has_config else "") + (
        PERMISSIONS_SECTION if privileged else ""
    )
    values = {"display_name": display_name, "optional_sections": optional}
    _ = (target / "README.md").write_text(
        render(repo.ROOT / "templates" / "readme" / "plugin.md", values),
        encoding="utf-8",
    )
    changelog = render(repo.ROOT / "templates" / "changelog" / "CHANGELOG.md", {})
    changelog = changelog.replace(
        "YYYY-MM-DD", dt.datetime.now(dt.UTC).date().isoformat()
    )
    _ = (target / "CHANGELOG.md").write_text(changelog, encoding="utf-8")

    add_marketplace_entry(name, description, category, tags)
    add_labels(name, display_name, category)
    repo.format_files([target])
    synced = repo.run(
        ["uv", "run", str(repo.ROOT / "scripts" / "sync_readmes.py")], check=False
    )
    print(synced.stdout.strip() or synced.stderr.strip())

    validation = repo.run(
        ["claude", "plugin", "validate", str(target), "--strict"], check=False
    )
    print(validation.stdout.strip())
    steps = [
        f"Created plugins/{name}. Next steps:",
        "  1. Replace every TODO (skills, agents, README) with real content.",
        "  2. Run `make check` until it passes.",
        f"  3. Commit with `feat({name}): add {name} plugin` and open a pull request.",
    ]
    print("\n" + "\n".join(steps))
    return 0


if __name__ == "__main__":
    sys.exit(main())
