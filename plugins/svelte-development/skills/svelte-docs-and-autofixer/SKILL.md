---
name: svelte-docs-and-autofixer
description: Looks up the current official Svelte, SvelteKit and Svelte CLI documentation and checks Svelte code with the Svelte autofixer, through the Svelte MCP server, with raw-download and optional local command-line fallbacks. Use whenever creating, editing or reviewing a .svelte component or a .svelte.ts/.svelte.js module, when unsure of a rune, template tag, SvelteKit API or configuration option, when the project's Svelte or SvelteKit version is newer than what you remember, or when asked for a Svelte playground link.
license: MIT
metadata:
  upstream: "sveltejs/ai-tools skills/svelte-code-writer"
  base: "6b5d0dab3c9c083387247ab20dc684573481076b"
---

# Svelte docs and autofixer

Svelte 5 and SvelteKit 3 changed APIs that training data still shows the old way. Before writing Svelte code from memory, get the current section; after writing it, run the autofixer until it reports nothing.

## Contents

- [Tools](#tools)
- [Workflow](#workflow)
- [When the MCP server is unavailable](#when-the-mcp-server-is-unavailable)
- [Source precedence](#source-precedence)
- [Gotchas](#gotchas)
- [References](#references)

## Tools

The plugin connects to the Svelte team's remote MCP server, `https://mcp.svelte.dev/mcp`. Claude Code reconnects a remote server on its own when it drops. In Claude Code its tools are named `mcp__plugin_svelte-development_svelte__<tool>`; they may be deferred, so load them with ToolSearch before concluding they are missing.

| Tool | Does | What leaves the machine |
|---|---|---|
| `list-sections` | Lists every documentation section with its `path` (203 on 2026-10-05) and a use-case hint | The request only |
| `get-documentation` | Returns the full text of one or more sections, by `path` (`kit/load`) or exact title | The section names |
| `svelte-autofixer` | Compiles the code and returns `issues`, `suggestions` and `require_another_tool_call_after_fixing` | **The code you pass** (Svelte states it does not log, store or inspect it) |
| `playground-link` | Builds a svelte.dev playground URL for the given files | The files you pass; the code lives only in the URL |

The remote server records usage events (tool name, session and client). Every call needs network access.

The server also offers two things the **user** starts, not the model:

- **Resources (`doc-section`)**: every documentation section as `svelte://<slug>.md`, returning that page's `llms.txt` text. The user includes one in a prompt by typing `@` and picking it from the autocomplete, for example the transition docs before asking for an animated component. When a user mentions wanting a page "in context", tell them they can attach it this way; you fetch the same content yourself with `get-documentation`.
- **Prompt `svelte-task`**: takes a `task` argument and injects instructions plus the section list for it. The user runs it from the `/` menu, where Claude Code lists it as an MCP prompt.

Source: https://svelte.dev/docs/ai/resources, https://svelte.dev/docs/ai/prompts and https://code.claude.com/docs/en/mcp (resources and prompts).

## Workflow

For a change to `.svelte`, `.svelte.ts` or `.svelte.js` files, prefer delegating to the `svelte-development:svelte-component-editor` agent, which runs this workflow in its own context. Run it inline only for small changes, when the user asks, or when you already are that agent. Copy this checklist for any Svelte code change:

```
- [ ] 1 Find      pick sections from the docs map (or list-sections); never guess a path
- [ ] 2 Read      get-documentation with every section the change touches, in one call
- [ ] 3 Write     write or edit the code from what the sections say
- [ ] 4 Fix       svelte-autofixer on the result; apply issues and suggestions
- [ ] 5 Repeat    re-run step 4 while require_another_tool_call_after_fixing is true or issues remain
- [ ] 6 Verify    LSP diagnostics and sv check (svelte-lsp-navigation skill)
```

- **Section names.** Pass the `path` exactly as `list-sections` prints it, without a leading `docs/`: `svelte/$state`, `kit/load`, `cli/sv-migrate`. An exact title also works (`Migrating to SvelteKit v3`). A `docs/kit/…` path returns only "similar results". The classified map of all sections is `${CLAUDE_PLUGIN_ROOT}/skills/svelte-best-practices/references/docs-map.md`.
- **Autofixer input.** Pass the full component code as `code`, with `filename`, `desired_svelte_version` 5 and `async: true` when the project enables `experimental.async`. Never pass a file path: the remote server treats it as code and answers "no issues" (observed on 2026-10-05). It reports Svelte compiler errors and Svelte-specific mistakes (legacy syntax, effects that should be derived values, runes misuse); type errors come from the language server, not from it.
- **Done** when the autofixer returns no issues and `require_another_tool_call_after_fixing` is false, and the language server and `sv check` report nothing new.
- **Playground links.** Offer one only for code you answered in the chat, after the user says yes; never for code written to the project's files. The code lives only in the URL, which is therefore long. Source: https://svelte.dev/docs/ai/instructions and https://svelte.dev/docs/ai/tools.

## When the MCP server is unavailable

1. **Retry.** The server may be reconnecting; the user can run `/mcp reconnect all`. Say that the documentation could not be checked.
2. **Raw download.** `curl -sS https://svelte.dev/docs/<area>/<slug>/llms.txt`, for example `https://svelte.dev/docs/kit/load/llms.txt`, then filter with `grep -n` or `sed -n`. Never summarize the docs through a web-fetch tool: it truncates.
3. **Local command line, if the user has it.** `@sveltejs/mcp` installed globally (`npm install -g @sveltejs/mcp`) gives `svelte-mcp list-sections`, `svelte-mcp get-documentation '<path>,<path>'` and `svelte-mcp svelte-autofixer <file path or code> [--async] [--svelte-version 5]`. Its autofixer runs on the user's machine, sends no code and reads file paths; offer it when the user does not want code sent to the remote server or works offline. Quote inline code in single quotes, because in double quotes the shell expands `$state`. Do not install it, or run it through `npx`, without the user's confirmation.

## Source precedence

The Svelte docs are current but not always right: a few pages still show SvelteKit 2 code. When sources disagree:

1. The package changelog, release notes and source code decide what exists at the project's version.
2. The official docs explain usage; check them against item 1 when they touch a changed area.
3. The `svelte-best-practices` references are the starting point and lose to both.

Say so in the answer when two sources conflict; never pick one silently. Known conflicts: `${CLAUDE_PLUGIN_ROOT}/skills/svelte-best-practices/references/known-doc-errata.md`. Changelog procedure and URLs: `${CLAUDE_PLUGIN_ROOT}/skills/svelte-best-practices/references/changelogs.md`.

## Gotchas

- **Everything needs network.** Offline, every tool fails; the local command line above is the only autofixer that works then.
- **A file path is not code.** The remote autofixer reports a path string as clean code; always pass the file's content.
- **`list-sections` hints are missing for the newest sections**, including every SvelteKit 3 addition and declaration tags ("use title and path to estimate use case"). The docs map classifies them.
- **The autofixer passing is not proof the code is right.** It does not type-check, does not know SvelteKit routing rules and does not run the code.

## References

- `${CLAUDE_PLUGIN_ROOT}/skills/svelte-best-practices/references/docs-map.md`: read when choosing sections; every section classified by area with its `get-documentation` path and raw URL.
- `${CLAUDE_PLUGIN_ROOT}/skills/svelte-best-practices/references/changelogs.md`: read when the project's version is newer than a reference's "Verified against" line.

Derived from the `svelte-code-writer` skill of sveltejs/ai-tools (MIT), base `6b5d0da`; see the plugin NOTICE. Sources: runtime output of the remote server and of the `@sveltejs/mcp` 0.1.26 command line (2026-10-05), https://svelte.dev/docs/ai/llms.txt, https://code.claude.com/docs/en/mcp (automatic reconnection).
