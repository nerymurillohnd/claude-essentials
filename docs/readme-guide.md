# README guide

How the root README and plugin READMEs are built. Decision: [ADR generated-readme-content](adr/decisions/ADR_2026-10-03_generated-readme-content.md).

## Two templates

| File                       | Template                     | How it is maintained                                                                        |
| -------------------------- | ---------------------------- | ------------------------------------------------------------------------------------------- |
| `README.md`                | `templates/readme/root.md`   | Rendered entirely by `scripts/sync_readmes.py`; edit the template, never `README.md`        |
| `plugins/<name>/README.md` | `templates/readme/plugin.md` | Created by the scaffold; authors write their sections, the script rewrites generated blocks |

Run `scripts/sync_readmes.py` after changing a manifest, the catalog or a component. `scripts/check.py` runs it with `--check` and fails on stale content.

## Plugin README structure

The README is what users read before they install: it says what the plugin contains, what it is for and what it solves. Sections come in this order, each heading with its emoji; `README_SECTIONS` in `scripts/repo.py` is the single list the template, the generated Contents line and the `repo` gate share ([ADR plugin-readme-sections](adr/decisions/ADR_2026-10-05_plugin-readme-sections.md)).

| Section                 | Required                  | Content                                                                                                                                                                      |
| ----------------------- | ------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Title                   | Yes                       | `displayName`                                                                                                                                                                |
| Header                  | Yes                       | Generated: badges, description, affiliation statement, Contents line                                                                                                         |
| 📖 Overview             | Yes                       | Author: the problem, the audience, what users get                                                                                                                            |
| 🎯 What it does         | Yes                       | Author: a table of two to four situations, with the columns Situation, What the plugin does and Result                                                                       |
| 📋 Prerequisites        | Yes                       | Generated table with the Claude Code minimum and its check command; then author: a table of every other tool with Tool, Minimum, Check and Why, or "No other prerequisites." |
| ⚡ Installation         | Yes                       | Generated: the one-command session install with `--marketplace`, the two-step session install and the shell install                                                          |
| 🚀 Usage                | Yes                       | Author: at least one concrete example per component                                                                                                                          |
| 🧩 Components           | Yes                       | Generated from the plugin's files; each name links to its file                                                                                                               |
| 🔧 Configuration        | When `userConfig` exists  | Generated table of options                                                                                                                                                   |
| 🔐 Permissions          | When the plugin runs code | Author: why each item is needed; generated table of what runs                                                                                                                |
| ❓ FAQ                  | Yes                       | Author: 3 to 5 questions in `<details>` blocks, see [FAQ](#faq)                                                                                                              |
| 🔄 Update and uninstall | Yes                       | Generated: update from the shell and in a session, `/reload-plugins`, version check, disable and uninstall, and the data uninstalling deletes                                |
| 📚 Documentation        | Yes                       | Generated links to the changelog and repository documents                                                                                                                    |
| 📄 License              | Yes                       | Generated                                                                                                                                                                    |

A section that does not apply is left out entirely, never written as "N/A". The script reports a generated block that does not apply, and a missing block that does. Each emoji is a single code point: a variation selector would stay in the heading's anchor.

## FAQ

- The FAQ holds 3 to 5 questions, each in its own `<details>` block with the question in `<summary>`. The `repo` gate counts them.
- The first question is always "Does installing this plugin modify my project?", answered precisely: what installing changes, and what changes only when a component runs.
- Choose the others from the questions users of this kind of plugin ask:

| The plugin ships           | Candidate questions                                                                                                  |
| -------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| Skills                     | Does the skill run on its own, or only when I invoke it? What does it change, and when does it stop for my approval? |
| Agents                     | What can the agent read or change? Which model does it use?                                                          |
| Hooks                      | What does each hook block or change, and how do I turn it off? Does it slow down my session?                         |
| MCP or LSP servers, `bin/` | What does it run on my machine? Which hosts does it reach?                                                           |
| Any plugin                 | Does it send my code anywhere? Does it work on Windows? Does it need an account or a paid service?                   |

Answer only what is true of the published version; leave out a question you cannot answer with certainty.

## Links

- Generated content links what it can: each component in the Components table to its file, the Contents line to every section, badges to their sections, and repository documents to absolute GitHub URLs.
- In author sections, link the first mention of a component to its file and of a repository document or Claude Code page to its URL.
- Inside a plugin, relative links only to files in the same plugin; everything else uses absolute GitHub URLs, because Claude Code copies the plugin alone into the user's cache.
- Links to a README section use its anchor, which starts with a hyphen because of the emoji: `#-what-it-does`.

## Conventions

- **Badges:** generated static images from manifest data plus GitHub's workflow status badge. Root: plugin count, minimum Claude Code, license, CI, community status. Plugin: version, category, minimum Claude Code, license, CI, one badge per component type, and whether the plugin runs code.
- **Hierarchy:** one `#` title, `##` sections in the order above, short paragraphs, tables for facts that compare (components, options, documents), prose for explanations.
- **Code blocks:** always fenced with a language: `text` for slash commands typed in Claude Code, `bash` for shell commands, `json` for settings.
- **Collapsible sections:** `<details>` only for advanced or rarely needed content, such as pinning or sparse clones.
- **Placeholders:** `{{name}}` is filled by scripts; `TODO:` marks text the author must write. `scripts/check.py` fails while either remains in a plugin.
- **Generated blocks:** the content between `<!-- BEGIN GENERATED: <block> -->` and `<!-- END GENERATED: <block> -->` is overwritten; change the source instead.
- **Tone:** say what the plugin does for the user and what it runs on their machine. No marketing language, no claims the plugin cannot back up.
