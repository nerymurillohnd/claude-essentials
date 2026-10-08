---
name: svelte-best-practices
description: The Svelte 5 and SvelteKit 3 rules that training data gets wrong - runes, snippets, event attributes, declaration tags, SvelteKit 3 imports, config, environment variables, routing, loading, forms, remote functions, hooks, adapters and security - plus the Svelte CLI (sv), Astro with Svelte islands and Tailwind CSS 4, with one reference per topic. Use before writing, converting, migrating, reviewing or explaining any Svelte or SvelteKit code, including a component pasted in the chat.
when_to_use: Triggers include a .svelte file or snippet, "convert to Svelte 5", "migrate from Svelte 4" or "upgrade to SvelteKit 3", code with export let, $:, on:click, slot elements or createEventDispatcher, a SvelteKit route, load function, hook, form action or vite.config, sv create, sv add or sv migrate, and Svelte with Astro or Tailwind CSS.
license: MIT
metadata:
  upstream: "sveltejs/ai-tools skills/svelte-core-bestpractices"
  base: "6b5d0dab3c9c083387247ab20dc684573481076b"
---

# Svelte 5 and SvelteKit 3 best practices

This skill is the contract for writing Svelte by the current rules. It is written for **Svelte 5** and **SvelteKit 3**; the plugin README declares every major it targets under "Versions this plugin is written for", and no reference here repeats them. Most Svelte and SvelteKit code in training data is Svelte 4 or SvelteKit 2; the rules below are where it goes wrong, and each topic has a reference with the foundations, short examples and the exact official sections to fetch. The Svelte 5 rules apply to Svelte 5 projects and the SvelteKit 3 rules to SvelteKit 3 projects; rule 7 says what to do in older ones.

## Contents

