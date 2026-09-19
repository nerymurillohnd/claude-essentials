# Adding a plugin

Every distributable unit in this repo — whether it's a full workflow bundle, a
single skill, or a single agent — is a **plugin** under `plugins/<name>/`. See
[ADR-0001](../decisions/adr-0001-marketplace-distribution-model.md) for why.

## 1. Pick a shape and copy its template

| Shape | Template | Result |
|---|---|---|
| Bundle (multiple skills/agents/commands/hooks) | `templates/plugin-bundle/` | A full workflow plugin |
| Single skill | `templates/plugin-skill-only/` | `/plugin install <name>@claude-essentials` gives exactly one skill |
| Single agent | `templates/plugin-agent-only/` | `/plugin install <name>@claude-essentials` gives exactly one subagent |

```bash
cp -R templates/plugin-skill-only plugins/my-new-skill
```

## 2. Fill in `.claude-plugin/plugin.json`

Required fields: `name` (must equal the directory name, kebab-case, at most 42
characters), `description`, and `version` (explicit semver; new plugins usually
start at `0.1.0`, see [versioning.md](versioning.md)). See
`schemas/plugin.schema.json` for the full field list, and
[plugins-reference.md](https://code.claude.com/docs/en/plugins-reference.md)
for everything Claude Code itself understands (author, license, keywords,
component paths, hooks, mcpServers, dependencies, ...).

Don't declare a `kind`. `npm run validate` derives it from what the plugin
ships, and it must match the `**Kind:**` line in the plugin's README:
exactly one `skills/<name>/SKILL.md` and nothing else is `skill-only`, exactly
one `agents/<name>.md` and nothing else is `agent-only`, and anything else is
`bundle` ([ADR-0001](../decisions/adr-0001-marketplace-distribution-model.md)).
Single-component plugins must use the default layout; declaring custom
component paths in `plugin.json` makes a plugin a bundle.

## 3. Write the actual skill/agent/command content

- Skills: `skills/<skill-name>/SKILL.md` — see [skills.md](https://code.claude.com/docs/en/skills.md)
  for frontmatter fields (`name`, `description`, `allowed-tools`, `context`, `agent`, `arguments`, ...).
- Agents: `agents/<agent-name>.md` — see [sub-agents.md](https://code.claude.com/docs/en/sub-agents.md)
  for frontmatter fields (`name`, `description`, `tools`, `model`, `color`, ...).
- Commands, hooks, MCP servers: see [plugins.md](https://code.claude.com/docs/en/plugins.md).

Fill in the plugin's `README.md` (already copied from the shape). It follows the
[master plugin README](../../templates/plugin-README-reusable-template.md):
15 required sections in a fixed order. A section that doesn't apply still
says so explicitly ("None — this plugin ships no agents."). **What it does not
do**, **Security**, and **Limitations** are never optional. Compatibility may
mark a surface ✅ only after installing from the remote marketplace on that
surface.

Add the plugin's row to the **Plugin catalog** table in the root
[README.md](../../README.md) (sorted by plugin id, replacing the placeholder row
if it is the first plugin), in the format
[templates/root-README-recommended-template.md](../../templates/root-README-recommended-template.md)
describes: the README title linked to `plugins/<id>/README.md`, the one-line
outcome, the kind, the Claude Code and Claude Cowork statuses from the plugin
README's badges, and its additional requirements. Use only requirement badges
listed in the master template's badge catalog; add a new one there first.

## 4. Regenerate and validate the catalog

```bash
npm run generate   # rebuilds .claude-plugin/marketplace.json from plugins/*
npm run validate   # schemas, README contract, and the root README catalog row
npm run check       # everything CI runs
```

`npm run validate` fails when a plugin README drifts from the template (missing,
unknown, or reordered sections; leftover `{{placeholders}}`; more than one alert
per section; code blocks without a language; badges outside the catalog; missing
Claude Code or Cowork install steps) or when the root catalog doesn't list every
plugin exactly once with matching kind and statuses.

`npm run generate` is what actually adds your plugin to the marketplace
catalog — don't hand-edit the `plugins` array in `.claude-plugin/marketplace.json`,
it will just get overwritten.

### Review before the PR

If you work with Claude Code in this repository, run `/plugin-release-review <id>`.
It checks what no script can: whether every README claim is true of the
plugin's files, whether the manifest, catalog row, CHANGELOG, and LICENSE tell
one consistent story, and whether a first-time reader understands what the
plugin does and what it will do to their machine. Its checklist cannot finish
until every step has evidence and the validators pass.

## 5. Date the CHANGELOG entry

Replace `{{YYYY-MM-DD}}` in `CHANGELOG.md` with today's date. `version-check`
requires a `## [X.Y.Z] - YYYY-MM-DD` entry matching `version`.

## 6. Open a PR

Fill in the pull request template. CI runs `npm run check` and
`version-check`, and both must pass before merge. After merge, the new
version reaches users through the marketplace (`/plugin update` or
auto-update), and the `Tag plugin versions` workflow tags `<name>--v<version>`
with `claude plugin tag`. See [versioning.md](versioning.md).
