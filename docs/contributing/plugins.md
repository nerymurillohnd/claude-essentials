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

## 4. Regenerate and validate the catalog

```bash
npm run generate   # rebuilds .claude-plugin/marketplace.json from plugins/*
npm run validate   # schema-checks marketplace.json + every plugin.json
npm run check       # both, plus biome format/lint
```

`npm run generate` is what actually adds your plugin to the marketplace
catalog — don't hand-edit the `plugins` array in `.claude-plugin/marketplace.json`,
it will just get overwritten.

## 5. Date the CHANGELOG entry

Replace `{{YYYY-MM-DD}}` in `CHANGELOG.md` with today's date. `version-check`
requires a `## [X.Y.Z] - YYYY-MM-DD` entry matching `version`.

## 6. Open a PR

Fill in the pull request template. CI runs `npm run check` and
`version-check`, and both must pass before merge. After merge, the new
version reaches users through the marketplace (`/plugin update` or
auto-update), and the `Tag plugin versions` workflow tags `<name>--v<version>`
with `claude plugin tag`. See [versioning.md](versioning.md).
