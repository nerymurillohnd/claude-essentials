# README guide

How the root README and plugin READMEs are built. Decision: [ADR generated-readme-content](adr/decisions/ADR_2026-10-03_generated-readme-content.md).

## Two templates

| File                       | Template                     | How it is maintained                                                                        |
| -------------------------- | ---------------------------- | ------------------------------------------------------------------------------------------- |
| `README.md`                | `templates/readme/root.md`   | Rendered entirely by `scripts/sync_readmes.py`; edit the template, never `README.md`        |
| `plugins/<name>/README.md` | `templates/readme/plugin.md` | Created by the scaffold; authors write their sections, the script rewrites generated blocks |

Run `uv run scripts/sync_readmes.py` after changing a manifest, the catalog or a component. `uv run scripts/check.py` runs it with `--check` and fails on stale content.

## Plugin README structure

| Section       | Required                  | Content                                                                                                          |
| ------------- | ------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| Title         | Yes                       | `displayName`                                                                                                    |
| Header        | Yes                       | Generated: badges, description, affiliation statement, navigation                                                |
| Overview      | Yes                       | Author: the problem, the audience, what users get                                                                |
| Requirements  | Yes                       | Generated minimum Claude Code version, then author: other tools, services, accounts, or "No other requirements." |
| Installation  | Yes                       | Generated: install and update commands                                                                           |
| Usage         | Yes                       | Author: at least one concrete example per component                                                              |
| Components    | Yes                       | Generated from the plugin's files                                                                                |
| Configuration | When `userConfig` exists  | Generated table of options                                                                                       |
| Permissions   | When the plugin runs code | Author: why each item is needed; generated table of what runs                                                    |
| Uninstall     | Yes                       | Generated                                                                                                        |
| Documentation | Yes                       | Generated links to the changelog and repository documents                                                        |
| License       | Yes                       | Generated                                                                                                        |

A section that does not apply is left out entirely, never written as "N/A". The script reports a generated block that does not apply, and a missing block that does.

## Conventions

- **Badges:** generated static images from manifest data plus GitHub's workflow status badge. Root: marketplace version, plugin count, minimum Claude Code, license, CI, community status. Plugin: version, category, minimum Claude Code, license, CI, one badge per component type, and whether the plugin runs code.
- **Hierarchy:** one `#` title, `##` sections in the order above, short paragraphs, tables for facts that compare (components, options, documents), prose for explanations.
- **Code blocks:** always fenced with a language: `text` for slash commands typed in Claude Code, `bash` for shell commands, `json` for settings.
- **Collapsible sections:** `<details>` only for advanced or rarely needed content, such as pinning or sparse clones.
- **Navigation:** a generated **Contents** line links to every section anchor.
- **Links:** inside a plugin, relative links only to files in the same plugin; everything else uses absolute GitHub URLs, because Claude Code copies the plugin alone into the user's cache. The root README uses relative links.
- **Placeholders:** `{{name}}` is filled by scripts; `TODO:` marks text the author must write. `uv run scripts/check.py` fails while either remains in a plugin.
- **Generated blocks:** the content between `<!-- BEGIN GENERATED: <block> -->` and `<!-- END GENERATED: <block> -->` is overwritten; change the source instead.
- **Tone:** say what the plugin does for the user and what it runs on their machine. No marketing language, no claims the plugin cannot back up.
