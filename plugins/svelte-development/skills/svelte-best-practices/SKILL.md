---
name: svelte-best-practices
description: How to write fast, robust, modern Svelte 5 and SvelteKit 3 code - runes and reactivity, effects and their alternatives, events, snippets, styling, context, SvelteKit 3 imports, config, environment variables, routing, loading, forms, remote functions, hooks, adapters and security - plus the Svelte CLI (sv), Astro with Svelte islands and Tailwind CSS 4, with one reference per topic and a guided migration for older projects. Use before writing, reviewing, converting or explaining any Svelte or SvelteKit code, including a component pasted in the chat.
when_to_use: Triggers include a .svelte file or snippet, "convert to Svelte 5", "migrate from Svelte 4" or "upgrade to SvelteKit 3", code with export let, $:, on:click, slot elements or createEventDispatcher, a SvelteKit route, load function, hook, form action or vite.config, sv create, sv add or sv migrate, and Svelte with Astro or Tailwind CSS.
license: MIT
metadata:
  upstream: "sveltejs/ai-tools skills/svelte-core-bestpractices"
  base: "6b5d0dab3c9c083387247ab20dc684573481076b"
---

# Svelte 5 and SvelteKit 3 best practices

This skill is the contract for writing Svelte by the current rules: **Svelte 5** in runes mode and **SvelteKit 3**. Most Svelte code in training data is older, so the practices below are where a model goes wrong; each topic has a reference with the foundations, short examples and the exact official sections to fetch.

## Contents