- [When to use it](#when-to-use-it)
- [Which tool first](#which-tool-first)
- [Rules for working](#rules-for-working)
- [Who does the work](#who-does-the-work)
- [Code rules that training data gets wrong](#code-rules-that-training-data-gets-wrong)
- [SvelteKit 2 to 3 and experimental features](#sveltekit-2-to-3-and-experimental-features)
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
| How a Svelte or SvelteKit API works at the installed version | `mcp__plugin_svelte-development_svelte__get-documentation` | Training data shows Svelte 4 and SvelteKit 2 |
| Whether the project has errors | The project check: `npm run check`; without a `check` script, `npx --no-install svelte-check` (after `npx --no-install svelte-kit sync` in SvelteKit) | Diagnostics arrive only for files the language server has open |

## Rules for working

These rules hold for every later turn of the task, not only the turn that loaded this skill.

1. **Never write Svelte from memory alone.** Read the reference for the topic, fetch the live sections the task touches before writing (the reference lists them), and run the autofixer after; the `svelte-docs-and-autofixer` skill has the tools. Skip the fetch only when the change uses no Svelte or SvelteKit API, such as copy, CSS values or markup text.
2. **Never skip the fetch when** an exact signature, option name or config key matters; the code uses an experimental feature, an adapter, environment variables, hooks or the Vite config; or what you remember disagrees with a reference, or a reference with the docs.
3. **Check the installed version first.** It decides which rules apply (command in the [procedure](#procedure)). These references follow the latest release of each package, so they can lag what is installed: read the changelog window in [changelogs.md](references/changelogs.md) whenever a reference disagrees with what the installed version does, and in the cases that file lists.
4. **Source precedence.** Package changelogs, release notes and source code decide what exists at the installed version; the official docs explain usage, and in any area SvelteKit 3 changed some pages still show SvelteKit 2 code ([known-doc-errata.md](references/known-doc-errata.md)); these references are the starting point and lose to both. When sources conflict, say so in the answer; never pick one silently.
5. **No WebFetch for docs or changelogs**: WebFetch, like any web-fetch tool, returns a truncated summary. Use the MCP tools or `curl`, as the `svelte-docs-and-autofixer` skill says.
6. **Runes mode in Svelte 5.** In a Svelte 5 project, new and changed code uses runes, snippets and event attributes; never mix in legacy syntax. A Svelte 4 project follows rule 7.
7. **Migrate first, then write for the latest.** This plugin is for SvelteKit 3 and Svelte 5. In a project on SvelteKit 2 or Svelte 4, before writing any code, tell the user and propose the migration: SvelteKit 2 to 3 with [migrating-to-kit-3.md](references/kit/migrating-to-kit-3.md), Svelte 4 to 5 with [legacy-and-migration.md](references/svelte/legacy-and-migration.md); the two majors are independent, so migrate only the one that is old. After the migration, work by the current rules. Only if the user declines, write code that works on the installed version (in SvelteKit 2, no `#lib/x.js` imports, `$app/env`, `refreshAll`, `defineParams` or options in `sveltekit({ … })`; in Svelte 4, no runes), never mix versions, and say in the answer that it is old-version code. SvelteKit 1 or Svelte 3 first need the legacy `sv migrate sveltekit-2` or `svelte-4` steps ([sv-cli.md](references/tooling/sv-cli.md)).
8. **Project instructions decide conventions, not APIs.** The project's `CLAUDE.md`, saved memory and team conventions win over this skill on style and structure (naming, file layout, formatting). They never make an API valid that the installed version removed; when one asks for such an API, say so.

## Who does the work

Decide this before the first tool call. In a SvelteKit 2 or Svelte 4 project, settle the migration with the user first (rule 7), and say in the agent's prompt whether they migrated or declined.

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
  description: "Migrate TodoList to Svelte 5"
  prompt: "Migrate src/lib/TodoList.svelte from Svelte 4 to runes mode. Keep its props and events working for its parents …"
```

For an audit, use `subagent_type: "svelte-development:svelte-code-auditor"` and name the scope. Source: https://svelte.dev/docs/ai/subagent and https://svelte.dev/docs/ai/instructions.

## Code rules that training data gets wrong

These apply to Svelte 5 and SvelteKit 3 projects; in older ones, rule 7 decides.

**Runes and reactivity** ([runes.md](references/svelte/runes.md))

- Reactive state is `$state`; a plain `let` that is reassigned does not update the template. Use `$state.raw` for large values that are only reassigned.
- Compute with `$derived`/`$derived.by`, never with `$effect` writing to state. `$effect` is an escape hatch for side effects (DOM, timers, external libraries) and runs only in the browser.
- Props come from `$props()` with a typed destructuring (`let { a, b }: Props = $props();`); `$bindable()` marks a prop as bindable. Passing `count` instead of `() => count` to a function or context captures the current value only.

**Template syntax** ([template-syntax.md](references/svelte/template-syntax.md))

- Events are attributes: `onclick={…}`, not `on:click`. Components take callback props, not `createEventDispatcher`.
- Content is passed as snippets: `{#snippet name()}` and `{@render children?.()}`, not `<slot>`.
- Declaration tags replace `{@const}`: `{const total = $derived(a + b)}` or `{let open = $state(false)}`, anywhere in the template.
- Prefer `{@attach}` over `use:` actions; `fromAction` wraps an existing action.
- Declaration tags and `{@attach}` need a minimum Svelte 5 minor ([template-syntax.md](references/svelte/template-syntax.md) gives it). Below it, keep `{@const}` and `use:`.
- `class` accepts objects and arrays; avoid the `class:` directive in new code.
- Key every `{#each}` with a stable string or number; never key by index or a freshly built array.

**Legacy syntax to remove** ([legacy-and-migration.md](references/svelte/legacy-and-migration.md)): `export let`, `$:`, `$$props`/`$$restProps`, `on:`, `<slot>`/`$$slots`, `<svelte:component>`, `<svelte:self>`, `beforeUpdate`/`afterUpdate`, `spring`/`tweened`, `svelte/legacy`.

**Server and client boundaries** ([security.md](references/kit/security.md), [hooks-errors-and-env.md](references/kit/hooks-errors-and-env.md))

- Secrets only in server code: `$app/env/private` (`$env/static/private` and friends in SvelteKit 2), `+page.server.ts`, `+server.ts`, hooks, and any module whose path has a `server` segment or `server/` directory (server-only everywhere except `src/routes` and `static` since 3.0).
- Universal `load` runs on both sides: nothing private there. Never keep per-user data in module-level variables: they leak between users during server rendering; use `event.locals` or context.
- `{@html}` renders unescaped markup: sanitize anything that came from a user.

**Example: a Svelte 4 component in Svelte 5.** Input:

```svelte
<script>
  import { createEventDispatcher } from 'svelte';
  export let open = false;
  export let title;
  const dispatch = createEventDispatcher();
  $: label = open ? 'Hide' : 'Show';
  function toggle() {
    open = !open;
    dispatch('toggle', open);
  }
</script>

<button on:click={toggle} class:active={open}>{label} {title}</button>
{#if open}<slot />{/if}
```

Output:

```svelte
<script lang="ts">
  import type { Snippet } from 'svelte';
  let { open = $bindable(false), title, ontoggle, children }:
    { open?: boolean; title: string; ontoggle?: (open: boolean) => void; children?: Snippet } = $props();
  const label = $derived(open ? 'Hide' : 'Show');
  function toggle() {
    open = !open;
    ontoggle?.(open);
  }
</script>

<button onclick={toggle} class={[open && 'active']}>{label} {title}</button>
{#if open}{@render children?.()}{/if}
```

Every change follows a rule above: props from `$props()` (`$bindable` because the parent may bind `open`), a computed value with `$derived`, a callback prop instead of the dispatcher, an event attribute, a `class` array instead of `class:`, and the default slot as the `children` snippet. Run the autofixer on the result before handing it back.

## SvelteKit 2 to 3 and experimental features

- **Upgrading a SvelteKit 2 project:** [migrating-to-kit-3.md](references/kit/migrating-to-kit-3.md) has the old-to-new table, the `sv migrate sveltekit-3` codemod and the manual checklist. The changes that break most often: options move into `sveltekit({ … })` in `vite.config`, `$lib` becomes `#lib/…js`, `$app/stores` becomes `$app/state`, `$env/*` becomes `$app/env/*`, and `invalidateAll()` becomes `refreshAll()`.
- **Requirements** (Node, Vite, TypeScript, plugin and adapter majors): [project-and-config.md](references/kit/project-and-config.md) and [adapters-and-deploy.md](references/kit/adapters-and-deploy.md).
- **Experimental features** change between minor releases: fetch the live section before writing any of them (rule 2). `await` in components, async SSR, `fork` and `hydratable` need `compilerOptions.experimental.async` ([async-and-boundaries.md](references/svelte/async-and-boundaries.md)); remote functions need `experimental.remoteFunctions` plus that flag ([forms-and-remote-functions.md](references/kit/forms-and-remote-functions.md)). A SvelteKit 2 project keeps its configuration in `svelte.config.js`, so look the keys up there and in the live section.

## Where things are

Read every reference the task touches, each once: a route with a form action needs `routing.md`, `loading-data.md` and `forms-and-remote-functions.md`. Each opens with its source precedence and ends with the exact calls that fetch its official sections.

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

   pnpm: `pnpm why svelte`; yarn: `yarn why svelte`. When it prints nothing (no `node_modules`, a monorepo), read the ranges in `package.json` and the lockfile; when the version is still unknown, write for Svelte 5 and SvelteKit 3 and say so. Rule 7 decides: on an old major, propose the migration before step 2; and [changelogs.md](references/changelogs.md) says when to read the changelog window. With no project, write for Svelte 5 and SvelteKit 3 and say so in the answer.
2. **References.** Read every reference from [Where things are](#where-things-are) that the task touches; the code rules above apply to every task.
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
