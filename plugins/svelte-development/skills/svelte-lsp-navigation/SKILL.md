---
name: svelte-lsp-navigation
description: Navigates and checks Svelte code with the Svelte language server through Claude Code's LSP tool - jump to definitions, find every reference before a rename or delete, read types on hover, list a component's symbols, trace callers and callees, and read diagnostics after edits, plus whole-project checks with sv check or svelte-check. Use when working in a Svelte or SvelteKit project and the task needs exact symbol locations, the impact of a change, type information, or proof that edited .svelte files have no errors, such as "where is this component used", "rename this prop everywhere", "is this function dead", "why does this type fail" or "check the project for errors".
license: MIT
---

# Svelte LSP navigation

The plugin starts the Svelte language server (`svelteserver --stdio`) for `.svelte` files. It answers by symbol, not by text, so it sees through imports, re-exports, `#lib` aliases and TypeScript inside `<script lang="ts">`. Prefer it over Grep whenever the question is about a symbol rather than a string.

## Contents

- [Before the first call](#before-the-first-call)
- [Tool priority and warm-up](#tool-priority-and-warm-up)
- [Operations](#operations)
- [Workflow for a change](#workflow-for-a-change)
- [Whole-project check](#whole-project-check)
- [What the server sees in dynamic code](#what-the-server-sees-in-dynamic-code)
- [Blind spots](#blind-spots)
- [Common mistakes](#common-mistakes)
- [Gotchas](#gotchas)
- [References](#references)

## Before the first call

- **Start every call from a `.svelte` file.** The plugin maps only `.svelte` to the Svelte server, which gives code intelligence for Svelte documents only. A call on a `.ts`, `.js`, `.svelte.ts` or `.svelte.js` file returns `No LSP server available for file type: .ts`; that is configuration, not a crash. From a `.svelte` file the server still finds definitions and references inside those files. To start from TypeScript files, the user needs a TypeScript language server installed separately.
- If the LSP tool is not in your tool list, it may only be deferred: load it with ToolSearch (`select:LSP`) before concluding it is missing.
- The server needs `svelteserver` on the user's PATH (`npm install -g svelte-language-server`) and TypeScript in the project. If a call on a `.svelte` file returns an error, read [troubleshooting.md](references/troubleshooting.md), then tell the user what is missing.
- Positions are 1-based line and character, as an editor shows them. Put the position on the first character of the symbol's name.
- The server's workspace is the project directory Claude Code was started in (`workspaceFolder` is the project directory). In a monorepo whose Svelte app lives in a subfolder, results that ignore the app's `tsconfig` or `vite.config` may come from a session started at the repository root (not tested on a monorepo); tell the user, and run the whole-project check from the app folder.
- The plugin restarts a crashed server up to three times and waits up to 90 seconds per request; after that, ask the user to run `/reload-plugins`.

## Tool priority and warm-up

The LSP tool is the primary tool for every question about a symbol: where it is defined, where it is used, what type it has, who calls it. Follow this order and do not skip a step:

1. **LSP first.** Make the first code-navigation call an LSP call, from a `.svelte` file. If the LSP tool is not in your tool list, load it with ToolSearch (`select:LSP`).
2. **Warm up before giving up.** If a call returns an error or nothing, do not switch tools yet: run `documentSymbol` on the file to open it and get the exact position, run `hover` at that position to confirm the symbol, then repeat the original call. Stop after three attempts on the same question.
3. **Then say so.** Only after step 2 fails, tell the user that the language server is not answering (and why, if the error says), and continue with the fallback.
4. **Fallback.** For diagnostics, the whole-project check. For symbol locations, Grep, stating that the results are text matches. For API questions, the Svelte MCP documentation tools.
5. **Grep alongside the LSP** only for the [blind spots](#blind-spots) below, never instead of it.

## Operations

All rows were observed working from `.svelte` positions on the bundled fixture ([operations.md](references/operations.md)).

| Operation | Purpose | Use before | Instead of |
|---|---|---|---|
| `goToDefinition` | Jump from a usage to its declaration, through `#lib` imports and component tags | Changing code you did not write | Grep for the name, then Read the matches |
| `findReferences` | Every usage in `.svelte` and `.ts` files, including props passed by parents | Renaming, changing a signature, deleting | Grep, which also matches comments and strings |
| `hover` | The inferred type, including `$props()` and rune-derived types | Writing code that depends on a type | Reading files and tracing types by hand |
| `documentSymbol` | Outline of one component: script symbols, props, markup elements | Working in a long component | Reading the whole file |
| `workspaceSymbol` | Find a symbol by name across the project; `query` must not be empty | Finding related code | Glob or Grep for a name |
| `prepareCallHierarchy` → `incomingCalls` / `outgoingCalls` | Callers per module with call positions, and what a function calls | Deciding whether a function is dead or what a change reaches | Grepping call sites |
| `goToImplementation` | Implementations of an interface | Not observed from a `.svelte` position; use `findReferences` on the interface | — |

The bundled SvelteKit 3 project at `${CLAUDE_PLUGIN_ROOT}/skills/svelte-lsp-navigation/fixtures/kit3-app` has known symbols for trying each operation; its README says how to install a copy.

## Workflow for a change

Copy this checklist when a change touches a symbol other files use:

```
- [ ] 1 Locate     documentSymbol or workspaceSymbol(query) from a .svelte file, for the exact position
- [ ] 2 Impact     findReferences from a .svelte usage (and incomingCalls for functions)
- [ ] 3 Blind      Grep the bare name for the blind spots below
- [ ] 4 Edit       change the declaration and every location from steps 2 and 3
- [ ] 5 Diagnose   read the diagnostics after each edit; fix until no new ones appear
- [ ] 6 Project    run the whole-project check; repeat 4-6 until it is clean
```

There is no rename operation: a rename is steps 2 to 4, including the props passed to the component and destructured in `$props()`.

## Whole-project check

Diagnostics after an edit are pushed once, for the files the server has open, and the LSP tool cannot request them again. For the whole project, run the project's checker from its root:

- The project's `check` script if it has one (`npm run check`); otherwise `npx svelte-kit sync` and then `npx svelte-check --tsconfig ./tsconfig.json`, which runs the `svelte-check` the project already has. `npx sv check` forwards to the same tool but downloads `sv` when the project does not depend on it, so ask before running it. Without `svelte-kit sync`, the generated `./$types` and `$app/types` are missing and the check reports false errors.
- Inside Claude Code, svelte-check prints its machine format by default (`START`, `ERROR "<file>" <line>:<col> "<message>"`, `COMPLETED … ERRORS … WARNINGS`), because it detects the `CLAUDECODE` environment variable. Parse those lines; pass `--output human` only for the user.
- Useful flags: `--threshold error`, `--fail-on-warnings`, `--compiler-warnings <code>:ignore|error`, `--diagnostic-sources "svelte,ts"`, `--tsgo` (TypeScript 7, experimental).

## What the server sees in dynamic code

Dynamic Svelte code is not a blind spot by default. Observed on 2026-10-05 (svelte-language-server 0.18.4):

| Code | Seen | How |
|---|---|---|
| A component held in a variable: `let Active = $state(CounterButton)`, then `<Active />` | Yes | `findReferences` on the import lists the assignment; references of `Active` include its tag |
| `<svelte:element this={tag}>` | Yes | `findReferences` on `tag` includes the `this={tag}` use |
| `{#await lazy then mod}` and `<mod.default />` | Yes | `goToDefinition` on `mod` reaches the await block |
| A function stored in an object: `{ format: formatCount }` | The alias site, yes | `findReferences` on `formatCount` lists the object property |
| A call through that alias: `handlers.format(...)` | Not as a call of the original | `incomingCalls` lists only direct callers; check the alias's own references |
| The path string of `import("#lib/components/X.svelte")` | No | A string, not a reference |
| `import.meta.glob("./*.svelte")` patterns | No | A string pattern |

`documentSymbol` lists every one of these constructs in a component (variables, `$state` holders, await bindings, `mod.default`, `svelte:element`). Run it before concluding that the server cannot see dynamic code.

## Blind spots

Uses the language server cannot see, because they live in strings, file names or configuration. Grep for them, alongside the LSP results, before a rename or delete:

- **Route files**: SvelteKit finds `+page.svelte`, `+layout.svelte`, `+server.ts` and hooks by file name, not by import, so nothing references them.
- **Paths in strings**: `import()` paths, `import.meta.glob` patterns, route paths in `href`, `goto()` and `resolve()`.
- **Calls through an alias**: callers of `obj.fn()` when `fn` was stored in an object; follow the alias with `findReferences`, not `incomingCalls`.
- **Strings and attributes**: CSS class names (including Tailwind classes in `class` objects and arrays), `data-sveltekit-*` attributes.
- **Configuration and scripts**: `vite.config`, `package.json` scripts and `imports`, `svelte-check --ignore` lists, CI files.
- **TypeScript files as a start point**: positions in `.ts`/`.js` files are not served (see above).

## Common mistakes

Each row is a thought that signals the wrong move.

| Tempting thought | Why it is wrong | Instead |
|---|---|---|
| "`findReferences` found nothing, so it is unused." | A position off the name, a start in a `.ts` file, or a server that crashed after route files changed gives the same answer | `hover` at the same position to confirm the symbol, start from a `.svelte` usage, Grep the [blind spots](#blind-spots), then decide |
| "No diagnostics came back, so the component is clean." | Diagnostics are pushed only after an edit and only for open files | Run the whole-project check |
| "The LSP tool is missing, so I'll Grep quietly." | It may only be deferred, and the user would take text matches for semantic answers | Load it with ToolSearch; if it still fails, say "LSP unavailable, using text search" and what that can miss |
| "I'll map `.ts` to the Svelte server so TypeScript files work." | The Svelte server returns empty results for them, hiding symbols, and takes those extensions from a TypeScript server | Start from `.svelte`, or have the user install a TypeScript language server |
| "The language server cannot see dynamic code, so only static diagnostics apply." | It tracks components held in variables, `svelte:element`, await blocks and object aliases; only string paths and patterns are invisible | `documentSymbol` on the file, then `findReferences` on what it lists; Grep only the string cases |
| "I know the LSP parameters, I'll call it directly." | When the tool is deferred, a call without its loaded schema fails with invalid parameters (observed: eight failed calls in a row) | Load it with ToolSearch (`select:LSP`) first, then call it with `operation`, `filePath`, `line`, `character` |
| "Reading the whole component is quicker." | It spends context and still leaves imports to trace | `documentSymbol`, then `goToDefinition`, then Read only the lines needed |
| "An ignore flag gets the check passing." | `--compiler-warnings x:ignore` or `--ignore` hides the problem from every later check and from the user | Fix the cause; ignore only a verified false positive, with the reason |

## Gotchas

- **The language server predates SvelteKit 3's release.** svelte-language-server 0.18.4 and svelte-check 4.7.6 (2026-08-13) read config from `vite.config` and handle Kit 3's top-level config, but these issues were open on 2026-10-05: route files moved, created or deleted can crash the server (language-tools #3108); config reading from `vite.config` can be wrong (#3080); type arguments on `$props()` make destructured props `any` (#3124); TypeScript 7 crashes svelte-check without `--tsgo` (#3063). If results look wrong after such changes, ask the user to run `/reload-plugins` and confirm with the whole-project check.
- **Cloud sessions do not start plugin language servers**, so the LSP tool is unavailable there; use the whole-project check instead.

## References

- [operations.md](references/operations.md): read before the first LSP call in a session; the observed result of each operation on the fixture and what the server answers per file type.
- [troubleshooting.md](references/troubleshooting.md): read when an LSP call fails, returns nothing unexpectedly, or diagnostics never appear.
- For Svelte and SvelteKit rules when fixing what diagnostics report, use the `svelte-best-practices` skill; for the official docs and the autofixer, the `svelte-docs-and-autofixer` skill.

Sources: Claude Code LSP tool (runtime schema and observed results, Claude Code 2.1.289, 2026-10-05), https://code.claude.com/docs/en/plugins/code-intelligence, svelte-check `src/options.ts` (machine output when `CLAUDECODE=1`).
