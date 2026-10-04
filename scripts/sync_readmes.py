# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Generate the README content that must never drift from the plugins.

Usage:
  uv run scripts/sync_readmes.py          # rewrite generated content
  uv run scripts/sync_readmes.py --check  # fail when anything is stale (make check)

* README.md (root) is rendered entirely from templates/readme/root.md plus the
  catalog in .claude-plugin/marketplace.json. Edit the template, never README.md.
* Each plugin README keeps the author's prose and holds generated blocks between
  `<!-- BEGIN GENERATED: <block> -->` and `<!-- END GENERATED: <block> -->`:
  header, requirements, installation, components, uninstall, and, when they apply,
  configuration (userConfig options) and runtime (what the plugin runs).

Generated Markdown is passed through Prettier so `prettier --check` and this
gate always agree (docs/readme-guide.md).
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

import repo
from repo import JSON

TEMPLATES = repo.ROOT / "templates" / "readme"
BEGIN = "<!-- BEGIN GENERATED: {} -->"
END = "<!-- END GENERATED: {} -->"
ALWAYS_BLOCKS = ("header", "requirements", "installation", "components", "uninstall")
INSTALL_SOURCE = repo.REPOSITORY_SLUG
# Plugins are copied alone into the user's cache, so links out of a plugin
# directory are absolute GitHub URLs, never "../" paths.
BLOB = f"{repo.REPOSITORY_URL}/blob/main"


# --------------------------------------------------------------------------
# Small Markdown helpers


def badge(label: str, message: str, color: str, link: str | None = None) -> str:
    def escape(text: str) -> str:
        return quote(text.replace("-", "--").replace("_", "__"), safe="")

    image = f"![{label}: {message}](https://img.shields.io/badge/{escape(label)}-{escape(message)}-{color})"
    return f"[{image}]({link})" if link else image


def ci_badge() -> str:
    """GitHub's native workflow status badge for the validation workflow."""
    workflow = f"{repo.REPOSITORY_URL}/actions/workflows/validate.yml"
    return f"[![CI]({workflow}/badge.svg)]({workflow})"


def cell(text: str) -> str:
    return " ".join(text.split()).replace("|", "\\|")


def table(header: list[str], rows: list[list[str]]) -> str:
    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join("---" for _ in header) + " |",
    ]
    lines += ["| " + " | ".join(cell(value) for value in row) + " |" for row in rows]
    return "\n".join(lines)


