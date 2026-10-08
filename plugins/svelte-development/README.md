# Svelte Development

<!-- BEGIN GENERATED: header -->

[![version: 0.3.1](https://img.shields.io/badge/version-0.3.1-blue)](CHANGELOG.md) [![category: development](https://img.shields.io/badge/category-development-informational)](https://github.com/nerymurillohnd/claude-essentials/blob/main/README.md#categories) [![Claude Code: ≥ 2.1.289](https://img.shields.io/badge/Claude%20Code-%E2%89%A5%202.1.289-orange)](https://code.claude.com/docs) [![license: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE) [![CI](https://github.com/nerymurillohnd/claude-essentials/actions/workflows/validate.yml/badge.svg)](https://github.com/nerymurillohnd/claude-essentials/actions/workflows/validate.yml) [![skills: 3](https://img.shields.io/badge/skills-3-blueviolet)](#-components) [![agents: 2](https://img.shields.io/badge/agents-2-blueviolet)](#-components) [![hooks: 3](https://img.shields.io/badge/hooks-3-blueviolet)](#-components) [![mcp servers: 1](https://img.shields.io/badge/mcp%20servers-1-blueviolet)](#-components) [![lsp servers: 1](https://img.shields.io/badge/lsp%20servers-1-blueviolet)](#-components) [![runs code: yes, reviewed](https://img.shields.io/badge/runs%20code-yes%2C%20reviewed-yellow)](#-permissions)

Svelte 5 and SvelteKit 3 development, with a guided migration for SvelteKit 2 and Svelte 4 projects: current best practices, docs lookup and autofixer, language-server navigation with renames proven by the project check, an editor and an auditor agent, a svelte-check of your changes before Claude stops, and the Svelte MCP and language servers, built on the Svelte team's AI tools.

Part of [Claude Essentials](https://github.com/nerymurillohnd/claude-essentials), an independent community plugin marketplace for Claude Code. Not affiliated with or endorsed by Anthropic.

**Contents:** [Overview](#-overview) · [What it does](#-what-it-does) · [Prerequisites](#-prerequisites) · [Installation](#-installation) · [Usage](#-usage) · [Components](#-components) · [Permissions](#-permissions) · [FAQ](#-faq) · [Update and uninstall](#-update-and-uninstall) · [Documentation](#-documentation) · [License](#-license)

<!-- END GENERATED: header -->

## 📖 Overview

Most Svelte code a model has seen is Svelte 4 and SvelteKit 2, so it writes `export let`, `on:click` and `$app/stores` into projects that run Svelte 5 and SvelteKit 3. This plugin gives Claude the current rules instead, and makes it prove every change.

> **For you if** you build with Svelte, SvelteKit, Astro islands or Tailwind CSS 4 in Claude Code — on Svelte 5 and SvelteKit 3, or still on Svelte 4 and SvelteKit 2.

**What it changes in Claude's habits**

- 📚 **Reads the docs first.** The official documentation and the changelogs, before writing, not after.
- 🧪 **Proves each change.** Svelte autofixer → language server → your project's own check, until all three are clean.
- 🏷️ **Latest by default.** Claude writes Svelte 5 and SvelteKit 3. In an older project it proposes the migration first, and writes for your installed version only if you decline or ask it to proceed without questions — and says so, never a mix.
- 🔎 **Asks the language server, not Grep,** for symbols, references and callers.

**The difference in one component**

|                    | Svelte 4 habits, without the plugin                                | Svelte 5, with the plugin                                         |
| ------------------ | ------------------------------------------------------------------ | ----------------------------------------------------------------- |
| Props and state    | `export let open = false;` and `$: label = open ? 'Hide' : 'Show'` | `let { open = $bindable(false) } = $props();` and `$derived(...)` |
| Events and content | `on:click`, `createEventDispatcher`, `<slot />`                    | `onclick`, a callback prop, `{@render children?.()}`              |
| SvelteKit          | `$app/stores`, `$lib/x`, `svelte.config.js`                        | `$app/state`, `#lib/x.js`, options in `vite.config` (SvelteKit 3) |

**What it costs you**

- **Tools to install first:** the Svelte language server and `svelte-check` in your project (see [Prerequisites](#-prerequisites)). Without them the skills and the Svelte MCP tools still work; code intelligence and the end-of-turn check do not.
- **Time at the end of a turn:** after Svelte edits, the plugin runs your project's own `svelte-check` over the whole project (up to 5 minutes), without a permission prompt.
- **Code that leaves your machine:** code passed to the Svelte autofixer goes to the Svelte team's server. See [Permissions](#-permissions) to keep it local.

**Built on the Svelte team's own AI tools**

|              |                                                                                                                                                                                  |
| ------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Upstream** | [sveltejs/ai-tools](https://github.com/sveltejs/ai-tools) (MIT) — skills and agent rewritten, corrected, and extended with SvelteKit 3, the Svelte CLI, Astro and Tailwind CSS 4 |
| **MCP**      | The Svelte team's remote server, which keeps its connection across `/clear`, reload and compact                                                                                  |
| **LSP**      | The Svelte language server, from a binary _you_ install                                                                                                                          |
| **Credits**  | [NOTICE](NOTICE) lists every derived file                                                                                                                                        |

_Not affiliated with or endorsed by the Svelte project._

## 🎯 What it does

| Situation                                          | What the plugin does                                                                                                                                                                                                                                                                | Result                                                                                                            |
| -------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| You ask for a new component or route               | Fetches the current Svelte and SvelteKit sections, writes runes and SvelteKit 3 code, runs the autofixer, the language server and the project check until all are clean                                                                                                             | Code that compiles and type-checks against the Svelte and SvelteKit versions your project has installed           |
| You paste a component and ask what is wrong        | Runs the Svelte autofixer on it and checks the current docs                                                                                                                                                                                                                         | Each problem with the rule behind it and the fix                                                                  |
| Your project is still on SvelteKit 2 or Svelte 4   | Proposes the migration before writing, runs it with you (`sv migrate`, then the manual checklist), and writes old-version code only if you decline or ask to proceed without questions                                                                                              | A project on SvelteKit 3 and Svelte 5, or, if you decline, code that runs today without a mix of versions         |
| You upgrade a SvelteKit 2 project                  | Explains the breaking changes, runs or reviews `sv migrate sveltekit-3`, and fixes what the codemod leaves in `MIGRATION_TASKS.md`                                                                                                                                                  | A project on SvelteKit 3 with `#lib`, `$app/state` and the config in `vite.config`                                |
| You ask where something is used or who calls it    | Asks the language server first and adds a text search only for what it cannot see (route files, string paths, CSS classes)                                                                                                                                                          | Locations marked as language-server results or text matches                                                       |
| You rename or delete a prop, function or component | Finds every reference, changes the declaration first, runs the project check and compares its errors with the references before editing the rest                                                                                                                                    | No missed usages, with the check's output as proof                                                                |
| Claude edits Svelte files and is about to finish   | The language server reports each edited `.svelte` file's diagnostics right after the edit; when Claude finishes a turn with Svelte changes it has not checked yet, the plugin runs your project's own `svelte-check` and sends the errors back so Claude fixes them before stopping | Errors in the edited file and in every file that uses it are caught in the same turn, not by you later            |
| You ask for a review                               | The auditor, which has no file-editing tools, checks legacy syntax, runes misuse, Kit 3 leftovers, server/client leaks, CSRF and origin settings                                                                                                                                    | A findings table with file, line, severity, evidence and fix; next-version changes listed apart as migration work |

## 📋 Prerequisites

<!-- BEGIN GENERATED: requirements -->

| Requirement      | Minimum                                                                                    | Check                               |
| ---------------- | ------------------------------------------------------------------------------------------ | ----------------------------------- |
| Operating system | macOS, Linux (WSL included), or Windows with [Git Bash](https://git-scm.com/downloads/win) | `uname -s` (in Git Bash on Windows) |
| Claude Code      | 2.1.289                                                                                    | `claude --version`                  |

Not installed, or older than the minimum? Follow the [setup guide](https://code.claude.com/docs/en/setup), or run `claude update` to update an existing install. On Windows, install [Git for Windows](https://git-scm.com/downloads/win), which provides Git Bash: Claude Code runs hooks and shell commands with it, and these plugins are not supported without it.

<!-- END GENERATED: requirements -->

### Versions this plugin is written for

| Target                     | Major     |
| -------------------------- | --------- |
| Svelte                     | 5 (runes) |
| SvelteKit                  | 3         |
| Astro, with Svelte islands | 7         |
| Tailwind CSS               | 4         |

This table is the single declaration of the majors: skills and agents name the majors they are written for, a minor or patch number only where it is the fact being taught, and none of them carries a verification date. A version number appears inside the plugin only where the number is the fact being taught — the release that added or removed an API, a minimum that carries a security fix, a peer range — and then in one reference that the others link to. On an older major the plugin proposes the migration first, and writes for your installed version only if you decline or ask it to proceed without questions, never mixing versions.

### Tools

> **Only Claude Code is required.** Without the tools below the plugin still loads: the skills and the Svelte MCP tools work. The tools add code intelligence for `.svelte` files and the end-of-turn project check.

In the order you install them, before the plugin:

| Tool                                      | Minimum                                                    | Check                     | Why                                                                                                                                       |
| ----------------------------------------- | ---------------------------------------------------------- | ------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| Node.js                                   | 18 for the language server; 22.17 for SvelteKit 3 projects | `node --version`          | Runs `svelteserver`; SvelteKit 3 itself needs 22.17                                                                                       |
| `svelte-language-server` (`svelteserver`) | 0.18.4                                                     | `command -v svelteserver` | Code intelligence for `.svelte` files; see the next step                                                                                  |
| TypeScript in your project                | 5.9 or 6                                                   | `npx tsc --version`       | Peer of the language server; SvelteKit 3 projects use TypeScript 6                                                                        |
| `svelte-check` in your project            | 4                                                          | `npm ls svelte-check`     | The project check, which the skills run and the end-of-turn hook runs from `node_modules/.bin`; projects created with `sv create` have it |
| `curl`                                    | any                                                        | `curl --version`          | Raw documentation and changelog downloads when the MCP server is unavailable                                                              |
| `@sveltejs/mcp` (`svelte-mcp`), optional  | 0.1.26                                                     | `command -v svelte-mcp`   | Only to run the autofixer on your machine instead of the remote server, or offline: `npm install -g @sveltejs/mcp`                        |

> **Install the language server binary first.** The plugin starts `svelteserver` but does not ship it, and Claude Code finds it only on the `PATH` of the shell you start `claude` from.

Until it is on that `PATH`:

- The plugin's LSP configuration does nothing and there is no code intelligence for `.svelte` files.
- The `svelte-lsp-navigation` skill falls back to text search.

Choose one install:

- **Global** (recommended: one install for every project):

  ```bash
  npm install -g svelte-language-server
  command -v svelteserver   # must print a path
  ```

- **In one project**, if you keep tools per project: install it as a dev dependency and start `claude` with the project's `node_modules/.bin` on your `PATH`, for example through your shell or direnv:

  ```bash
  npm install -D svelte-language-server
  PATH="$PWD/node_modules/.bin:$PATH" claude
  ```

Then:

- **Session already open?** Run `/reload-plugins` after installing — `/reload-plugins --force` if the LSP tool was never loaded in it.
- **MCP server:** remote (`https://mcp.svelte.dev/mcp`). It needs network access and nothing installed.
- **`.ts` and `.js` code intelligence** needs a TypeScript language server plugin, which this one does not include.

## ⚡ Installation

<!-- BEGIN GENERATED: installation -->

Inside a Claude Code session, in one command. It asks you to confirm adding the `claude-essentials` marketplace, then opens the plugin's details, where you install it:

```text
/plugin install svelte-development --marketplace nerymurillohnd/claude-essentials
```

Or in two steps; skip the first line if you already added the marketplace:

```text
/plugin marketplace add nerymurillohnd/claude-essentials
/plugin install svelte-development@claude-essentials
```

From your shell:

```bash
claude plugin marketplace add nerymurillohnd/claude-essentials
claude plugin install svelte-development@claude-essentials
```

<!-- END GENERATED: installation -->

## 🚀 Usage

Claude loads a skill when your request matches its description. To be certain, name it, for example `/svelte-development:svelte-best-practices`, or ask for an agent by name.

**Create a component or a route**

```text
Create a SvelteKit 3 route at /todos with a form action that adds an item, and a list that shows them.
```

- Claude hands it to the [component editor](agents/svelte-component-editor.md) agent, which works in its own context, so documentation lookups do not fill your conversation.
- Guided by [`svelte-best-practices`](skills/svelte-best-practices/SKILL.md), it fetches `kit/form-actions` and `kit/load`, writes `+page.server.ts` and `+page.svelte`, runs the autofixer and reads the language server diagnostics.
- _Want it for certain?_ Name it: "Use the svelte-component-editor agent to …", or mention `@agent-svelte-development:svelte-component-editor`.

**Check a component you already have**

```text
/svelte-development:svelte-docs-and-autofixer check src/lib/components/Cart.svelte
```

- Runs [`svelte-docs-and-autofixer`](skills/svelte-docs-and-autofixer/SKILL.md): the autofixer, then the fixes, until it reports nothing.

**Ask where something is used**

```text
Where is the Counter class used, and is formatPrice still called anywhere?
```

- [`svelte-lsp-navigation`](skills/svelte-lsp-navigation/SKILL.md) answers with `findReferences` and `incomingCalls` instead of a text search.

**Rename across the project**

```text
Rename the label prop of CounterButton to caption everywhere.
```

- Claude lists the uses with `findReferences`, renames the declaration alone, runs the project check, and compares the errors with that list.
- **An error at an unlisted place** is a use the language server missed. **A listed place with no error** is a use the check cannot see. Both are fixed before the rename counts as done.

**Audit without changing anything**

```text
Use the svelte-code-auditor agent to audit src/ after our SvelteKit 3 upgrade.
```

- The [auditor](agents/svelte-code-auditor.md) runs the project check and the autofixer, walks its checklist and returns a findings table, changing no file.
- Ask the [component editor](agents/svelte-component-editor.md) to apply the fixes.

## 🧩 Components

<!-- BEGIN GENERATED: components -->

| Type       | Name                                                                                         | What it does                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| ---------- | -------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Skill      | [`/svelte-development:svelte-best-practices`](skills/svelte-best-practices/SKILL.md)         | Writes, reviews and explains Svelte 5 and SvelteKit 3 code by current practice (runes, snippets, events, routes, load, forms, env, config) and migrates SvelteKit 2 or Svelte 4 projects. Use for any task that writes or changes Svelte or SvelteKit code, including a pasted component, a route or a param matcher.                                                                                                                                                                                                                                                |
| Skill      | [`/svelte-development:svelte-docs-and-autofixer`](skills/svelte-docs-and-autofixer/SKILL.md) | Fetches the official Svelte, SvelteKit and Svelte CLI docs and checks Svelte code with the Svelte autofixer, through the plugin's Svelte MCP tools. Use when an exact API, rune, option or signature matters, or to check a Svelte component for problems.                                                                                                                                                                                                                                                                                                           |
| Skill      | [`/svelte-development:svelte-lsp-navigation`](skills/svelte-lsp-navigation/SKILL.md)         | Answers where a Svelte project's component, prop, function or type is defined, used or called, and what a change would break, through the Svelte language server and the project check. Use for "is X used", "which files break if", renames, types and checking the project for errors.                                                                                                                                                                                                                                                                             |
| Agent      | [`svelte-development:svelte-code-auditor`](agents/svelte-code-auditor.md)                    | Audits Svelte 5 and SvelteKit 3 code without changing it - legacy Svelte 4 syntax, runes misuse, SvelteKit 2 leftovers after an upgrade, server and client boundary leaks, CSRF and origin settings, unsafe HTML, accessibility warnings, Astro island props and Tailwind CSS 4 setup - and reports evidence-backed findings with file, line, severity and fix. Use when asked to review, audit or check a Svelte or SvelteKit codebase, a pull request or a migration to Svelte 5 or SvelteKit 3. Not for making changes (use svelte-component-editor).             |
| Agent      | [`svelte-development:svelte-component-editor`](agents/svelte-component-editor.md)            | Writes and edits Svelte 5 components (.svelte) and modules (.svelte.ts, .svelte.js) and SvelteKit 3 route files, checking every change against the current Svelte docs, the Svelte autofixer, the Svelte language server and the project check before handing it back. Use proactively when creating, editing, refactoring or migrating Svelte or SvelteKit files beyond a line or two, or fixing errors the Svelte compiler, the language server or svelte-check report. Not for read-only reviews (use svelte-code-auditor) or questions that need no file change. |
| Hook       | `PreToolUse`                                                                                 | Runs automatically on this event; see Permissions                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| Hook       | `SessionEnd`                                                                                 | Runs automatically on this event; see Permissions                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| Hook       | `Stop`                                                                                       | Runs automatically on this event; see Permissions                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| MCP server | `svelte`                                                                                     | Tools appear as `mcp__plugin_svelte-development_svelte__*`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| LSP server | `svelte`                                                                                     | Code intelligence for the mapped file types                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |

<!-- END GENERATED: components -->

## 🔐 Permissions

> **Read this before installing.** Everything Claude itself runs goes through your permission prompts. The two hooks do not: Claude Code runs them on their event, without asking.

### What each prompt covers

| Item                         | Prompted?             | What it does                                                                  |
| ---------------------------- | --------------------- | ----------------------------------------------------------------------------- |
| **MCP server `svelte`**      | Yes                   | The Svelte team's remote server at `https://mcp.svelte.dev/mcp`, over HTTPS   |
| **LSP server `svelte`**      | No prompt, local only | `svelteserver` over stdio for `.svelte` files; sends nothing over the network |
| **Skill and agent commands** | Yes                   | `curl -sS`, `npm view`, `npx --no-install svelte-check`, the project check    |
| **Hooks in `hooks/`**        | **No**                | Two bash scripts Claude Code runs itself; see [Hooks](#hooks) below           |

### Code that leaves your machine

- **Documentation tools** (`list-sections`, `get-documentation`) return the current docs and send no code.
- **`svelte-autofixer` and `playground-link`** send the code you or Claude pass them to the Svelte team's server, which states that it does not log, store or inspect it ([remote setup](https://svelte.dev/docs/ai/remote-setup)). The server records usage events: tool name, session and client.
- **Keep it local** by disabling the server in `/mcp` and asking Claude to use the `svelte-mcp` command line, which runs the autofixer on your machine.
- **Fallback downloads** reach `svelte.dev`, `raw.githubusercontent.com` (the `sveltejs`, `withastro` and `tailwindlabs` repositories), `api.github.com` (unauthenticated, 60 requests per hour) and the npm registry.

### Your files

| Component                                             | Can it write?          | Limits                                                                        |
| ----------------------------------------------------- | ---------------------- | ----------------------------------------------------------------------------- |
| [Auditor](agents/svelte-code-auditor.md)              | No Edit, no Write tool | Has Bash for the project checks, limited by its instructions, not technically |
| [Component editor](agents/svelte-component-editor.md) | Yes                    | Only the files the task asks for                                              |
| Skills                                                | No                     | They never write files                                                        |
| Hooks                                                 | No file of yours       | They write only small state files in the plugin's data folder                 |

Both agents run `svelte-check` and `svelte-kit sync` with `npx --no-install`, so they never download a package your project does not already have.

### Hooks

Two bash scripts in `hooks/`, run by path. Neither reads its input or the network. They are part of the plugin, so turning them off means disabling the plugin in `/plugin`.

**`skill-hint.sh`** — before a Svelte MCP tool, a `svelte-mcp`, `svelte-check` or `sv` command, or a `Grep` or `Glob` call:

- Names the skill that fits, once per session for each kind, and for searches says to ask the language server first.
- Runs on `Grep` and `Glob` only in a project whose `package.json` mentions `svelte`.
- Keeps one empty file per hint and session in `${CLAUDE_PLUGIN_DATA}`, removed at `SessionEnd`.
- A hook cannot load a skill; it only says which one to load.

**`check-on-stop.sh`** — when Claude finishes a turn with changed `.svelte`, `.svelte.ts` or `.svelte.js` files it has not checked yet:

- Runs **one command: your project's own `svelte-check`** from `node_modules/.bin`. Never downloaded, never installed.
- That command loads your `svelte.config.js`, which is JavaScript, **so your project's configuration runs without a prompt**.
- Runs **no generator**: generating a project's types is your project's own command, which stays behind a prompt.
- Checks the whole project, because `svelte-check` has no single-file mode, and sends the errors to Claude, which keeps working on them.
- Writes no file of yours; keeps one fingerprint per project in the plugin's data folder, and stops after 5 minutes.

It stays **silent** when there is nothing to check, without git, before the first commit, without an installed `svelte-check`, outside the project root (a monorepo package in a subfolder is not checked), and for a state it already checked — so errors that predate your session cannot hold Claude in a loop.

When `svelte-check` reports errors only in a JSON configuration file, it could not read your TypeScript configuration and checked no source file. In a SvelteKit project that configuration extends a file SvelteKit generates, so the hook says exactly that and asks Claude to run your project check, which generates the types first and goes through your prompts.

> The checks it asks for include the autofixer, so **more of your component code reaches the Svelte team's server** than without the hook. If that code must stay on your machine, disable the `svelte` server in `/mcp` and use the local `svelte-mcp`.

### In Claude Tag

Slack, public beta:

- The organization's Activity page exports the outbound requests Claude makes, **but not its MCP traffic**, so code sent to the autofixer is not in that export ([audit](https://claude.com/docs/claude-tag/admins/audit)).
- Sessions run in a sandbox that can block hosts other than the default package registries until an admin allows them, which stops the `curl` fallbacks.
- `svelteserver` is not preinstalled there ([configure GitHub](https://claude.com/docs/claude-tag/admins/configure-github#install-project-dependencies)).

### Allow rules

Nothing is pre-approved. To skip prompts for the read-only documentation tools, add your own allow rules, for example:

```text
mcp__plugin_svelte-development_svelte__list-sections
mcp__plugin_svelte-development_svelte__get-documentation
Bash(curl -sS https://svelte.dev/docs/*)
```

<!-- BEGIN GENERATED: runtime -->

What this plugin runs on your machine, generated from its configuration files:

| Component                                                     | Runs                                                               |
| ------------------------------------------------------------- | ------------------------------------------------------------------ |
| Hook `PreToolUse` (mcp__plugin_svelte-development_svelte__.*) | `"${CLAUDE_PLUGIN_ROOT}/hooks/skill-hint.sh" docs`                 |
| Hook `PreToolUse` (Bash)                                      | `"${CLAUDE_PLUGIN_ROOT}/hooks/skill-hint.sh" docs`                 |
| Hook `PreToolUse` (Bash)                                      | `"${CLAUDE_PLUGIN_ROOT}/hooks/skill-hint.sh" check`                |
| Hook `PreToolUse` (Bash)                                      | `"${CLAUDE_PLUGIN_ROOT}/hooks/skill-hint.sh" cli`                  |
| Hook `PreToolUse` (Bash)                                      | `"${CLAUDE_PLUGIN_ROOT}/hooks/skill-hint.sh" cli`                  |
| Hook `PreToolUse` (Bash)                                      | `"${CLAUDE_PLUGIN_ROOT}/hooks/skill-hint.sh" cli`                  |
| Hook `PreToolUse` (Bash)                                      | `"${CLAUDE_PLUGIN_ROOT}/hooks/skill-hint.sh" cli`                  |
| Hook `PreToolUse` (Grep\|Glob)                                | `"${CLAUDE_PLUGIN_ROOT}/hooks/skill-hint.sh" lsp`                  |
| Hook `SessionEnd` (all)                                       | `rm -f "${CLAUDE_PLUGIN_DATA}"/hint-*-"${CLAUDE_CODE_SESSION_ID}"` |
| Hook `Stop` (all)                                             | `"${CLAUDE_PLUGIN_ROOT}/hooks/check-on-stop.sh"`                   |
| MCP server `svelte` (http)                                    | `https://mcp.svelte.dev/mcp`                                       |
| LSP server `svelte`                                           | `svelteserver`                                                     |

<!-- END GENERATED: runtime -->

## ❓ FAQ

<details>
<summary>Does installing this plugin modify my project?</summary>

No. Installing adds the plugin to your Claude Code configuration only.

| What                                                           | Changes your project?                                          |
| -------------------------------------------------------------- | -------------------------------------------------------------- |
| The skills                                                     | Never; they write no files                                     |
| The [auditor](agents/svelte-code-auditor.md)                   | No source file                                                 |
| The [component editor](agents/svelte-component-editor.md)      | Only the files a task names                                    |
| `npx --no-install svelte-kit sync`, which either agent may run | Regenerates SvelteKit's generated folder                       |
| The end-of-turn hook                                           | Nothing: it runs `svelte-check`, which writes no file of yours |

</details>

<details>
<summary>I already use the Svelte team's own plugin (`svelte@svelte`). Should I install both?</summary>

**No, pick one.**

- `sv add ai-tools` can enable `svelte@svelte` in a project's `.claude/settings.json`.
- Both plugins connect a Svelte MCP server and a language server for the same files, and their skills give overlapping instructions.
- To use this one there, run `/plugin disable svelte@svelte`.
- This plugin's components have different names, so nothing is overwritten.

</details>

<details>
<summary>What runs on my machine, what leaves it, and what can the agents change?</summary>

|                         |                                                                                                                                                                                                                                                                                                         |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Local**               | `svelteserver`, which you install, sends nothing. The hooks print fixed notes, keep small state files in the plugin's data folder, and run your project's own `svelte-check` at the end of turns with unchecked Svelte changes — **without a permission prompt**, because Claude Code runs hooks itself |
| **Leaves your machine** | Documentation requests to `https://mcp.svelte.dev`, and any code passed to the autofixer or the playground tool (the Svelte team states it does not log, store or inspect it). Changelog checks reach `raw.githubusercontent.com`, `api.github.com` and the npm registry                                |
| **Changes files**       | The [component editor](agents/svelte-component-editor.md), only what the task asks for. The [auditor](agents/svelte-code-auditor.md) has no tool to edit or write                                                                                                                                       |
| **Model**               | Both agents use your session's model                                                                                                                                                                                                                                                                    |

The end-of-turn check leads Claude to run the autofixer after Svelte edits, so keep the server off and use the local `svelte-mcp` if your code must stay on your machine. See [Permissions](#-permissions).

</details>

<details>
<summary>Does it work on a SvelteKit 2 or Svelte 4 project?</summary>

**Yes, by migrating it first.** Claude reads the installed versions before writing anything.

- On SvelteKit 2 or Svelte 4, it proposes the migration (`sv migrate sveltekit-3` or `sv migrate svelte-5`), runs it with you, and then works on SvelteKit 3 and Svelte 5.
- If you decline, or ask it to proceed without questions (an automated run), it writes code that runs on your installed version — no `#lib` imports, `$app/env` or `defineParams` in SvelteKit 2, no runes in Svelte 4 — and says so.
- SvelteKit 1 or Svelte 3 first need the older `sv migrate` steps (`sveltekit-2`, `svelte-4`); the plugin has no step-by-step guide for them.
- The live documentation describes the newest versions, so Claude checks each API against your installed one.

</details>

<details>
<summary>Does it work on Windows?</summary>

**Not tested yet.** Windows needs Git Bash, as the [Prerequisites](#-prerequisites) say: Claude Code runs the plugin's hooks with it, and without it the hooks fail (without blocking anything) and the plugin is not supported.

- The MCP server is remote, and the language server is a Node.js program that should run anywhere Node.js does.
- The fallback commands use `curl`, which Windows 10 and later include, plus `grep` and `awk`, which come with Git Bash.
- Report problems through an issue.

</details>

## 🔄 Update and uninstall

<!-- BEGIN GENERATED: uninstall -->

**Update.** Background auto-update is off for community marketplaces. From your shell:

```bash
claude plugin update svelte-development@claude-essentials
```

Or in a session: `/plugin` → **Installed** → the plugin → **Update now**. The new version loads in your next session; in a session that is already open, run `/reload-plugins`. To update automatically, turn on **Enable auto-update** for `claude-essentials` under `/plugin` → **Marketplaces**.

**Check the installed version** with `/plugin list`.

**Disable or uninstall.** In a session:

```text
/plugin disable svelte-development@claude-essentials
/plugin uninstall svelte-development@claude-essentials
```

From your shell:

```bash
claude plugin disable svelte-development@claude-essentials
claude plugin uninstall svelte-development@claude-essentials
```

Uninstalling from the last scope also deletes the plugin's stored options and its data directory; add `--keep-data` to the shell command to keep the data.

<!-- END GENERATED: uninstall -->

## 📚 Documentation

<!-- BEGIN GENERATED: documentation -->

| Document                                                                                                 | Read it for                                                  |
| -------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------ |
| [Changelog](CHANGELOG.md)                                                                                | Release notes and migration steps for this plugin            |
| [Claude Essentials](https://github.com/nerymurillohnd/claude-essentials/blob/main/README.md)             | The marketplace, its catalog and how to keep plugins updated |
| [Security policy](https://github.com/nerymurillohnd/claude-essentials/blob/main/SECURITY.md)             | Reporting a vulnerability privately                          |
| [Security review](https://github.com/nerymurillohnd/claude-essentials/blob/main/docs/security-review.md) | How plugins that run code are reviewed                       |
| [Contributing](https://github.com/nerymurillohnd/claude-essentials/blob/main/CONTRIBUTING.md)            | Reporting a bug or proposing a change to this plugin         |
| [Claude Code plugins](https://code.claude.com/docs/en/plugins/install)                                   | Installing, updating and removing plugins                    |

<!-- END GENERATED: documentation -->

## 📄 License

<!-- BEGIN GENERATED: license -->

This plugin is released under the [MIT License](LICENSE), like the rest of Claude Essentials. Third-party material is listed in [THIRD_PARTY_NOTICES.md](https://github.com/nerymurillohnd/claude-essentials/blob/main/THIRD_PARTY_NOTICES.md).

<!-- END GENERATED: license -->
