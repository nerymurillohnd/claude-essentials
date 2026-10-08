# Changelog

Notable changes to this plugin are documented here for its users.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and plugin versions follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.1] - 2026-10-08

### Changed

- Each skill now opens with what it is, when to use it and when not, and the rules it works by, before its contents, so Claude knows how to work before reading the rest. Five ground rules sit at the top of every skill, whichever loads first: read the installed versions and propose a migration on an older major, fetch the docs before using an API, use the language server for symbols, run the autofixer after code, and finish only when the project check is clean.
- Shorter skill descriptions that say what each skill does and when to use it: the three together take about a third of the space they did in the skill list Claude sees on every turn.
- The navigation skill says when a rename is done (the project check ran before, after breaking the declaration, and at the end) and runs `documentSymbol` on importing files before saying a component is not used dynamically.

## [0.3.0] - 2026-10-08

### Fixed

- `flushSync()` inside an effect is no longer described as an error with `experimental.async`: Svelte lifted that restriction in 5.43.15, and the known-errata list now records the docs page that still shows it.
- The component editor no longer reads "SvelteKit 2 or Svelte 4" as "no runes" in a SvelteKit 2 project on Svelte 5: the two majors are independent. Both agents and the best-practices skill also use declaration tags and `{@attach}` only when the installed Svelte has them, and read `package.json` and the lockfile when `npm ls` prints nothing.
- Migrating to SvelteKit 3: the leftover search covers the whole project instead of `src`, the `sv migrate` flags for a run without a prompt are listed, and five breaking changes missing from the manual checklist are added.
- Svelte gotchas now cover `derived_invalid_export`, `derived_references_self`, `snippet_without_render_tag`, `bind_not_bindable`, `props_invalid_value`, `each_key_duplicate` and `effect_orphan`.
- The SvelteKit references say they are for SvelteKit 3 projects, a SvelteKit 2 project keeps `$env/*` unless it enabled explicit environment variables, and the adapter example no longer reuses the removed `ORIGIN` variable.
- Without `svelteserver` on the PATH, the navigation skill checks for the server first and goes straight to labelled text search instead of retrying a tool that cannot answer; a symbol that lives only in `.ts`/`.js` files may start with text search, said to you.
- The final check in every skill falls back to `svelte-check` (after `svelte-kit sync` in SvelteKit) when the project has no `check` script.
- The docs-and-autofixer skill no longer promises a note after each edit that no hook sends.

### Changed

- **Svelte 5 and SvelteKit 3 first.** The best-practices skill now teaches current practice before anything else: it brings back the Svelte team's practices for effects and their alternatives (`{@attach}`, function bindings, `$inspect`, `createSubscriber`), `$inspect.trace`, `<svelte:window>`, `{#key}`, styling with CSS custom properties and `createContext`, and adds a short SvelteKit 3 section. Old versions take one rule instead of three, and the Svelte 4 to 5 example moved to the migration reference.
- **Latest by default, migration proposed on older projects.** In a SvelteKit 2 or Svelte 4 project, Claude proposes the migration to SvelteKit 3 or Svelte 5 before writing, and works on the latest versions after it. It writes code for the older version only if you decline, or ask it to proceed without questions (an automated run), and says so. The component editor reports an older major back instead of editing unless its prompt settles that; the auditor opens its report with the migration recommendation. SvelteKit 1 and Svelte 3 projects are pointed to the older `sv migrate` steps.
- A task that spans several topics reads every reference it touches, not only one.
- The docs-and-autofixer skill loads for checking code, exact APIs and playground links, not for every reply that contains Svelte code.
- The skills are leaner contracts. The SvelteKit 2 to 3 table and the experimental-flag table in `svelte-best-practices` now live only in their references, and the language-server table for dynamic code moved into the navigation reference. References no longer point back to a skill.
- The README says plainly when Claude loads a skill, adds a before-and-after comparison and what the plugin costs you, and puts "only Claude Code is required" before the tool list.

## [0.2.0] - 2026-10-06

### Added