def frontmatter(path: Path) -> dict[str, str]:
    """Read simple `key: value` frontmatter, joining indented continuation lines."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---", 4)
    if end == -1:
        return {}
    fields: dict[str, str] = {}
    key: str | None = None
    for line in text[4:end].splitlines():
        match = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if match:
            key = str(match.group(1))
            fields[key] = match.group(2).strip().strip("'\"")
        elif key and line.startswith((" ", "\t")):
            fields[key] = f"{fields[key]} {line.strip()}".strip()
    return fields


def prettier(text: str, filename: str) -> str:
    result = repo.run(
        ["prettier", "--stdin-filepath", filename], check=False, input_text=text
    )
    if result.returncode != 0:
        raise SystemExit(f"prettier failed on {filename}: {result.stderr.strip()}")
    return result.stdout


# --------------------------------------------------------------------------
# Plugin inventory


@dataclass
class Plugin:
    path: Path
    name: str
    manifest: dict[str, JSON]
    entry: dict[str, JSON]

    @property
    def display_name(self) -> str:
        return repo.as_str(self.manifest.get("displayName")) or self.name

    @property
    def version(self) -> str:
        return repo.as_str(self.manifest.get("version")) or "0.0.0"

    @property
    def category(self) -> str:
        return repo.as_str(self.entry.get("category")) or ""

    @property
    def min_claude_code(self) -> str:
        metadata = repo.as_dict(self.manifest.get("metadata")) or {}
        return repo.as_str(metadata.get("minClaudeCodeVersion")) or repo.MIN_CLAUDE_CODE


def load_plugins() -> list[Plugin]:
    data = repo.as_dict(repo.load_json(repo.MARKETPLACE_FILE)) or {}
    plugins: list[Plugin] = []
    for raw in repo.as_list(data.get("plugins")) or []:
        entry = repo.as_dict(raw) or {}
        name = repo.as_str(entry.get("name")) or ""
        path = repo.PLUGINS_DIR / name
        manifest_path = path / ".claude-plugin" / "plugin.json"
        if not manifest_path.is_file():
            continue
        manifest = repo.as_dict(repo.load_json(manifest_path)) or {}
        plugins.append(Plugin(path, name, manifest, entry))
    return plugins


def _json_file(path: Path) -> dict[str, JSON]:
    return (repo.as_dict(repo.load_json(path)) or {}) if path.is_file() else {}


def hooks_config(plugin: Plugin) -> dict[str, JSON]:
    return _json_file(plugin.path / "hooks" / "hooks.json")


def mcp_servers(plugin: Plugin) -> dict[str, JSON]:
    servers = dict(
        repo.as_dict(_json_file(plugin.path / ".mcp.json").get("mcpServers")) or {}
    )
    inline = repo.as_dict(plugin.manifest.get("mcpServers"))
    if inline:
        servers.update(inline)
    return servers


def lsp_servers(plugin: Plugin) -> dict[str, JSON]:
    servers = dict(_json_file(plugin.path / ".lsp.json"))
    inline = repo.as_dict(plugin.manifest.get("lspServers"))
    if inline:
        servers.update(inline)
    return servers


def bin_files(plugin: Plugin) -> list[str]:
    folder = plugin.path / "bin"
    return (
        sorted(p.name for p in folder.iterdir() if p.is_file())
        if folder.is_dir()
        else []
    )


def is_privileged(plugin: Plugin) -> bool:
    hooks = hooks_config(plugin)
    return bool(
        hooks
        or plugin.manifest.get("hooks")
        or mcp_servers(plugin)
        or lsp_servers(plugin)
        or bin_files(plugin)
        or (plugin.path / "monitors").exists()
    )


def components(plugin: Plugin) -> list[list[str]]:
    rows: list[list[str]] = []
    for skill in sorted((plugin.path / "skills").glob("*/SKILL.md")):
        fields = frontmatter(skill)
        name = fields.get("name") or skill.parent.name
        rows.append(
            ["Skill", f"`/{plugin.name}:{name}`", fields.get("description", "")]
        )
    for agent in sorted((plugin.path / "agents").rglob("*.md")):
        fields = frontmatter(agent)
        name = fields.get("name") or agent.stem
        rows.append(["Agent", f"`{plugin.name}:{name}`", fields.get("description", "")])
    for command in sorted((plugin.path / "commands").glob("*.md")):
        fields = frontmatter(command)
        rows.append(
            [
                "Command",
                f"`/{plugin.name}:{command.stem}`",
                fields.get("description", ""),
            ]
        )
    for style in sorted((plugin.path / "output-styles").glob("*.md")):
        fields = frontmatter(style)
        name = fields.get("name") or style.stem
        rows.append(["Output style", f"`{name}`", fields.get("description", "")])
    hooks = repo.as_dict(hooks_config(plugin).get("hooks")) or {}
    for event in sorted(hooks):
        rows.append(
            ["Hook", f"`{event}`", "Runs automatically on this event; see Permissions"]
        )
    if "modules" in hooks_config(plugin):
        rows.append(["Mod", "hooks module", "Runs inside Claude Code; see Permissions"])
    for server in sorted(mcp_servers(plugin)):
        rows.append(
            [
                "MCP server",
                f"`{server}`",
                f"Tools appear as `mcp__plugin_{plugin.name}_{server}__*`",
            ]
        )
    for server in sorted(lsp_servers(plugin)):
        rows.append(
            ["LSP server", f"`{server}`", "Code intelligence for the mapped file types"]
        )
    for executable in bin_files(plugin):
        rows.append(
            [
                "Executable",
                f"`{executable}`",
                "On the Bash tool's PATH while the plugin is enabled",
            ]
        )
    return rows


def component_badges(plugin: Plugin) -> list[str]:
    """One badge per component type the plugin ships, with its count."""
    counts: dict[str, int] = {}
    for row in components(plugin):
        counts[row[0]] = counts.get(row[0], 0) + 1
    return [
        badge(
            kind.lower() + ("" if kind.endswith("s") else "s"),
            str(count),
            "blueviolet",
            "#components",
        )
        for kind, count in counts.items()
    ]


def runtime_rows(plugin: Plugin) -> list[list[str]]:
    rows: list[list[str]] = []
    hooks = repo.as_dict(hooks_config(plugin).get("hooks")) or {}
    for event in sorted(hooks):
        for matcher_raw in repo.as_list(hooks[event]) or []:
            matcher = repo.as_dict(matcher_raw) or {}
            for handler_raw in repo.as_list(matcher.get("hooks")) or []:
                handler = repo.as_dict(handler_raw) or {}
                command = (
                    repo.as_str(handler.get("command"))
                    or repo.as_str(handler.get("url"))
                    or ""
                )
                scope = repo.as_str(matcher.get("matcher")) or "all"
                rows.append([f"Hook `{event}` ({scope})", f"`{command}`"])
    if "modules" in hooks_config(plugin):
        modules = repo.as_list(hooks_config(plugin).get("modules")) or []
        rows.append(["Mod", ", ".join(f"`{repo.as_str(m) or ''}`" for m in modules)])
    for name, raw in sorted(mcp_servers(plugin).items()):
        server = repo.as_dict(raw) or {}
        target = repo.as_str(server.get("url")) or " ".join(
            [
                repo.as_str(server.get("command")) or "",
                *[repo.as_str(a) or "" for a in repo.as_list(server.get("args")) or []],
            ]
        )
        rows.append(
            [
                f"MCP server `{name}` ({repo.as_str(server.get('type')) or 'stdio'})",
                f"`{target.strip()}`",
            ]
        )
    for name, raw in sorted(lsp_servers(plugin).items()):
        server = repo.as_dict(raw) or {}
        rows.append(
            [f"LSP server `{name}`", f"`{repo.as_str(server.get('command')) or ''}`"]
        )
    for executable in bin_files(plugin):
        rows.append([f"Executable `{executable}`", "`bin/" + executable + "`"])
    return rows


def config_rows(plugin: Plugin) -> list[list[str]]:
    options = repo.as_dict(plugin.manifest.get("userConfig")) or {}
    rows: list[list[str]] = []
    for key, raw in sorted(options.items()):
        option = repo.as_dict(raw) or {}
        rows.append(
            [
                f"`{key}`",
                repo.as_str(option.get("type")) or "",
                "Yes" if option.get("required") is True else "No",
                "Yes" if option.get("sensitive") is True else "No",
                repo.as_str(option.get("description")) or "",
            ]
        )
    return rows


# --------------------------------------------------------------------------
# Block content


def plugin_blocks(plugin: Plugin) -> dict[str, str]:
    sections = ["Overview", "Requirements", "Installation", "Usage", "Components"]
    configuration = config_rows(plugin)
    privileged = is_privileged(plugin)
    if configuration:
        sections.append("Configuration")
    if privileged:
        sections.append("Permissions")
    sections += ["Uninstall", "Documentation", "License"]
    nav = " · ".join(f"[{title}](#{title.lower()})" for title in sections)
    badges = " ".join(
        [
            badge("version", plugin.version, "blue", "CHANGELOG.md"),
            badge(
                "category",
                plugin.category,
                "informational",
                f"{BLOB}/README.md#categories",
            ),
            badge(
                "Claude Code",
                f"≥ {plugin.min_claude_code}",
                "orange",
                "https://code.claude.com/docs",
            ),
            badge("license", "MIT", "green", f"{BLOB}/LICENSE"),
            ci_badge(),
            *component_badges(plugin),
            badge(
                "runs code",
                "yes, reviewed" if privileged else "no",
                "yellow" if privileged else "brightgreen",
                "#permissions" if privileged else "#components",
            ),
        ]
    )
    description = repo.as_str(plugin.manifest.get("description")) or ""
    blocks = {
        "header": "\n\n".join(
            [
                badges,
                description,
                f"Part of [Claude Essentials]({repo.REPOSITORY_URL}), an independent community plugin marketplace for Claude Code. Not affiliated with or endorsed by Anthropic.",
                f"**Contents:** {nav}",
            ]
        ),
        "requirements": f"- Claude Code {plugin.min_claude_code} or later.",
        "installation": "\n\n".join(
            [
                "Inside a Claude Code session:",
                f"```text\n/plugin marketplace add {INSTALL_SOURCE}\n/plugin install {plugin.name}@{repo.MARKETPLACE_NAME}\n```",
                "From your shell:",
                f"```bash\nclaude plugin marketplace add {INSTALL_SOURCE}\nclaude plugin install {plugin.name}@{repo.MARKETPLACE_NAME}\n```",
                f"Background auto-update is off for community marketplaces. Get fixes with `claude plugin update {plugin.name}@{repo.MARKETPLACE_NAME}`, or turn on **Enable auto-update** for `{repo.MARKETPLACE_NAME}` under `/plugin` → **Marketplaces**.",
            ]
        ),
        "components": table(["Type", "Name", "What it does"], components(plugin))
        if components(plugin)
        else "This plugin has no components yet.",
        "uninstall": f"```text\n/plugin uninstall {plugin.name}@{repo.MARKETPLACE_NAME}\n```",
        "documentation": table(
            ["Document", "Read it for"],
            [
                [
                    "[Changelog](CHANGELOG.md)",
                    "Release notes and migration steps for this plugin",
                ],
                [
                    f"[Claude Essentials]({BLOB}/README.md)",
                    "The marketplace, its catalog and how to keep plugins updated",
                ],
                [
                    f"[Security policy]({BLOB}/SECURITY.md)",
                    "Reporting a vulnerability privately",
                ],
                [
                    f"[Security review]({BLOB}/docs/security-review.md)",
                    "How plugins that run code are reviewed",
                ],
                [
                    f"[Contributing]({BLOB}/CONTRIBUTING.md)",
                    "Reporting a bug or proposing a change to this plugin",
                ],
                [
                    "[Claude Code plugins](https://code.claude.com/docs/en/plugins/install)",
                    "Installing, updating and removing plugins",
                ],
            ],
        ),
        "license": f"This plugin is released under the [MIT License]({BLOB}/LICENSE), like the rest of Claude Essentials. Third-party material is listed in [THIRD_PARTY_NOTICES.md]({BLOB}/THIRD_PARTY_NOTICES.md).",
    }
    if configuration:
        blocks["configuration"] = "\n\n".join(
            [
                f"Claude Code asks for these options when you enable the plugin. Change them later with `/plugin configure {plugin.name}@{repo.MARKETPLACE_NAME}`.",
                table(
                    ["Option", "Type", "Required", "Sensitive", "Description"],
                    configuration,
                ),
            ]
        )
    if privileged:
        blocks["runtime"] = "\n\n".join(
            [
                "What this plugin runs on your machine, generated from its configuration files:",
                table(["Component", "Runs"], runtime_rows(plugin)),
            ]
        )
    return blocks


def apply_blocks(
    text: str, blocks: dict[str, str], where: str
) -> tuple[str, list[str]]:
    problems: list[str] = []
    present = {
        str(found.group(1))
        for found in re.finditer(r"<!-- BEGIN GENERATED: ([a-z-]+) -->", text)
    }
    for name in sorted(present - set(blocks)):
        problems.append(
            f'{where}: block "{name}" does not apply to this plugin; remove it and its section'
        )
    for name, content in blocks.items():
        pattern = re.compile(
            rf"({re.escape(BEGIN.format(name))}\n)(.*?)({re.escape(END.format(name))})",
            re.DOTALL,
        )
        if not pattern.search(text):
            heading = {
                "configuration": "## Configuration",
                "runtime": "## Permissions",
            }.get(name, f"block {name}")
            problems.append(
                f"{where}: add {BEGIN.format(name)} and {END.format(name)} under {heading}"
            )
            continue
        text = pattern.sub(
            lambda m, c=content: f"{m.group(1)}\n{c}\n\n{m.group(3)}", text, count=1
        )
    return text, problems


# --------------------------------------------------------------------------
# Root README


def root_readme(plugins: list[Plugin]) -> str:
    data = repo.as_dict(repo.load_json(repo.MARKETPLACE_FILE)) or {}
    version = repo.as_str(data.get("version")) or "0.0.0"
    if plugins:
        rows = [
            [
                f"[{p.display_name}](plugins/{p.name}/README.md)",
                f"`{p.name}`",
                f"[{p.category}](#categories)",
                p.version,
                repo.as_str(p.entry.get("description")) or "",
            ]
            for p in plugins
        ]
        catalog = table(
            ["Plugin", "Install as", "Category", "Version", "Description"], rows
        )
    else:
        catalog = "No plugins are published yet."
    counts = {
        category: sum(1 for p in plugins if p.category == category)
        for category in repo.CATEGORIES
    }
    categories = table(
        ["Category", "Covers", "Plugins"],
        [
            [f"`{c}`", repo.CATEGORY_DESCRIPTIONS[c], str(counts[c])]
            for c in repo.CATEGORIES
        ],
    )
    badges = " ".join(
        [
            badge("marketplace", f"v{version}", "blue", "CHANGELOG.md"),
            badge("plugins", str(len(plugins)), "informational", "#plugins"),
            badge(
                "Claude Code",
                f"≥ {repo.MIN_CLAUDE_CODE}",
                "orange",
                "https://code.claude.com/docs",
            ),
            badge("license", "MIT", "green", "LICENSE"),
            ci_badge(),
            badge("community", "unaffiliated", "lightgrey", "#claude-essentials"),
        ]
    )
    text = (TEMPLATES / "root.md").read_text(encoding="utf-8")
    values = {
        "badges": badges,
        "catalog": catalog,
        "categories": categories,
        "min_claude_code": repo.MIN_CLAUDE_CODE,
    }
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", value)
    return text


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    _ = parser.add_argument(
        "--check", action="store_true", help="fail instead of writing"
    )
    args = parser.parse_args()
    check_only: bool = args.check  # pyright: ignore[reportAny]  # argparse Namespace attributes are Any

    problems: list[str] = []
    stale: list[str] = []
    plugins = load_plugins()
    targets: list[tuple[Path, str]] = [
        (repo.ROOT / "README.md", prettier(root_readme(plugins), "README.md"))
    ]
    for plugin in plugins:
        readme = plugin.path / "README.md"
        where = str(readme.relative_to(repo.ROOT))
        if not readme.is_file():
            problems.append(f"{where}: missing")
            continue
        updated, block_problems = apply_blocks(
            readme.read_text(encoding="utf-8"), plugin_blocks(plugin), where
        )
        problems.extend(block_problems)
        targets.append((readme, prettier(updated, where)))

    for path, expected in targets:
        current = path.read_text(encoding="utf-8") if path.is_file() else ""
        if current == expected:
            continue
        stale.append(str(path.relative_to(repo.ROOT)))
        if not check_only:
            _ = path.write_text(expected, encoding="utf-8")

    for problem in problems:
        print(f"✘ {problem}")
    if check_only and stale:
        for path in stale:
            print(
                f"✘ {path}: generated content is stale; run `uv run scripts/sync_readmes.py`"
            )
    if problems or (check_only and stale):
        return 1
    print(
        f"sync_readmes: {'checked' if check_only else 'updated'} {len(targets)} README file(s)"
        + (f", rewrote {', '.join(stale)}" if stale and not check_only else "")
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
