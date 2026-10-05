---
status: accepted
date: 2026-10-05
decision-makers:
  - "Nery Samuel Murillo (maintainer)"
consulted:
  - "Claude Code by Anthropic (research, drafting and verification)"
---

# Plugins derived from a project's own official AI content

## Purpose

Allow a plugin to start from the AI content (skills, agents, MCP and LSP configuration) that a software project publishes for its own technology, credit it, and improve it, without weakening the clean-room policy for everything else.

## Scope

Plugins in `plugins/` whose skills, agents or server configuration derive from an upstream project's official AI content, starting with `svelte-development`, derived from `sveltejs/ai-tools`. It does not cover third-party marketplaces or plugin collections in general, which [ADR clean-room-policy](ADR_2026-10-03_clean-room-policy.md) still governs.

## Context and problem statement

The Svelte team publishes official skills, an agent, an MCP server and an LSP configuration for Claude Code in `sveltejs/ai-tools` (MIT). They are a strong base, but they contain no SvelteKit content, predate SvelteKit 3.0.0 (2026-10-01), call tools by wrong names, and start their MCP server with `npx -y`, which downloads at every session start and breaks [ADR security-posture](ADR_2026-10-03_security-posture.md). The clean-room policy forbids using another plugin collection as a source of content. The maintainer decided on 2026-10-05 (this session, option C of three: an external `git-subdir` entry, a cross-marketplace dependency, or a derived plugin) to build a derived plugin.

## Decision drivers

- Users get the project's own knowledge, corrected and extended, with the project credited.
- Licensing: the upstream license must allow modification and redistribution, and its notice must travel with every installed copy.
- Security posture: no downloads at install or session start, every host declared.
- Currency: a derived copy freezes, so changes upstream must be noticed.
- No implied endorsement by the upstream project.

## Considered options

- Derived plugin in `plugins/<name>/`, credited, with a recorded base commit
- External `git-subdir` catalog entry pointing at the upstream plugin, pinned by `sha`
- Plugin dependency on the upstream marketplace (`allowCrossMarketplaceDependenciesOn`)

## Decision outcome

Chosen option: **derived plugin**, because it is the only option that lets us fix the MCP startup, the tool names and the missing SvelteKit 3 content, while the other two ship upstream's plugin unchanged.

A derived plugin is accepted only when all of these hold:

- The upstream is the project's **own official** AI content for its own technology, and the maintainer names it explicitly.
- Its license allows modification and redistribution (MIT, Apache-2.0, BSD or similar).
- The plugin ships a `NOTICE` file that carries the upstream copyright and license text, the upstream repository, the base commit and the list of derived files. The plugin `LICENSE` stays the repository template.
- The derived skills carry `license` and `metadata` frontmatter that name the upstream and base commit.
- `THIRD_PARTY_NOTICES.md` and `docs/sourcing-log.md` get a row.
- Names, descriptions and READMEs never call the derived content "official", never use the upstream logo or colours, and state that the project does not endorse the plugin.
- Component names differ from upstream's when users can install both, so two copies with conflicting instructions never share a name.
- Before every release of the plugin, the maintainer compares the upstream against the recorded base commit and merges what still applies (`.claude/rules/plugins/derived-content.md`).

### Consequences

- Good, because users get corrected, current and extended content, and the upstream gets visible credit.
- Good, because the security posture holds: nothing downloads at session start. The MCP server is the Svelte team's remote HTTPS server, declared in the README Permissions section with what it receives (maintainer decision, 2026-10-05: it reconnects on its own, which a local stdio server does not, and needs no install), and the language server is a binary the user installs.
- Bad, because upstream changes no longer arrive automatically; the pre-release comparison is manual until automation is approved.
- Bad, because the clean-room policy now has an exception that reviewers must apply carefully.

### Confirmation

Reviewers check every condition above in the pull request that adds or releases a derived plugin. The maintainer rule `.claude/rules/plugins/derived-content.md` holds the pre-release comparison. Revisit if an upstream changes its license or asks not to be redistributed.

## Pros and cons of the options

### Derived plugin

- Good, because everything can be fixed and extended.
- Bad, because updates need a manual merge.

### External `git-subdir` entry

- Good, because updates only need a new `sha`.
- Bad, because nothing can be changed: with a `plugin.json` present, entry `mcpServers` and `lspServers` do not apply, so the `npx -y` startup ships as is.

### Cross-marketplace dependency

- Good, because the upstream stays the single source.
- Bad, because it installs the same `npx -y` server and two plugins with overlapping skills.

## More information

Evidence: the Claude Code [marketplace reference](https://code.claude.com/docs/en/plugins/marketplace-reference) (plugin sources, how an entry combines with `plugin.json`), [plugin dependencies](https://code.claude.com/docs/en/plugins/dependencies), the `sveltejs/ai-tools` MIT license at commit `6b5d0dab3c9c083387247ab20dc684573481076b`, and the [Svelte branding guidelines](https://github.com/sveltejs/branding).