- Hooks that keep the language server first and check Svelte changes before Claude stops. When Claude finishes a turn with changed `.svelte`, `.svelte.ts` or `.svelte.js` files it has not checked, the plugin runs your project's own `svelte-check` (whole project, from `node_modules/.bin`, never downloaded) and sends the errors back, so Claude fixes them in the same turn; it checks each state of your changes once, so older errors cannot keep it in a loop. Claude Code runs hooks without a permission prompt, so the hook runs that one command and nothing else: `svelte-check` is the check in every Svelte project, with or without SvelteKit, and generating a project's types stays your project's own command, behind a prompt. When `svelte-check` can only report that it could not read the project TypeScript configuration, the hook says so and asks Claude to run your project check instead of editing files to satisfy it. The README Permissions section says which items a prompt covers and which it does not. Before a Svelte MCP tool, a `svelte-mcp`, `svelte-check` or `sv` command, or a search in a Svelte project, Claude is told once per session which skill to load, and that symbols go to the language server first. Per-file diagnostics come from the language server after each edit of a `.svelte` file; `.svelte.ts` and `.svelte.js` files get none, so the end-of-turn check is their coverage.

### Changed

- The skills and references carry no version or verification stamps. The versions this plugin targets are declared in its README and nowhere else; no reference opens with a "verified against version X on date Y" line, the errata table has no "checked on" column, and no page claims that a URL answered on a given day. A version number appears only where the number is the fact being taught (the release that added or removed an API, a minimum that carries a security fix, a peer range), in one reference that the others link to. Examples that need the installed version now read it from the project instead of carrying a pasted number. The changelog check no longer keys off those stamps: it fires when the installed version is not the latest on the registry, or when a reference disagrees with what the installed version does.
- The README reads like a page, not like release notes: one paragraph (the description), and tables, labelled bullets and callouts everywhere else, with the Permissions section split into what each prompt covers, what leaves your machine, your files, the hooks, Claude Tag and allow rules.
- A project on Svelte without SvelteKit gets a project check that works: the skills and both agents no longer chain `svelte-kit sync && svelte-check`, which failed the whole check where there is no sync, and show the command for each kind of project.
- Projects still on SvelteKit 2 or Svelte 4 get code for their installed version: the skills and the editor no longer write SvelteKit 3 APIs or runes there unless the task is the migration, and the auditor lists SvelteKit 3 and Svelte 5 changes as migration work instead of defects.
- One routing rule in every skill and both agents: the language server first for questions about the project's own symbols, the docs first for Svelte APIs, the project check first for errors; Claude departs from it only for a reason it states.
- Renames, signature changes and deletions are proven by breaking them on purpose: a baseline project check, a declaration-only change, and a comparison of the new errors with the sites `findReferences` found, so missed uses show up before the edit is finished.
- Both agents run on your session's model even when `CLAUDE_CODE_SUBAGENT_MODEL` is set (`model: inherit`), load their three skills themselves when they run without them (as an agent-team teammate, which gets no preloaded skills), and the skills delegate to them without a `name`, so the call starts a subagent rather than a teammate.
- The language server configuration keeps only the limits it has a reason for: a request now fails after Claude Code's default 60 seconds instead of 90.
- Clearer skills after a full read-through: the Svelte 5 and SvelteKit 3 rules say they apply to projects on those versions (rule 6 no longer demands runes in a Svelte 4 project), the autofixer is called with Svelte version 4 for Svelte 4 code, a review skips the writing step, `.svelte.ts` edits are known to get no language server diagnostics, and the language server skill separates what the language server, the project check and Grep each see in dynamic imports.
- When a tool stays silent, the skills probe the right one: for the language server, `command -v svelteserver` and a `documentSymbol` call on a project component; for the project check, `svelte-kit sync`, the `COMPLETED <n> FILES` line against the tsconfig `include`, what the check script runs, and the app folder in a monorepo.
- The README's Prerequisites list the platforms (macOS, Linux or Windows with Git Bash) and every tool in the order you install it, before the plugin; the language server step comes first, with a global or a per-project install, because without `svelteserver` on your `PATH` the plugin's LSP configuration does nothing.
- Each skill now opens with what it is for, when to use it and when not, its rules (which hold for the whole task, not only the turn that loaded the skill), and who does the work: you inline, the `svelte-component-editor` agent for file changes, or the `svelte-code-auditor` agent for read-only reviews, with the exact Agent call. The procedures follow, in order, after the rules.
- Every tool a skill or agent asks for is shown as the exact call: the Svelte MCP tools with their parameters, the LSP tool, ToolSearch for deferred tools, the Skill tool call that loads a sibling skill, and the shell commands for the project check, versions, changelog windows and fallbacks. Shell examples quote URLs that contain `$`.
- Skill descriptions name the key use first and add trigger phrases (`when_to_use`), so Claude loads them for code pasted in the chat as well as for project files.
- Both agents list their rules before their workflow, and their descriptions say when to use the other agent instead.
- The docs map's command-line example uses an installed `svelte-mcp` instead of downloading `@sveltejs/mcp` with `npx -y`.
- `svelte-best-practices` and `svelte-docs-and-autofixer` now agree on when to read the docs: always before writing, except for changes that use no Svelte or SvelteKit API (copy, CSS values, markup text); the cases where the fetch is never skipped are unchanged.
- `svelte-lsp-navigation` is shorter: the "Common mistakes" table repeated its rules and is gone, and its operations reference is read when an example or an unexpected result calls for it, not before every session.
- The mistakes Claude makes without the plugin are read before the procedures: the Svelte code rules, the SvelteKit 2 to 3 table and the experimental features in `svelte-best-practices`, and the language server gotchas in `svelte-lsp-navigation`.
- `svelte-lsp-navigation` answers usage questions with a template that marks each location as a language server result or a text match; the editor agent ends with a report template; and `svelte-best-practices` repeats the autofix and check steps until both are clean.
- `svelte-best-practices` shows a Svelte 4 component converted to Svelte 5, with the rule behind each change; `svelte-lsp-navigation` says which procedure fits a question, a change or a project check; one term, "project check", names the project's type and Svelte check everywhere; and each output template says whether it is fixed or a default.
- The Svelte MCP tools are named in full (`mcp__plugin_svelte-development_svelte__<tool>`) wherever a call is described, and the skill frontmatter holds no angle-bracket tags.
- The Windows answer in the README FAQ names `grep` and `awk`, which the changelog and search commands need, besides `curl`.
- The project's `CLAUDE.md`, saved memory and conventions decide style and structure over the skills, but never make a removed API valid.
- The README's Permissions section says what changes in Claude Tag: MCP traffic, including code sent to the autofixer, is not in the organization's network export, and the sandbox can block the `curl` fallbacks and has no `svelteserver`.
- Defaults instead of menus: sections come from the docs map first (`list-sections` only for a topic the map lacks), and `sv` runs with `npx` unless the project's lockfile names another package manager.

