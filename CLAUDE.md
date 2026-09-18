# claude-essentials

Public Claude Code plugin marketplace. Everything under `plugins/` is shipped
to and installed by the community — treat it as a public API surface, not
scratch work.

## Core model

Claude Code's marketplace mechanism only distributes **plugins**
(`/plugin install <name>@claude-essentials`). There is no separate mechanism
for a bare skill or bare agent. This repo ships all three shapes — bundles,
single-skill plugins, and single-agent plugins — as plugins, distinguished
only by a catalog-only `kind` field. Full reasoning:
[docs/decisions/adr-0001-marketplace-distribution-model.md](docs/decisions/adr-0001-marketplace-distribution-model.md).

Before proposing a different distribution mechanism, re-read that ADR and
verify against live docs at https://code.claude.com/docs/en/plugin-marketplaces.md
— don't assume the constraint from memory, it may have changed.

## Working in this repo

- `.claude-plugin/marketplace.json`'s `plugins` array is **generated** by
  `npm run generate` from `plugins/*/.claude-plugin/plugin.json`. Never hand-edit
  that array — edit the individual plugin's manifest and regenerate.
- `npm run check` (Biome format+lint, generate, validate) must pass before any
  commit that touches `plugins/`, `schemas/`, or `scripts/`.
- New plugins start from `templates/plugin-bundle/`, `templates/plugin-skill-only/`,
  or `templates/plugin-agent-only/` — see [docs/contributing/plugins.md](docs/contributing/plugins.md).
- A plugin's manifest `name` must equal its directory name under `plugins/`;
  the generator and validator both enforce this and will fail otherwise.
- Formatting/linting: Biome (`biome.json`) for all JSON/JS in this repo, per
  standing global tooling preference.

## Publishing

Nothing here is pushed to the public GitHub remote or has a GitHub repository
created for it without explicit confirmation in the conversation first — this
repo's whole purpose is public distribution, so a push is not a reversible,
low-stakes action.
