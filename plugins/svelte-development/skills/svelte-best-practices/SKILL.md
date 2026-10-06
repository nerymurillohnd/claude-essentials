---
name: svelte-best-practices
description: The Svelte 5 and SvelteKit 3 rules that training data gets wrong - runes, snippets, event attributes, declaration tags, SvelteKit 3 imports, config, environment variables, routing, loading, forms, remote functions, hooks, adapters and security - plus the Svelte CLI (sv), Astro with Svelte islands and Tailwind CSS 4, with one reference per topic. Use before writing, converting, migrating, reviewing or explaining any Svelte or SvelteKit code, including a component pasted in the chat.
when_to_use: Triggers include a .svelte file or snippet, "convert to Svelte 5", "migrate from Svelte 4" or "upgrade to SvelteKit 3", code with export let, $:, on:click, <slot> or createEventDispatcher, a SvelteKit route, load function, hook, form action or vite.config, sv create, sv add or sv migrate, and Svelte with Astro or Tailwind CSS.
license: MIT
metadata:
  upstream: "sveltejs/ai-tools skills/svelte-core-bestpractices"
  base: "6b5d0dab3c9c083387247ab20dc684573481076b"
---

# Svelte 5 and SvelteKit 3 best practices

This skill is the contract for writing Svelte by the current rules. Target versions: **svelte 5.57.1** and **@sveltejs/kit 3.0.0** (2026-10-01). Most Svelte and SvelteKit code in training data is Svelte 4 or SvelteKit 2; the rules below are where it goes wrong, and each topic has a reference with the foundations, short examples and the exact official sections to fetch.

## Contents