### Fixed

- The bundled SvelteKit 3 fixture now ships its `src/lib` files (the components, the `Counter` class and `formatCount`): a repository ignore rule had left them out of 0.1.0, so the fixture's imports pointed at files that were missing.

## [0.1.0] - 2026-10-05

### Added

- `svelte-best-practices` skill: current rules for Svelte 5.57 and SvelteKit 3.0 (runes, template syntax, async and boundaries, routing, loading, form actions, remote functions, hooks, environment variables, adapters, security, migration from SvelteKit 2), the Svelte CLI, Astro 7 islands and Tailwind CSS 4, with a map of every official documentation section, a changelog check and a list of known documentation errors.
- `svelte-docs-and-autofixer` skill: looks up the current Svelte documentation and runs the Svelte autofixer through the Svelte MCP server, with command-line and raw-download fallbacks.
- `svelte-lsp-navigation` skill: code navigation and diagnostics for `.svelte` files through the Svelte language server, with a SvelteKit 3 example project.
- `svelte-component-editor` agent: writes and edits Svelte and SvelteKit code and proves each change with the docs, the autofixer, the language server and the project's own check.
- `svelte-code-auditor` agent: audits Svelte and SvelteKit code with evidence-backed findings, without file-editing tools.
- The Svelte team's remote MCP server (`https://mcp.svelte.dev/mcp`), which needs no install and reconnects on its own, and the Svelte language server (`svelteserver`) for `.svelte` files, run from a binary you install.
- Built on the Svelte team's AI tools (sveltejs/ai-tools, MIT); see NOTICE.
