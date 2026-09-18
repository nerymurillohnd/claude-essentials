# ADR-0001: Standalone skills and agents are distributed as single-component plugins

- **Status**: accepted
- **Date**: 2026-09-18

## Context

The original goal for this repo was to distribute three kinds of things to the
community through one public marketplace: multi-part plugin *bundles*,
standalone *skills*, and standalone *agents* — each independently installable.

Verified against Claude Code's current, official documentation
([plugin-marketplaces.md](https://code.claude.com/docs/en/plugin-marketplaces.md),
[plugins-reference.md](https://code.claude.com/docs/en/plugins-reference.md),
[discover-plugins.md](https://code.claude.com/docs/en/discover-plugins.md)):
a `.claude-plugin/marketplace.json` catalog can only list **plugins**. There is
no marketplace-level mechanism to list or install a bare skill or a bare agent
on its own — `/plugin install` always installs a plugin. The only way to get a
skill onto a machine *without* going through a plugin is dropping it directly
into `~/.claude/skills/` or `<project>/.claude/skills/`, which is a manual,
per-machine action, not something a marketplace entry can trigger.

## Decision

We do not attempt to invent a non-standard distribution path. Instead, a
"standalone skill" or "standalone agent" in this repo is a **plugin whose only
component is that one skill or agent** — a minimal wrapper plugin. From the
installer's point of view (`/plugin install my-skill@claude-essentials`) this
is indistinguishable from installing "just the skill": nothing else comes with
it.

Each plugin declares which of the three shapes it is via a `kind` field in its
`.claude-plugin/plugin.json` (`bundle` | `skill-only` | `agent-only`). This
field is **not** part of Claude Code's own schema — it's a catalog-only
convention this repo's `schemas/plugin.schema.json`, generator, and README use
to group and label plugins. Claude Code itself ignores it.

Starter layouts for all three shapes live in `templates/`.

## Consequences

- Every entry in `plugins/` is a valid, self-contained plugin — no special-cased
  install path to build or maintain.
- A single-skill and a single-agent plugin still carry a `.claude-plugin/plugin.json`
  manifest, which is more ceremony than "just a skill file" — but it's the only
  ceremony Claude Code requires for something to be marketplace-installable, so
  there's no lighter-weight alternative to build instead.
- If Claude Code later adds a native way to distribute a bare skill or agent
  through a marketplace, this ADR should be revisited and the `kind: skill-only`
  / `kind: agent-only` plugins could be migrated to that mechanism without
  changing anything from the installer's perspective.

### Amendment — 2026-09-18: kind is derived from the plugin's files, not declared

- The `kind` field in `plugin.json` is removed from the schema and the
  templates. On 2026-09-18, with Claude Code 2.1.276, `claude plugin validate
  --strict` reported `Unknown field 'kind'` for every plugin. That made the
  official strict validator unusable in CI (DEBT-0001).
- `npm run validate` now derives the kind from what a plugin ships:
  - exactly one `skills/<name>/SKILL.md` and no other component is
    `skill-only`;
  - exactly one `agents/<name>.md` and no other component is `agent-only`;
  - anything else is `bundle`, including declared custom component paths,
    commands, hooks, MCP or LSP servers, output styles, and monitors.
- The plugin README's `**Kind:**` line must match the derived kind. So a
  "skill-only" plugin that grows a second component now fails validation.
  The old manifest field never enforced that.
- The three shapes, their templates, and the distribution decision above are
  unchanged. See [ADR-0003](adr-0003-plugin-versioning-and-tagging.md) and
  the [spec](../superpowers/specs/2026-09-18-repo-protocols-design.md) (D5).