- [When to use it](#when-to-use-it)
- [Rules for working](#rules-for-working)
- [Who does the work](#who-does-the-work)
- [Where things are](#where-things-are)
- [Procedure](#procedure)
- [Code rules that training data gets wrong](#code-rules-that-training-data-gets-wrong)
- [SvelteKit 2 to 3: what changed](#sveltekit-2-to-3-what-changed)
- [Experimental features](#experimental-features)

## When to use it

| Use it | Do not use it |
|---|---|
| Writing, converting or reviewing Svelte components, `.svelte.ts`/`.svelte.js` modules or SvelteKit files | For where a symbol of the project is used: that is the `svelte-lsp-navigation` skill |
| Migrating from Svelte 4 or SvelteKit 2 | For React, Vue, plain TypeScript or other non-Svelte code |
| Setting up a project with `sv`, or Svelte with Astro or Tailwind CSS | |
| Explaining how something is done in Svelte 5 or SvelteKit 3 | |

## Rules for working

These rules hold for every later turn of the task, not only the turn that loaded this skill.

1. **Never write Svelte from memory alone.** Read the reference for the topic, then fetch the live sections with the `svelte-docs-and-autofixer` skill before writing, and run the autofixer after.
2. **Fetch the live section before writing when** an exact signature, option name or config key matters; the code uses an experimental feature, an adapter, environment variables, hooks or the Vite config; the project's installed version is newer than the reference's "Verified against" line; or what you remember disagrees with a reference, or a reference with the docs.
3. **Check the installed version first.** It decides which rules apply (command in the [procedure](#procedure)). When it is newer than a reference's "Verified against" line, read the changelog window in [changelogs.md](references/changelogs.md) before relying on that reference.
4. **Source precedence.** Package changelogs, release notes and source code decide what exists at the installed version; the official docs explain usage, and in any area SvelteKit 3 changed some pages still show SvelteKit 2 code ([known-doc-errata.md](references/known-doc-errata.md)); these references are the starting point and lose to both. When sources conflict, say so in the answer; never pick one silently.
5. **No WebFetch for docs or changelogs.** WebFetch, like any web-fetch tool, returns a truncated summary. Use the MCP tools or `curl` for the raw text.
6. **Runes mode only.** New and changed code uses runes, snippets and event attributes; never mix in legacy syntax.

## Who does the work

Decide this before the first tool call.

| Situation | Who | How |
|---|---|---|
| A question, an explanation, a review or conversion of code pasted in the chat, or a change of one or two lines | You | Follow the [procedure](#procedure) inline |
| Creating, editing, refactoring or migrating `.svelte`, `.svelte.ts`, `.svelte.js` or SvelteKit route files beyond a line or two | `svelte-component-editor` agent | Delegate with the Agent tool (below) |
| Reviewing, auditing or checking a codebase, a pull request or a migration without changing it | `svelte-code-auditor` agent | Delegate with the Agent tool (below) |
| The user asks you to work inline, or you already are one of these agents | You | Never delegate further |

The documentation lookups and the autofixer loop then run in the agent's context instead of filling the main conversation. The agent starts without this conversation, so its prompt names the files, the task, the constraints and what to report:

```text
Agent
  subagent_type: "svelte-development:svelte-component-editor"
  description: "Migrate TodoList to Svelte 5"
  prompt: "Migrate src/lib/TodoList.svelte from Svelte 4 to runes mode. Keep its props and events working for its parents …"
```

For an audit, use `subagent_type: "svelte-development:svelte-code-auditor"` and name the scope. Source: https://svelte.dev/docs/ai/subagent and https://svelte.dev/docs/ai/instructions.

## Where things are

Read the one reference that matches the task; each opens with its "Verified against" line and ends with the exact calls that fetch its official sections.

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
| [integrations/astro.md](references/integrations/astro.md) | Svelte components inside an Astro 7 site |
| [integrations/tailwind.md](references/integrations/tailwind.md) | Tailwind CSS 4 with SvelteKit or Astro |
| [docs-map.md](references/docs-map.md) | Choosing which official section to fetch |
| [changelogs.md](references/changelogs.md) | The project's version is newer than a reference, or behaviour differs from the docs |
| [known-doc-errata.md](references/known-doc-errata.md) | Before copying a docs example in an area SvelteKit 3 changed |

## Procedure

Run these steps in order for any Svelte code you write, convert or review.

1. **Installed versions**, in a project (skip for code pasted in the chat with no project):

   ```sh
   npm ls svelte @sveltejs/kit --depth=0
   ```

   pnpm: `pnpm why svelte`; yarn: `yarn why svelte`. If a version is newer than the reference's "Verified against" line, run the changelog window check in [changelogs.md](references/changelogs.md).
2. **Reference.** Read the reference from [Where things are](#where-things-are) that matches the task, and the code rules below.
3. **Live sections**, in one call, with the paths from the reference's "Official sources" or the docs map:

   ```text
   mcp__plugin_svelte-development_svelte__get-documentation
     section: ["svelte/$props", "svelte/snippet", "svelte/v5-migration-guide"]
   ```

   If the tool is deferred, load it with ToolSearch (`select:mcp__plugin_svelte-development_svelte__get-documentation`); if the server is unavailable, follow the fallbacks in the `svelte-docs-and-autofixer` skill.
4. **Write** the code by the rules and the sections.
5. **Autofix** the full code with `mcp__plugin_svelte-development_svelte__svelte-autofixer` (`code`, `desired_svelte_version: 5`, `filename`) until it reports no issues, as the `svelte-docs-and-autofixer` skill says.
6. **Check**, in a project: the language server diagnostics and the project's checker (`npm run check`), as the `svelte-lsp-navigation` skill says.

## Code rules that training data gets wrong

**Runes and reactivity** ([runes.md](references/svelte/runes.md))

- Reactive state is `$state`; a plain `let` that is reassigned does not update the template. Use `$state.raw` for large values that are only reassigned.
- Compute with `$derived`/`$derived.by`, never with `$effect` writing to state. `$effect` is an escape hatch for side effects (DOM, timers, external libraries) and runs only in the browser.
- Props come from `$props()` with a typed destructuring (`let { a, b }: Props = $props();`); `$bindable()` marks a prop as bindable. Passing `count` instead of `() => count` to a function or context captures the current value only.

**Template syntax** ([template-syntax.md](references/svelte/template-syntax.md))

- Events are attributes: `onclick={…}`, not `on:click`. Components take callback props, not `createEventDispatcher`.
- Content is passed as snippets: `{#snippet name()}` and `{@render children?.()}`, not `<slot>`.
- `{@const}` is legacy since 5.56: use declaration tags, `{const total = $derived(a + b)}` or `{let open = $state(false)}`, anywhere in the template.
- Prefer `{@attach}` (5.29) over `use:` actions; `fromAction` wraps an existing action.
- `class` accepts objects and arrays (5.16); avoid the `class:` directive in new code.
- Key every `{#each}` with a stable string or number; never key by index or a freshly built array.

**Legacy syntax to remove** ([legacy-and-migration.md](references/svelte/legacy-and-migration.md)): `export let`, `$:`, `$$props`/`$$restProps`, `on:`, `<slot>`/`$$slots`, `<svelte:component>`, `<svelte:self>`, `beforeUpdate`/`afterUpdate`, `spring`/`tweened`, `svelte/legacy`.

**Server and client boundaries** ([security.md](references/kit/security.md), [hooks-errors-and-env.md](references/kit/hooks-errors-and-env.md))

- Secrets only in server code: `$app/env/private`, `+page.server.ts`, `+server.ts`, hooks, and any module whose path has a `server` segment or `server/` directory (server-only everywhere except `src/routes` and `static` since 3.0).
- Universal `load` runs on both sides: nothing private there. Never keep per-user data in module-level variables: they leak between users during server rendering; use `event.locals` or context.
- `{@html}` renders unescaped markup: sanitize anything that came from a user.

## SvelteKit 2 to 3: what changed

Full table and the `sv migrate sveltekit-3` codemod: [migrating-to-kit-3.md](references/kit/migrating-to-kit-3.md). The changes that break most often:

| SvelteKit 2 | SvelteKit 3 |
| --- | --- |
| `svelte.config.js` | Options in `sveltekit({ … })` in `vite.config.ts`; a leftover `svelte.config.js` is silently ignored |
| `import x from '$lib/x'` | `import x from '#lib/x.js'` with `"imports": { "#lib": …, "#lib/*": "./src/lib/*" }` in `package.json`; the extension is required |
| `$app/stores` (`$page`) | `$app/state` (`page`), removed in 3.0 |
| `$env/static/private` and friends | `$app/env/private` / `$app/env/public` with `defineEnvVars` in `src/env.ts` (`$env/*` deprecated) |
| `$app/environment` | `$app/env` |
| `invalidateAll()` | `refreshAll()` |
| `goto(url, { noScroll, keepFocus, replaceState })` | `goto(url, { reset, replace })`; `goto` rejects URLs outside the app |
| `base`, `assets`, `resolveRoute` from `$app/paths` | `resolve('blog/x')`, `asset('x.png')` (no leading slash) |
| `src/params/*.ts` matchers | One `src/params.ts`: `export const params = defineParams({ … })` from `@sveltejs/kit/params` |
| `error(404, { message })` | `error(404, 'Not found', { … })` |
| `json()` / `text()` | `Response.json()` / `new Response()` |
| `csrf.checkOrigin`, `prerender.origin`, adapter-node `ORIGIN` | `csrf.trustedOrigins`, `paths.origin` |
| `$service-worker` | `$app/env` (`version`), `$app/manifest`, `$app/paths` |

Requirements: Node 22.17+, Vite 8 (`^8.0.12`), Svelte `^5.57.1`, TypeScript 6 when TypeScript is used, `@sveltejs/vite-plugin-svelte` 7, and the 3.0 adapter majors (auto 8, node 6, static 4, cloudflare 8, vercel 7, netlify 7, bun 1).

## Experimental features

They change between minor releases: fetch the live section before writing any of them (rule 2).

| Feature | Enable |
| --- | --- |
| `await` in components, `$effect.pending`, async SSR, `fork`, `hydratable` | `compilerOptions.experimental.async` (in `sveltekit({ compilerOptions })`); `fork` and `hydratable` throw `experimental_async_required` without it |
| Remote functions (`query`, `query.batch`, `query.live`, `form`, `command`, `prerender`) | `experimental.remoteFunctions` in `sveltekit({ … })` plus the async flag above; `*.remote.ts` files error without it |
| Fork preloads | `experimental.forkPreloads` |

Details: [async-and-boundaries.md](references/svelte/async-and-boundaries.md) and [forms-and-remote-functions.md](references/kit/forms-and-remote-functions.md).

Derived from the `svelte-core-bestpractices` skill of sveltejs/ai-tools (MIT), base `6b5d0da`, and extended; see the plugin NOTICE. Not affiliated with or endorsed by the Svelte project.
