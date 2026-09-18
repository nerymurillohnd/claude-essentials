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

Required fields: `name` (must equal the directory name, kebab-case) and
`description`. See `schemas/plugin.schema.json` for the full field list, and
[plugins-reference.md](https://code.claude.com/docs/en/plugins-reference.md)
for everything Claude Code itself understands (author, license, keywords,
component paths, hooks, mcpServers, dependencies, ...).

Set `kind` to `bundle`, `skill-only`, or `agent-only` to match the template you
started from.

## 3. Write the actual skill/agent/command content

- Skills: `skills/<skill-name>/SKILL.md` — see [skills.md](https://code.claude.com/docs/en/skills.md)
  for frontmatter fields (`name`, `description`, `allowed-tools`, `context`, `agent`, `arguments`, ...).
- Agents: `agents/<agent-name>.md` — see [sub-agents.md](https://code.claude.com/docs/en/sub-agents.md)
  for frontmatter fields (`name`, `description`, `tools`, `model`, `color`, ...).
- Commands, hooks, MCP servers: see [plugins.md](https://code.claude.com/docs/en/plugins.md).

Add a plugin-level `README.md` explaining what it does and why.

## 4. Regenerate and validate the catalog

```bash
npm run generate   # rebuilds .claude-plugin/marketplace.json from plugins/*
npm run validate   # schema-checks marketplace.json + every plugin.json
npm run check       # both, plus biome format/lint
```

`npm run generate` is what actually adds your plugin to the marketplace
catalog — don't hand-edit the `plugins` array in `.claude-plugin/marketplace.json`,
it will just get overwritten.

## 5. Open a PR

CI runs `npm run check` on every PR. It must pass before merge.
