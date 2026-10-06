# Changelog

Notable changes to this plugin are documented here for its users.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and plugin versions follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- Each skill now opens with what it is for, when to use it and when not, its rules (which hold for the whole task, not only the turn that loaded the skill), and who does the work: you inline, the `svelte-component-editor` agent for file changes, or the `svelte-code-auditor` agent for read-only reviews, with the exact Agent call. The procedures follow, in order, after the rules.
- Every tool a skill or agent asks for is shown as the exact call: the Svelte MCP tools with their parameters, the LSP tool, ToolSearch for deferred tools, the Skill tool call that loads a sibling skill, and the shell commands for the project check, versions, changelog windows and fallbacks. Shell examples quote URLs that contain `$`.
- Skill descriptions name the key use first and add trigger phrases (`when_to_use`), so Claude loads them for code pasted in the chat as well as for project files.
- Both agents list their rules before their workflow, and their descriptions say when to use the other agent instead.
- The docs map's command-line example uses an installed `svelte-mcp` instead of downloading `@sveltejs/mcp` with `npx -y`.
- `svelte-best-practices` and `svelte-docs-and-autofixer` now agree on when to read the docs: always before writing, except for changes that use no Svelte or SvelteKit API (copy, CSS values, markup text); the cases where the fetch is never skipped are unchanged.
- `svelte-lsp-navigation` is shorter: the "Common mistakes" table repeated its rules and is gone, and its operations reference is read when an example or an unexpected result calls for it, not before every session.
- The mistakes Claude makes without the plugin are read before the procedures: the Svelte code rules, the SvelteKit 2 to 3 table and the experimental features in `svelte-best-practices`, and the language server gotchas in `svelte-lsp-navigation`.
- `svelte-lsp-navigation` answers usage questions with a template that marks each location as a language server result or a text match; the editor agent ends with a report template; and `svelte-best-practices` repeats the autofix and check steps until both are clean.
- Defaults instead of menus: sections come from the docs map first (`list-sections` only for a topic the map lacks), and `sv` runs with `npx` unless the project's lockfile names another package manager.

## [0.1.0] - 2026-10-05

### Added

- `svelte-best-practices` skill: current rules for Svelte 5.57 and SvelteKit 3.0 (runes, template syntax, async and boundaries, routing, loading, form actions, remote functions, hooks, environment variables, adapters, security, migration from SvelteKit 2), the Svelte CLI, Astro 7 islands and Tailwind CSS 4, with a map of every official documentation section, a changelog check and a list of known documentation errors.
- `svelte-docs-and-autofixer` skill: looks up the current Svelte documentation and runs the Svelte autofixer through the Svelte MCP server, with command-line and raw-download fallbacks.
- `svelte-lsp-navigation` skill: code navigation and diagnostics for `.svelte` files through the Svelte language server, with a SvelteKit 3 example project.
- `svelte-component-editor` agent: writes and edits Svelte and SvelteKit code and proves each change with the docs, the autofixer, the language server and the project's own check.
- `svelte-code-auditor` agent: audits Svelte and SvelteKit code with evidence-backed findings, without file-editing tools.
- The Svelte team's remote MCP server (`https://mcp.svelte.dev/mcp`), which needs no install and reconnects on its own, and the Svelte language server (`svelteserver`) for `.svelte` files, run from a binary you install.
- Built on the Svelte team's AI tools (sveltejs/ai-tools, MIT); see NOTICE.