- [When to use it](#when-to-use-it)
- [Which tool first](#which-tool-first)
- [Rules for working](#rules-for-working)
- [Who does the work](#who-does-the-work)
- [Svelte 5 practices](#svelte-5-practices)
- [SvelteKit 3 practices](#sveltekit-3-practices)
- [Where things are](#where-things-are)
- [Procedure](#procedure)

## When to use it

| Use it | Do not use it |
|---|---|
| Writing, converting or reviewing Svelte components, `.svelte.ts`/`.svelte.js` modules or SvelteKit files | For where a symbol of the project is used: that is the `svelte-lsp-navigation` skill |
| Migrating from Svelte 4 or SvelteKit 2 | For React, Vue, plain TypeScript or other non-Svelte code |
| Setting up a project with `sv`, or Svelte with Astro or Tailwind CSS | |
| Explaining how something is done in Svelte 5 or SvelteKit 3 | |

## Which tool first

The default route, because each tool answers a different kind of question. Depart from it when the project gives a reason, and say why.

| The question is about | First tool | Why |
|---|---|---|
| A symbol of this project: where it is defined or used, who calls it, its type, what a change breaks | The LSP tool: `documentSymbol` or `workspaceSymbol`, then `findReferences`, `goToDefinition`, `hover`, `incomingCalls` | It answers by symbol, through imports and aliases. Grep matches text and a whole-file Read spends context: Grep follows only for what the server cannot see: route files, paths in strings, CSS classes, configuration. Without `svelteserver` on the PATH there is no LSP tool: use Grep and say they are text matches |
| How a Svelte or SvelteKit API works at the installed version | `mcp__plugin_svelte-development_svelte__get-documentation` | Training data shows older Svelte and SvelteKit |
| Whether the project has errors | The project check: `npm run check`; without a `check` script, `npx --no-install svelte-check` (after `npx --no-install svelte-kit sync` in SvelteKit) | Diagnostics arrive only for files the language server has open |

## Rules for working

These rules hold for every later turn of the task, not only the turn that loaded this skill.

1. **Never write Svelte from memory alone.** Read the reference for the topic, fetch the live sections the task touches before writing (the reference lists them), and run the autofixer after. Skip the fetch only when the change uses no Svelte or SvelteKit API, such as copy, CSS values or markup text.
2. **Never skip the fetch when** an exact signature, option name or config key matters; the code uses an experimental feature, an adapter, environment variables, hooks or the Vite config; or what you remember disagrees with a reference, or a reference with the docs.
3. **Latest by default.** Write Svelte 5 runes and SvelteKit 3, and check the installed versions first ([procedure](#procedure), step 1). On an older major, propose the migration before writing ([migrating-to-kit-3.md](references/kit/migrating-to-kit-3.md), [legacy-and-migration.md](references/svelte/legacy-and-migration.md)); the two majors are independent. Write for the installed version only when the user declines, or when the request says to proceed without questions; then never mix versions, and say that the code is for the older version. No project, or no version found: write the latest and say so. SvelteKit 1 or Svelte 3 first need the legacy `sv migrate sveltekit-2` or `svelte-4` steps ([sv-cli.md](references/tooling/sv-cli.md)).
4. **Source precedence.** Package changelogs, release notes and source code decide what exists at the installed version; the official docs explain usage, and some pages still show older code ([known-doc-errata.md](references/known-doc-errata.md)); these references are the starting point and lose to both. When sources conflict, say so; never pick one silently. When a reference disagrees with what the installed version does, read the changelog window in [changelogs.md](references/changelogs.md).
5. **No WebFetch for docs or changelogs**: WebFetch, like any web-fetch tool, returns a truncated summary. Use the MCP tools or `curl`.
6. **Project instructions decide conventions, not APIs.** The project's `CLAUDE.md`, saved memory and team conventions win on naming, file layout and formatting. They never make an API valid that the installed version removed; when one asks for such an API, say so.

## Who does the work

Decide this before the first tool call. On an older major, settle the migration first (rule 3) and say in the agent's prompt whether the user migrated, declined, or asked to proceed without questions.

| Situation | Who | How |
|---|---|---|
| A question, an explanation, a review or conversion of code pasted in the chat, or a change of one or two lines | You | Follow the [procedure](#procedure) inline |
| Creating, editing, refactoring or migrating `.svelte`, `.svelte.ts`, `.svelte.js` or SvelteKit route files beyond a line or two | `svelte-component-editor` agent | Delegate with the Agent tool (below) |
| Reviewing, auditing or checking a codebase, a pull request or a migration without changing it | `svelte-code-auditor` agent | Delegate with the Agent tool (below) |
| The user asks you to work inline, or you already are one of these agents | You | Never delegate further |

The documentation lookups and the autofixer loop then run in the agent's context instead of filling the main conversation. The agent starts without this conversation, so its prompt names the files, the task, the constraints and what to report. Call it without a `name`: a named call can start an agent-team teammate instead of a subagent, and a teammate gets none of the agent's preloaded skills.

```text
Agent
  subagent_type: "svelte-development:svelte-component-editor"
  description: "Add a filter to TodoList"
  prompt: "In src/lib/TodoList.svelte, add a text filter over the items. Keep its props and callbacks working for its parents …"
```

For an audit, use `subagent_type: "svelte-development:svelte-code-auditor"` and name the scope. Source: https://svelte.dev/docs/ai/subagent and https://svelte.dev/docs/ai/instructions.

## Svelte 5 practices

**State and derived values** ([runes.md](references/svelte/runes.md))

- Use `$state` only for values that drive an effect, a derived or the template; everything else is a plain variable. Objects and arrays become deep proxies; for large values that are only reassigned (API responses), use `$state.raw`.
- Compute with `$derived(expression)`, or `$derived.by(() => …)` for several statements, never with an `$effect` that writes state. Deriveds can be reassigned for optimistic UI and return objects as they are, without a proxy.
- Treat props as values that change: anything computed from a prop is a `$derived`, not a plain `let`. Props come from a typed `$props()` destructuring; `$bindable()` marks one the parent may bind. Pass a getter (`() => count`), not the value, to a function or context that must stay live.
- Share reactive logic with classes whose fields are `$state`, in `.svelte.ts` modules, instead of stores.

**Effects are an escape hatch** ([runes.md](references/svelte/runes.md), [context-lifecycle-and-reactivity-classes.md](references/svelte/context-lifecycle-and-reactivity-classes.md))

- Avoid updating state inside `$effect`. Instead: sync an external library (D3, a map) with `{@attach}`; react to user input in the event handler or with a function binding (`bind:value={get, set}`); log with `$inspect`; observe something outside Svelte with `createSubscriber`.
- Effects run only in the browser: never wrap their body in `if (browser)`.
- To see why something re-runs, put `$inspect.trace(label)` on the first line of the `$effect` or `$derived.by`.

**Template** ([template-syntax.md](references/svelte/template-syntax.md))

- Events are attributes: `onclick={…}`, `{onclick}` and spread props work. For `window` and `document`, use `<svelte:window onkeydown={…} />` and `<svelte:document>`, not `onMount` or `$effect`. Components take callback props, not `createEventDispatcher`.
- Pass content as snippets: `{#snippet name(arg)}` and `{@render name(arg)}`; children arrive as the `children` snippet.
- Key every `{#each}` with a stable unique id, never the index or a freshly built object; do not destructure an item you mutate (`bind:value={item.count}`).
- `{#key}` destroys and recreates everything inside it: use it for transitions, not to re-run a child's logic (use `$derived` there).
- Declaration tags replace `{@const}`: `{const total = $derived(a + b)}` or `{let open = $state(false)}`; prefer `{@attach}` over `use:` actions (`fromAction` wraps an existing one). Both need a minimum Svelte 5 minor ([template-syntax.md](references/svelte/template-syntax.md) gives it); below it, keep `{@const}` and `use:`.
- `class` takes objects and arrays (`class={[open && 'active']}`) instead of the `class:` directive.

**Styling** ([styling-motion-and-elements.md](references/svelte/styling-motion-and-elements.md))

- Pass a JavaScript value to CSS with a custom property: `<div style:--columns={columns}>`, then `var(--columns)` in `<style>`.
- Let a parent style a child with CSS custom properties (`<Child --color="red" />`). Use `:global` only when that is impossible, such as a library component, and scope it under an element of your own.

**Context and async** ([context-lifecycle-and-reactivity-classes.md](references/svelte/context-lifecycle-and-reactivity-classes.md), [async-and-boundaries.md](references/svelte/async-and-boundaries.md))

- Prefer context to state in a shared module: module state leaks between users during server rendering. Use `createContext`, which is typed, rather than `setContext`/`getContext` (the context reference gives its minimum minor; below it, keep `setContext`/`getContext`).
- `await` in components, `hydratable` and `fork` need `compilerOptions.experimental.async`; they change between minor releases, so fetch their sections first (rule 2).

**Avoid legacy features** ([legacy-and-migration.md](references/svelte/legacy-and-migration.md)): runes instead of implicit `let` reactivity and `$:`; `$props` instead of `export let`, `$$props`, `$$restProps`; `onclick` instead of `on:click`; snippets instead of `<slot>`, `$$slots`, `<svelte:fragment>`; `<DynamicComponent>` instead of `<svelte:component this={…}>`; `import Self from './Self.svelte'` instead of `<svelte:self>`; `$state` classes instead of stores; `{@attach}` instead of `use:`; `class` arrays instead of `class:`; `Spring`/`Tween` instead of `spring`/`tweened`; no `beforeUpdate`/`afterUpdate`, no `svelte/legacy` in new code.

## SvelteKit 3 practices

Each line links the reference to read before relying on it.

- **Config** lives in `sveltekit({ … })` in `vite.config.ts`; there is no `svelte.config.js` ([project-and-config.md](references/kit/project-and-config.md)).
- **Imports**: `#lib/x.js` subpath imports declared in `package.json` `imports`, with the extension; server-only code sits under a `server` segment or directory ([project-and-config.md](references/kit/project-and-config.md)).
- **Page state** comes from `$app/state` (`page`, `navigating`, `updated`); reload data with `refreshAll()` or `invalidate` ([loading-data.md](references/kit/loading-data.md)).
- **Environment variables** are declared with `defineEnvVars` in `src/env.ts` and read from `$app/env/private` or `$app/env/public` ([hooks-errors-and-env.md](references/kit/hooks-errors-and-env.md)).
- **Params** are matched by one `src/params.ts` with `defineParams` from `@sveltejs/kit/params` ([routing.md](references/kit/routing.md)); paths come from `resolve('blog/x')` and `asset('x.png')` ([navigation-and-options.md](references/kit/navigation-and-options.md)).
- **Forms**: form actions are stable; remote functions (`query`, `form`, `command`, `prerender`) need `experimental.remoteFunctions` plus the async flag ([forms-and-remote-functions.md](references/kit/forms-and-remote-functions.md)).
- **Secrets and boundaries**: secrets only in server code (`$app/env/private`, `+page.server.ts`, `+server.ts`, hooks, `server` modules). Universal `load` runs on both sides, so nothing private there; never keep per-user data in module-level variables, use `event.locals` or context; sanitize anything passed to `{@html}` ([security.md](references/kit/security.md)).
- **Requirements** (Node, Vite, TypeScript, adapter majors): [project-and-config.md](references/kit/project-and-config.md), [adapters-and-deploy.md](references/kit/adapters-and-deploy.md).

## Where things are

Read every reference the task touches, each once, for anything this page does not settle: a route with a form action needs `routing.md`, `loading-data.md` and `forms-and-remote-functions.md`. Each opens with its source precedence and ends with the exact calls that fetch its official sections.

| Reference | Read when |
| --- | --- |
| [svelte/runes.md](references/svelte/runes.md) | Using `$state`, `$derived`, `$effect`, `$props`, `$bindable`, `$inspect` or `$host` |
| [svelte/template-syntax.md](references/svelte/template-syntax.md) | Writing markup: blocks, snippets, declaration tags, attachments, bindings, events, classes |
| [svelte/async-and-boundaries.md](references/svelte/async-and-boundaries.md) | `await` in components, `<svelte:boundary>`, `fork`, `hydratable`, server rendering |
| [svelte/context-lifecycle-and-reactivity-classes.md](references/svelte/context-lifecycle-and-reactivity-classes.md) | Context, lifecycle, `svelte/reactivity`, stores, `mount`/`hydrate`/`render` |
| [svelte/styling-motion-and-elements.md](references/svelte/styling-motion-and-elements.md) | Styles, transitions, motion, special elements, custom elements, TypeScript |
| [svelte/legacy-and-migration.md](references/svelte/legacy-and-migration.md) | Reading or migrating Svelte 4 code |
| [svelte/gotchas-and-warnings.md](references/svelte/gotchas-and-warnings.md) | A compiler or runtime warning, or behaviour that surprises |
| [kit/project-and-config.md](references/kit/project-and-config.md) | Project layout, `vite.config`, `#lib`, tsconfig, server-only modules |
| [kit/routing.md](references/kit/routing.md) | Routes, layouts, params and matchers, error pages |
| [kit/loading-data.md](references/kit/loading-data.md) | `load`, invalidation, `refreshAll`, `$app/state` |
| [kit/forms-and-remote-functions.md](references/kit/forms-and-remote-functions.md) | Form actions, `use:enhance`, remote functions |
| [kit/hooks-errors-and-env.md](references/kit/hooks-errors-and-env.md) | Hooks, errors, environment variables, service workers, cookies |
| [kit/navigation-and-options.md](references/kit/navigation-and-options.md) | `goto`, link options, page options, `$app/paths` |
| [kit/adapters-and-deploy.md](references/kit/adapters-and-deploy.md) | Choosing or configuring an adapter and deploying |
| [kit/security.md](references/kit/security.md) | CSRF, origins, redirects, secrets, CSP, required security releases |
| [kit/migrating-to-kit-3.md](references/kit/migrating-to-kit-3.md) | Upgrading a SvelteKit 2 project |
| [tooling/sv-cli.md](references/tooling/sv-cli.md) | `sv create`, `sv add`, `sv check`, `sv migrate`, Prettier, testing add-ons |
| [integrations/astro.md](references/integrations/astro.md) | Svelte components inside an Astro site |
| [integrations/tailwind.md](references/integrations/tailwind.md) | Tailwind CSS with SvelteKit or Astro |
| [docs-map.md](references/docs-map.md) | Choosing which official section to fetch |
| [changelogs.md](references/changelogs.md) | The project's version is newer than a reference, or behaviour differs from the docs |
| [known-doc-errata.md](references/known-doc-errata.md) | Before copying a docs example in an area SvelteKit 3 changed |

The sibling skills (`svelte-docs-and-autofixer`, `svelte-lsp-navigation`) are named `svelte-development:<skill>`. When a step needs one that is not loaded yet, load it with the Skill tool:

```text
Skill
  skill: "svelte-development:svelte-docs-and-autofixer"
```

## Procedure

Run these steps in order for any Svelte code you write, convert or review.

1. **Installed versions**, in a project (skip for code pasted in the chat with no project):

   ```sh
   npm ls svelte @sveltejs/kit --depth=0
   ```

   pnpm: `pnpm why svelte`; yarn: `yarn why svelte`. When it prints nothing (no `node_modules`, a monorepo), read the ranges in `package.json` and the lockfile; when the version is still unknown, write for Svelte 5 and SvelteKit 3 and say so. Rule 3 decides: on an old major, propose the migration before step 2; and [changelogs.md](references/changelogs.md) says when to read the changelog window. With no project, write for Svelte 5 and SvelteKit 3 and say so in the answer.
2. **References.** Read every reference from [Where things are](#where-things-are) that the task touches; the practices above apply to every task.
3. **Live sections**, in one call, with the paths from the reference's "Official sources" or the docs map:

   ```text
   mcp__plugin_svelte-development_svelte__get-documentation
     section: ["svelte/$props", "svelte/snippet", "svelte/v5-migration-guide"]
   ```

   If the tool is deferred, load it with ToolSearch (`select:mcp__plugin_svelte-development_svelte__get-documentation`); if the server is unavailable, download the raw section with `curl -sS 'https://svelte.dev/docs/<area>/<slug>/llms.txt'` (the docs map lists every URL) and say the docs were not read through the server.
4. **Write** the code by the rules and the sections. For a review, skip this step and take the code under review to step 5.
5. **Autofix** the full code with `mcp__plugin_svelte-development_svelte__svelte-autofixer` (`code`, `desired_svelte_version` 5, or 4 for Svelte 4 code, `filename`, and `async: true` when the project enables experimental async) until it reports no issues, as the `svelte-docs-and-autofixer` skill says.
6. **Check**, in a project: the language server diagnostics, when `svelteserver` is installed, and the project check, from the project root:

   ```sh
   npm run check                                    # when package.json has a check script
   npx --no-install svelte-kit sync                 # SvelteKit, no check script: generate the types,
   npx --no-install svelte-check --tsconfig ./tsconfig.json   # then check (never chain the two with &&)
   npx --no-install svelte-check                    # Svelte without SvelteKit
   ```

   In SvelteKit, run the sync first: without it the generated types are missing and the check reports false errors. If either reports a problem, fix it and repeat steps 5 and 6; finish only when both are clean.

Derived from the `svelte-core-bestpractices` skill of sveltejs/ai-tools (MIT), base `6b5d0da`, and extended; see the plugin NOTICE. Not affiliated with or endorsed by the Svelte project.
