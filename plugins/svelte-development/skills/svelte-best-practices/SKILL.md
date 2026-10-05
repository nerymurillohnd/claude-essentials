---
name: svelte-best-practices
description: Current rules, APIs and pitfalls for writing, reviewing and migrating Svelte 5 and SvelteKit 3 code - runes, template syntax, async and boundaries, routing, loading, form actions, remote functions, hooks, environment variables, adapters and security - plus the Svelte CLI (sv), Astro with Svelte islands and Tailwind CSS 4. Use when writing or changing a .svelte component, a .svelte.ts/.svelte.js module, a SvelteKit route, hook, load function or vite.config, when migrating from Svelte 4 or SvelteKit 2, when setting up a project with sv, or when combining Svelte with Astro or Tailwind CSS.
license: MIT
metadata:
  upstream: "sveltejs/ai-tools skills/svelte-core-bestpractices"
  base: "6b5d0dab3c9c083387247ab20dc684573481076b"
---

# Svelte 5 and SvelteKit 3 best practices

Target versions: **svelte 5.57.1** and **@sveltejs/kit 3.0.0** (2026-10-01). Most Svelte and SvelteKit code in training data is Svelte 4 or SvelteKit 2: the rules below are where it goes wrong. Each topic has a reference with the foundations, short examples and the exact official sections to fetch.

## Contents

- [Delegate Svelte file work](#delegate-svelte-file-work)
- [Source precedence](#source-precedence)
- [Rules that training data gets wrong](#rules-that-training-data-gets-wrong)
- [SvelteKit 2 to 3: what changed](#sveltekit-2-to-3-what-changed)
- [Experimental features](#experimental-features)
- [Fetch before writing when](#fetch-before-writing-when)
- [References](#references)

## Delegate Svelte file work

When creating or editing `.svelte` files or `.svelte.ts`/`.svelte.js` modules, delegate the change to the `svelte-development:svelte-component-editor` agent, and audits to `svelte-development:svelte-code-auditor`. The documentation lookups and the autofixer loop then run in the agent's own context instead of filling the main conversation. Work inline only for a one-line change, when the user asks you to, or when you already are one of these agents. Source: https://svelte.dev/docs/ai/subagent and https://svelte.dev/docs/ai/instructions.

## Source precedence

1. The package **changelog, release notes and source code** decide what exists at the project's installed version.
2. The **official docs** (`get-documentation` through the Svelte MCP server, or `curl -sS https://svelte.dev/docs/<area>/<slug>/llms.txt`) explain usage; check them against item 1 in any area SvelteKit 3 changed, because some pages still show SvelteKit 2 code ([known-doc-errata.md](references/known-doc-errata.md)).
3. **These references** are the starting point and lose to both.

When sources conflict, say so in the answer instead of picking one silently. When the project's installed version (`package.json`, the lockfile or `npm ls <pkg>`) is newer than a reference's "Verified against" line, run the check in [changelogs.md](references/changelogs.md) before relying on it. Never summarize docs through a web-fetch tool: it truncates; use the MCP server or `curl`.

## Rules that training data gets wrong

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

**Legacy syntax to remove** ([legacy-and-migration.md](references/svelte/legacy-and-migration.md)): `export let`, `$:`, `$$props`/`$$restProps`, `on:`, `<slot>`/`$$slots`, `<svelte:component>`, `<svelte:self>`, `beforeUpdate`/`afterUpdate`, `spring`/`tweened`, `svelte/legacy`. Use runes mode for the project.

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

They change between minor releases; fetch the live section before writing any of them.

| Feature | Enable |
| --- | --- |
| `await` in components, `$effect.pending`, async SSR, `fork`, `hydratable` | `compilerOptions.experimental.async` (in `sveltekit({ compilerOptions })`); `fork` and `hydratable` throw `experimental_async_required` without it |
| Remote functions (`query`, `query.batch`, `query.live`, `form`, `command`, `prerender`) | `experimental.remoteFunctions` in `sveltekit({ … })` plus the async flag above; `*.remote.ts` files error without it |
| Fork preloads | `experimental.forkPreloads` |

Details: [async-and-boundaries.md](references/svelte/async-and-boundaries.md) and [forms-and-remote-functions.md](references/kit/forms-and-remote-functions.md).

## Fetch before writing when

- An exact signature, option name or config key matters.
- The code uses an experimental feature, an adapter, environment variables, hooks or the Vite config.
- The project's installed version is newer than the reference you read.
- What you remember disagrees with a reference, or a reference disagrees with the docs.

Then: the `svelte-docs-and-autofixer` skill (MCP `get-documentation`, then `svelte-autofixer`), the section paths in [docs-map.md](references/docs-map.md), and [changelogs.md](references/changelogs.md) for the version window.

## References

Read the one that matches the task; each opens with its contents and ends with the official sections to fetch.

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

Derived from the `svelte-core-bestpractices` skill of sveltejs/ai-tools (MIT), base `6b5d0da`, and extended; see the plugin NOTICE. Not affiliated with or endorsed by the Svelte project.
