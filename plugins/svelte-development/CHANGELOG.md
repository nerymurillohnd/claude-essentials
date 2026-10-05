# Changelog

Notable changes to this plugin are documented here for its users.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and plugin versions follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-10-05

### Added

- `svelte-best-practices` skill: current rules for Svelte 5.57 and SvelteKit 3.0 (runes, template syntax, async and boundaries, routing, loading, form actions, remote functions, hooks, environment variables, adapters, security, migration from SvelteKit 2), the Svelte CLI, Astro 7 islands and Tailwind CSS 4, with a map of every official documentation section, a changelog check and a list of known documentation errors.
- `svelte-docs-and-autofixer` skill: looks up the current Svelte documentation and runs the Svelte autofixer through the Svelte MCP server, with command-line and raw-download fallbacks.
- `svelte-lsp-navigation` skill: code navigation and diagnostics for `.svelte` files through the Svelte language server, with a SvelteKit 3 example project.
- `svelte-component-editor` agent: writes and edits Svelte and SvelteKit code and proves each change with the docs, the autofixer, the language server and `sv check`.
- `svelte-code-auditor` agent: read-only audit of Svelte and SvelteKit code with evidence-backed findings.
- The Svelte team's remote MCP server (`https://mcp.svelte.dev/mcp`), which needs no install and reconnects on its own, and the Svelte language server (`svelteserver`) for `.svelte` files, run from a binary you install.
- Built on the Svelte team's AI tools (sveltejs/ai-tools, MIT); see NOTICE.
