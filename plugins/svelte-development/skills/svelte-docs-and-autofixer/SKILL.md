---
name: svelte-docs-and-autofixer
description: Looks up the current official Svelte, SvelteKit and Svelte CLI docs and checks Svelte code with the Svelte autofixer, through this plugin's Svelte MCP tools (get-documentation, svelte-autofixer), with raw-download and local command-line fallbacks. Use whenever Svelte code is written, changed or checked for problems, including a component pasted in the chat, and whenever an exact Svelte or SvelteKit API, rune, option or signature matters.
when_to_use: Triggers include "is anything wrong with this component", "check this Svelte code", "how do I … in Svelte 5", "what is the SvelteKit 3 way to", "is this API current", a request for a Svelte playground link, and any reply that will contain Svelte code.
license: MIT
metadata:
  upstream: "sveltejs/ai-tools skills/svelte-code-writer"
  base: "6b5d0dab3c9c083387247ab20dc684573481076b"
---

# Svelte docs and autofixer

This skill is the contract for two jobs: reading the current official Svelte docs before writing, and proving Svelte code with the Svelte autofixer after writing. Svelte 5 and SvelteKit 3 changed APIs that training data still shows the old way, so neither job is done from memory.

## Contents

- [When to use it](#when-to-use-it)
- [Rules](#rules)
- [Who does the work](#who-does-the-work)
- [Where things are](#where-things-are)
- [Tools](#tools)
- [Procedure](#procedure)
- [When the MCP server is unavailable](#when-the-mcp-server-is-unavailable)
- [What the user can start](#what-the-user-can-start)

## When to use it

| Use it | Do not use it |
|---|---|
| Before writing or changing any `.svelte`, `.svelte.ts` or `.svelte.js` code, or replying with Svelte code | For where a symbol of the project is defined or used: that is the `svelte-lsp-navigation` skill |
| When asked whether Svelte code has problems, including code pasted in the chat | For a whole-project type check: that is the project check (`svelte-lsp-navigation`) |
| When an exact rune, template tag, SvelteKit API, option or config key matters | For React, Vue, plain TypeScript or other non-Svelte code |
| When the project's Svelte or SvelteKit version is newer than what you remember | |

## Rules

These rules hold for every later turn of the task, not only the turn that loaded this skill. The short tool names (`get-documentation`, `svelte-autofixer`, `list-sections`, `playground-link`) stand for their full names, `mcp__plugin_svelte-development_svelte__<tool>`; always call the full name.

1. **Docs before code, by default.** Fetch the sections a change touches with `get-documentation` before writing it. Skip the fetch only when the change uses no Svelte or SvelteKit API, such as copy, CSS values or markup text. Never guess a section path: take it from the docs map.
2. **Autofixer after code.** Run `svelte-autofixer` on every component or module you wrote or reviewed, and repeat until it returns no issues and `require_another_tool_call_after_fixing` is false. After each `Write` or `Edit` of a Svelte file, the plugin adds a note next to the tool result saying the autofixer has not checked the new content: that note marks the file as unchecked until you run step 4 of the procedure on it.
3. **Pass code, never a path.** The remote autofixer treats a file path as code and answers "no issues" (observed on 2026-10-05). Read the file and pass its full content as `code`; `filename` is the bare file name (`Counter.svelte`), never a path.
4. **The autofixer is not proof.** It does not type-check, does not know SvelteKit routing rules and does not run the code. Type errors come from the language server and the project check.
5. **No WebFetch for docs.** WebFetch, like any web-fetch tool, returns a truncated summary. Use the MCP tools, or `curl` for the raw text.
6. **Source precedence.** Package changelogs, release notes and source code decide what exists at the project's version; the official docs explain usage; the `svelte-best-practices` references are the starting point and lose to both. When two sources disagree, say so in the answer; never pick one silently. The live docs describe the newest Svelte and SvelteKit: in a project on an older major (SvelteKit 2, Svelte 4), check each API against the installed version before using it.
7. **Playground links only on request.** Offer one only for code answered in the chat, and call `playground-link` only after the user says yes; never for code written to the project's files.
8. **Network and privacy.** Every MCP call needs network access. `svelte-autofixer` sends the code you pass to the Svelte team's server (Svelte states it does not log, store or inspect it); when the user does not want code to leave the machine, use the local command line below.
9. **No installs without consent.** Never install `@sveltejs/mcp` or run it through `npx` without the user's confirmation.

## Who does the work

Decide this before the first tool call.

| Situation | Who | How |
|---|---|---|
| A question about an API, a review of code pasted in the chat, or a change of one or two lines | You | Follow the [procedure](#procedure) inline |
| Creating, editing or refactoring `.svelte`, `.svelte.ts`, `.svelte.js` or SvelteKit route files beyond a line or two | `svelte-component-editor` agent | Delegate with the Agent tool (below) |
| Reviewing, auditing or checking project files without changing them | `svelte-code-auditor` agent | Delegate with the Agent tool (below) |
| The user asks you to work inline, or you already are one of these agents | You | Never delegate further |

The agent starts without this conversation: its prompt must name the files, the task, the constraints and what to report.

```text
Agent
  subagent_type: "svelte-development:svelte-component-editor"
  description: "Add a bindable value prop"
  prompt: "In src/lib/components/Counter.svelte, add a bindable `value` prop with default 0 …"
```

For an audit, use `subagent_type: "svelte-development:svelte-code-auditor"` and name the scope (files, a directory or a diff).

## Where things are

- `${CLAUDE_PLUGIN_ROOT}/skills/svelte-best-practices/references/docs-map.md`: every documentation section classified by area, with its `get-documentation` path and raw URL. Read it to choose sections.
- `${CLAUDE_PLUGIN_ROOT}/skills/svelte-best-practices/references/changelogs.md`: the commands that read the changelog window when the project's version is newer than a reference's "Verified against" line.
- `${CLAUDE_PLUGIN_ROOT}/skills/svelte-best-practices/references/known-doc-errata.md`: pages that still show SvelteKit 2 code, and what is right.
- The `svelte-best-practices` skill: the Svelte 5 and SvelteKit 3 rules to write by. The `svelte-lsp-navigation` skill: language server diagnostics and the project check.

The sibling skills (`svelte-best-practices`, `svelte-lsp-navigation`) are named `svelte-development:<skill>`. When a step needs one that is not loaded yet, load it with the Skill tool:

```text
Skill
  skill: "svelte-development:svelte-best-practices"
```

## Tools

The plugin connects to the Svelte team's remote MCP server, `https://mcp.svelte.dev/mcp`; Claude Code reconnects it on its own when it drops. The tools are named `mcp__plugin_svelte-development_svelte__<tool>`. They may be deferred: if they are not in your tool list, load them before concluding they are missing:

```text
ToolSearch
  query: "select:mcp__plugin_svelte-development_svelte__get-documentation,mcp__plugin_svelte-development_svelte__svelte-autofixer,mcp__plugin_svelte-development_svelte__list-sections"
```

| Tool | Input | Returns |
|---|---|---|
| `mcp__plugin_svelte-development_svelte__list-sections` | none | Every section with its `path` (203 on 2026-10-05) and a use-case hint |
| `mcp__plugin_svelte-development_svelte__get-documentation` | `section`: one path or title, or an array of them | The full text of each section |
| `mcp__plugin_svelte-development_svelte__svelte-autofixer` | `code` (required), `desired_svelte_version` (required, `5`), `filename`, `async` | `issues`, `suggestions`, `require_another_tool_call_after_fixing` |
| `mcp__plugin_svelte-development_svelte__playground-link` | `name`, `tailwind`, `files` (`{ "App.svelte": "<code>" }`) | A svelte.dev playground URL holding the code |

Section paths are written exactly as `list-sections` prints them, without a leading `docs/`: `svelte/$state`, `kit/load`, `cli/sv-migrate`. An exact title also works (`Migrating to SvelteKit v3`). A `docs/kit/…` path returns only "similar results". The `list-sections` hints are missing for the newest sections, including every SvelteKit 3 addition and declaration tags; the docs map classifies them.

## Procedure

Copy this checklist for any Svelte code you write, change or review, and run the calls in this order.

```
- [ ] 1 Find      choose the sections in docs-map.md; call list-sections only for a topic the map lacks
- [ ] 2 Read      one get-documentation call with every section the code touches
- [ ] 3 Write     write or edit the code from what the sections say
- [ ] 4 Fix       svelte-autofixer on the full code; apply issues and suggestions
- [ ] 5 Repeat    step 4 until no issues and require_another_tool_call_after_fixing is false
- [ ] 6 Verify    language server diagnostics and the project check (svelte-lsp-navigation)
```

**Step 2, read the sections in one call:**

```text
mcp__plugin_svelte-development_svelte__get-documentation
  section: ["svelte/$props", "svelte/$bindable"]
```

**Step 4, check the code.** Pass the whole component as `code`; set `async: true` only when the project enables `compilerOptions.experimental.async`:

```text
mcp__plugin_svelte-development_svelte__svelte-autofixer
  code: "<script lang=\"ts\">\n  let { value = $bindable(0) }: { value?: number } = $props();\n</script>\n…"
  desired_svelte_version: 5
  filename: "Counter.svelte"
```

It reports Svelte compiler errors and Svelte-specific mistakes: legacy syntax, effects that should be derived values, runes misuse.

**Step 6, verify.** Read the diagnostics Claude Code reports after each edit of a `.svelte` file, then run the project check from the project root, as the `svelte-lsp-navigation` skill describes:

```sh
npm run check
```

**Done** when the autofixer returns no issues with `require_another_tool_call_after_fixing` false, and the language server and the project check report nothing new.

**Playground link**, only after the user said yes:

```text
mcp__plugin_svelte-development_svelte__playground-link
  name: "Bindable counter"
  tailwind: false
  files: { "App.svelte": "<the code from the answer>" }
```

## When the MCP server is unavailable

Try these in order, and say in the answer that the documentation or the code could not be checked through the server.

1. **Retry once.** The server may be reconnecting. The user can run `/mcp reconnect all`.
2. **Raw download of the docs.** Fetch the section's text and filter it:

   ```sh
   curl -sS https://svelte.dev/docs/kit/load/llms.txt | grep -n 'depends'
   ```

   The URL pattern is `https://svelte.dev/docs/<area>/<slug>/llms.txt`; the docs map lists it for every section.
3. **Local command line, if the user has it.** `@sveltejs/mcp`, installed globally by the user, runs on their machine, sends no code and reads file paths. Use it offline or when code must not leave the machine. Quote inline code in single quotes, because double quotes let the shell expand `$state`:

   ```sh
   command -v svelte-mcp                                         # installed?
   svelte-mcp list-sections
   svelte-mcp get-documentation 'svelte/$props,svelte/$bindable'
   svelte-mcp svelte-autofixer src/lib/components/Counter.svelte --svelte-version 5
   ```

   If it is missing, the user installs it with `npm install -g @sveltejs/mcp`; ask before suggesting `npx`.

## What the user can start

The server also offers two things the user starts, not the model:

- **Resources (`doc-section`)**: every section as `svelte://<slug>.md`. The user attaches one by typing `@` and picking it, for example the transition docs before asking for an animated component. When a user wants a page "in context", tell them they can attach it this way; you fetch the same content with `get-documentation`.
- **Prompt `svelte-task`**: takes a `task` argument and injects instructions plus the section list for it; the user runs it from the `/` menu.

Derived from the `svelte-code-writer` skill of sveltejs/ai-tools (MIT), base `6b5d0da`; see the plugin NOTICE. Sources: the remote server's `tools/list` schemas and runtime output, and the `@sveltejs/mcp` 0.1.26 command line (2026-10-05); https://svelte.dev/docs/ai/llms.txt, https://svelte.dev/docs/ai/resources, https://svelte.dev/docs/ai/prompts; https://code.claude.com/docs/en/mcp and https://code.claude.com/docs/en/plugins-reference (plugin agents are named `<plugin>:<agent>`).
