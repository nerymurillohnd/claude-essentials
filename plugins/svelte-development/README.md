# Svelte Development

<!-- BEGIN GENERATED: header -->

[![version: 0.2.0](https://img.shields.io/badge/version-0.2.0-blue)](CHANGELOG.md) [![category: development](https://img.shields.io/badge/category-development-informational)](https://github.com/nerymurillohnd/claude-essentials/blob/main/README.md#categories) [![Claude Code: ≥ 2.1.289](https://img.shields.io/badge/Claude%20Code-%E2%89%A5%202.1.289-orange)](https://code.claude.com/docs) [![license: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE) [![CI](https://github.com/nerymurillohnd/claude-essentials/actions/workflows/validate.yml/badge.svg)](https://github.com/nerymurillohnd/claude-essentials/actions/workflows/validate.yml) [![skills: 3](https://img.shields.io/badge/skills-3-blueviolet)](#-components) [![agents: 2](https://img.shields.io/badge/agents-2-blueviolet)](#-components) [![hooks: 1](https://img.shields.io/badge/hooks-1-blueviolet)](#-components) [![mcp servers: 1](https://img.shields.io/badge/mcp%20servers-1-blueviolet)](#-components) [![lsp servers: 1](https://img.shields.io/badge/lsp%20servers-1-blueviolet)](#-components) [![runs code: yes, reviewed](https://img.shields.io/badge/runs%20code-yes%2C%20reviewed-yellow)](#-permissions)

Svelte 5 and SvelteKit 3 development that also respects SvelteKit 2 projects: current best practices, docs lookup and autofixer, language-server navigation with renames proven by the project check, an editor and an auditor agent, a post-edit autofixer reminder, and the Svelte MCP and language servers, built on the Svelte team's AI tools.

Part of [Claude Essentials](https://github.com/nerymurillohnd/claude-essentials), an independent community plugin marketplace for Claude Code. Not affiliated with or endorsed by Anthropic.

**Contents:** [Overview](#-overview) · [What it does](#-what-it-does) · [Prerequisites](#-prerequisites) · [Installation](#-installation) · [Usage](#-usage) · [Components](#-components) · [Permissions](#-permissions) · [FAQ](#-faq) · [Update and uninstall](#-update-and-uninstall) · [Documentation](#-documentation) · [License](#-license)

<!-- END GENERATED: header -->

## 📖 Overview

Most Svelte code a model has seen is Svelte 4 and SvelteKit 2, so it writes `export let`, `on:click`, `$app/stores` and `svelte.config.js` into projects that run Svelte 5 and SvelteKit 3. This plugin is for developers who build with Svelte, SvelteKit, Astro islands or Tailwind CSS 4 in Claude Code: it gives Claude the current rules, makes it check the official documentation and the changelogs before writing, and makes it prove each change with the Svelte autofixer, the Svelte language server and your project's own check. It writes for the Svelte and SvelteKit versions your project has installed, so a SvelteKit 2 project gets SvelteKit 2 code and an offer to migrate, never a mix of both.

It builds on the Svelte team's own AI tools ([sveltejs/ai-tools](https://github.com/sveltejs/ai-tools), MIT): their skills and agent are rewritten, corrected and extended with SvelteKit 3, the Svelte CLI, Astro and Tailwind CSS 4, the Svelte team's remote MCP server keeps its connection across session changes, and the Svelte language server runs from a binary you install. Credits and the list of derived files are in [NOTICE](NOTICE). Not affiliated with or endorsed by the Svelte project.

## 🎯 What it does

| Situation                                          | What the plugin does                                                                                                                                                    | Result                                                                                                            |
| -------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| You ask for a new component or route               | Fetches the current Svelte and SvelteKit sections, writes runes and SvelteKit 3 code, runs the autofixer, the language server and the project check until all are clean | Code that compiles and type-checks against Svelte 5.57 and SvelteKit 3                                            |
| You paste a component and ask what is wrong        | Runs the Svelte autofixer on it and checks the current docs                                                                                                             | Each problem with the rule behind it and the fix                                                                  |
| Your project is still on SvelteKit 2 or Svelte 4   | Writes code for the installed version and says where SvelteKit 3 or Svelte 5 would differ                                                                               | Code that runs on your project today, and a migration offer instead of a mix of versions                          |
| You upgrade a SvelteKit 2 project                  | Explains the breaking changes, runs or reviews `sv migrate sveltekit-3`, and fixes what the codemod leaves in `MIGRATION_TASKS.md`                                      | A project on SvelteKit 3 with `#lib`, `$app/state` and the config in `vite.config`                                |
| You ask where something is used or who calls it    | Asks the language server first and adds a text search only for what it cannot see (route files, string paths, CSS classes)                                              | Locations marked as language-server results or text matches                                                       |
| You rename or delete a prop, function or component | Finds every reference, changes the declaration first, runs the project check and compares its errors with the references before editing the rest                        | No missed usages, with the check's output as proof                                                                |
| Claude edits a `.svelte` file                      | A hook reminds it, next to the edit, that the autofixer and the project check have not seen the new content                                                             | The checks run after the edit instead of being forgotten                                                          |
| You ask for a review                               | The auditor, which has no file-editing tools, checks legacy syntax, runes misuse, Kit 3 leftovers, server/client leaks, CSRF and origin settings                        | A findings table with file, line, severity, evidence and fix; next-version changes listed apart as migration work |

## 📋 Prerequisites

<!-- BEGIN GENERATED: requirements -->

| Requirement | Minimum | Check              |
| ----------- | ------- | ------------------ |
| Claude Code | 2.1.289 | `claude --version` |

Not installed, or older than the minimum? Follow the [setup guide](https://code.claude.com/docs/en/setup), or run `claude update` to update an existing install.

<!-- END GENERATED: requirements -->

| Tool                                      | Minimum                                                    | Check                                        | Why                                                                                                                             |
| ----------------------------------------- | ---------------------------------------------------------- | -------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| Node.js                                   | 18 for the language server; 22.17 for SvelteKit 3 projects | `node --version`                             | Runs `svelteserver`; SvelteKit 3 itself needs 22.17                                                                             |
| `@sveltejs/mcp` (`svelte-mcp`), optional  | 0.1.26                                                     | `npm ls -g --depth 0 @sveltejs/mcp`          | Only to run the autofixer on your machine instead of the remote server, or offline. Install with `npm install -g @sveltejs/mcp` |
| `svelte-language-server` (`svelteserver`) | 0.18.4                                                     | `npm ls -g --depth 0 svelte-language-server` | Code intelligence for `.svelte` files. Install with `npm install -g svelte-language-server`                                     |
| TypeScript in your project                | 5.9 or 6                                                   | `npx tsc --version`                          | Peer of the language server; SvelteKit 3 projects use TypeScript 6                                                              |
| `curl`                                    | any                                                        | `curl --version`                             | Raw documentation and changelog downloads when the MCP server is unavailable                                                    |

**Install the language server binary.** The plugin's LSP configuration (`.lsp.json`) starts `svelteserver`, which the plugin does not ship. Until it is on your `PATH`, that configuration does nothing: there is no code intelligence for `.svelte` files, and the `svelte-lsp-navigation` skill falls back to text search. Install it once, globally, then reload:

```bash
npm install -g svelte-language-server
command -v svelteserver   # must print a path
```

Then run `/reload-plugins` in an open session (`/reload-plugins --force` if the LSP tool was never loaded in it).

The Svelte MCP server is remote (`https://mcp.svelte.dev/mcp`): it needs network access and nothing installed. Without `svelteserver` the plugin still loads: the skills and the MCP tools work, and code intelligence for `.svelte` files stays unavailable until you install it and run `/reload-plugins`. Code intelligence for `.ts` and `.js` files needs a TypeScript language server plugin, which this plugin does not include.

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

The skills load on their own when a task matches; you can also call them directly.

```text
Create a SvelteKit 3 route at /todos with a form action that adds an item, and a list that shows them.
```

Claude hands the work to the [component editor](agents/svelte-component-editor.md) agent, which runs in its own context so the documentation lookups do not fill your conversation. Guided by [`svelte-best-practices`](skills/svelte-best-practices/SKILL.md), it fetches `kit/form-actions` and `kit/load` through the MCP server, writes `+page.server.ts` and `+page.svelte`, runs the autofixer and reads the language server's diagnostics. You can also name the agent yourself: "Use the svelte-component-editor agent to …", or mention it to make sure it runs: `@agent-svelte-development:svelte-component-editor`.

```text
/svelte-development:svelte-docs-and-autofixer check src/lib/components/Cart.svelte
```

Runs [`svelte-docs-and-autofixer`](skills/svelte-docs-and-autofixer/SKILL.md): the autofixer on the component, then the fixes, until it reports nothing.

```text
Where is the Counter class used, and is formatPrice still called anywhere?
```

[`svelte-lsp-navigation`](skills/svelte-lsp-navigation/SKILL.md) answers with `findReferences` and `incomingCalls` instead of a text search.

```text
Rename the label prop of CounterButton to caption everywhere.
```

Claude lists the uses with `findReferences`, renames the declaration alone, runs the project check, and compares the errors it reports with that list before editing the parents. An error at an unlisted place is a use the language server missed; a listed place with no error is one the check cannot see. Both are fixed before the rename counts as done.

```text
Use the svelte-code-auditor agent to audit src/ after our SvelteKit 3 upgrade.
```

The [auditor](agents/svelte-code-auditor.md) runs the project check and the autofixer, walks its checklist and returns a findings table without changing files. Ask the [component editor](agents/svelte-component-editor.md) to apply the fixes.

## 🧩 Components

<!-- BEGIN GENERATED: components -->

| Type       | Name                                                                                         | What it does                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| ---------- | -------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Skill      | [`/svelte-development:svelte-best-practices`](skills/svelte-best-practices/SKILL.md)         | The Svelte 5 and SvelteKit 3 rules that training data gets wrong - runes, snippets, event attributes, declaration tags, SvelteKit 3 imports, config, environment variables, routing, loading, forms, remote functions, hooks, adapters and security - plus the Svelte CLI (sv), Astro with Svelte islands and Tailwind CSS 4, with one reference per topic. Use before writing, converting, migrating, reviewing or explaining any Svelte or SvelteKit code, including a component pasted in the chat.                                                               |
| Skill      | [`/svelte-development:svelte-docs-and-autofixer`](skills/svelte-docs-and-autofixer/SKILL.md) | Looks up the current official Svelte, SvelteKit and Svelte CLI docs and checks Svelte code with the Svelte autofixer, through this plugin's Svelte MCP tools (get-documentation, svelte-autofixer), with raw-download and local command-line fallbacks. Use whenever Svelte code is written, changed or checked for problems, including a component pasted in the chat, and whenever an exact Svelte or SvelteKit API, rune, option or signature matters.                                                                                                            |
| Skill      | [`/svelte-development:svelte-lsp-navigation`](skills/svelte-lsp-navigation/SKILL.md)         | Answers questions about the project's own Svelte code by symbol, through Claude Code's LSP tool and the Svelte language server - where a component, prop or function is defined and used, who calls it, what type it has, a component's outline, diagnostics after edits - plus the project check with the project's svelte-check. Use in a Svelte or SvelteKit project whenever a task needs exact symbol locations, the impact of a change, type information or proof that the project has no errors, before reaching for Grep.                                    |
| Agent      | [`svelte-development:svelte-code-auditor`](agents/svelte-code-auditor.md)                    | Audits Svelte 5 and SvelteKit 3 code without changing it - legacy Svelte 4 syntax, runes misuse, SvelteKit 2 leftovers after an upgrade, server and client boundary leaks, CSRF and origin settings, unsafe HTML, accessibility warnings, Astro island props and Tailwind CSS 4 setup - and reports evidence-backed findings with file, line, severity and fix. Use when asked to review, audit or check a Svelte or SvelteKit codebase, a pull request or a migration to Svelte 5 or SvelteKit 3. Not for making changes (use svelte-component-editor).             |
| Agent      | [`svelte-development:svelte-component-editor`](agents/svelte-component-editor.md)            | Writes and edits Svelte 5 components (.svelte) and modules (.svelte.ts, .svelte.js) and SvelteKit 3 route files, checking every change against the current Svelte docs, the Svelte autofixer, the Svelte language server and the project check before handing it back. Use proactively when creating, editing, refactoring or migrating Svelte or SvelteKit files beyond a line or two, or fixing errors the Svelte compiler, the language server or svelte-check report. Not for read-only reviews (use svelte-code-auditor) or questions that need no file change. |
| Hook       | `PostToolUse`                                                                                | Runs automatically on this event; see Permissions                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| MCP server | `svelte`                                                                                     | Tools appear as `mcp__plugin_svelte-development_svelte__*`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| LSP server | `svelte`                                                                                     | Code intelligence for the mapped file types                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |

<!-- END GENERATED: components -->

## 🔐 Permissions

- **MCP server `svelte`** is the Svelte team's remote server at `https://mcp.svelte.dev/mcp`, over HTTPS. `list-sections` and `get-documentation` return the current documentation. `svelte-autofixer` and `playground-link` receive the code you or Claude pass them: that code is sent to the Svelte team's server, which states that it does not log, store or inspect it ([remote setup](https://svelte.dev/docs/ai/remote-setup)). The server records usage events (tool name, session and client). If you do not want code to leave your machine, disable the server in `/mcp` and ask Claude to use the local `svelte-mcp` command line, which runs the autofixer on your machine.
- **LSP server `svelte` (`svelteserver`)** runs locally over stdio for `.svelte` files and reads your project's files and `node_modules` to resolve types. It sends nothing over the network.
- **Network from the skills and agents**: when the MCP server is unavailable, or to check what changed between versions, they run `curl -sS` against `svelte.dev`, `raw.githubusercontent.com` (the `sveltejs`, `withastro` and `tailwindlabs` repositories) and `api.github.com` (unauthenticated, 60 requests per hour), and `npm view` against the npm registry. Every command goes through your normal permission prompts.
- **Files**: the [auditor](agents/svelte-code-auditor.md) has no Edit or Write tool. It does have Bash, limited by its instructions rather than technically, to run the project checks; every command still goes through your permission prompts, and the checks it is told to run regenerate only SvelteKit's `.svelte-kit` folder. The [component editor](agents/svelte-component-editor.md) edits only what the task asks for. Both run `svelte-check` and `svelte-kit sync` with `npx --no-install`, so they never download a package your project does not already have.
- **Hook**: after each `Write` or `Edit` of a `.svelte`, `.svelte.ts` or `.svelte.js` file, a `PostToolUse` hook prints a fixed note that Claude reads next to the tool result: the Svelte autofixer has not checked the new content and the project check has not run since the change. It runs `echo` with a constant text, reads nothing, sends nothing, cannot block the edit, and does not run for any other file. Its purpose is that Claude runs the autofixer after Svelte edits, so more of your component code is sent to the Svelte team's server than without it; if that code must stay on your machine, disable the `svelte` server in `/mcp` and ask Claude to use the local `svelte-mcp` command line, which checks files without sending them.
- **In Claude Tag** (Slack, public beta, checked 2026-10-05): the organization's Activity page exports the outbound requests Claude makes, but not its MCP traffic, so code sent to the autofixer does not appear in that export ([audit](https://claude.com/docs/claude-tag/admins/audit)). Sessions run in a sandbox where hosts other than the default package registries can be blocked until an admin allows them, which can stop the `curl` fallbacks, and `svelteserver` is not preinstalled there ([configure GitHub](https://claude.com/docs/claude-tag/admins/configure-github#install-project-dependencies)).
- Nothing is pre-approved. To skip prompts for the read-only documentation tools, you can add allow rules to your own settings, for example `mcp__plugin_svelte-development_svelte__list-sections`, `mcp__plugin_svelte-development_svelte__get-documentation` and `Bash(curl -sS https://svelte.dev/docs/*)`.

<!-- BEGIN GENERATED: runtime -->

What this plugin runs on your machine, generated from its configuration files:

| Component                  | Runs                                                                                                                                                                                                                                                                                                                                                                                                                           |
| -------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Hook `PostToolUse` (Write) | `echo '{"hookSpecificOutput":{"hookEventName":"PostToolUse","additionalContext":"svelte-development: this write created or replaced a Svelte component (.svelte). The Svelte autofixer (mcp__plugin_svelte-development_svelte__svelte-autofixer) has not checked the new content yet; it takes the full file content as code, never a path. The project check (the project's check script) has not run since this change."}}'` |
| Hook `PostToolUse` (Write) | `echo '{"hookSpecificOutput":{"hookEventName":"PostToolUse","additionalContext":"svelte-development: this write created or replaced a Svelte module (.svelte.ts). The Svelte autofixer (mcp__plugin_svelte-development_svelte__svelte-autofixer) has not checked the new content yet; it takes the full file content as code, never a path. The project check (the project's check script) has not run since this change."}}'` |
| Hook `PostToolUse` (Write) | `echo '{"hookSpecificOutput":{"hookEventName":"PostToolUse","additionalContext":"svelte-development: this write created or replaced a Svelte module (.svelte.js). The Svelte autofixer (mcp__plugin_svelte-development_svelte__svelte-autofixer) has not checked the new content yet; it takes the full file content as code, never a path. The project check (the project's check script) has not run since this change."}}'` |
| Hook `PostToolUse` (Edit)  | `echo '{"hookSpecificOutput":{"hookEventName":"PostToolUse","additionalContext":"svelte-development: this edit changed a Svelte component (.svelte). The Svelte autofixer (mcp__plugin_svelte-development_svelte__svelte-autofixer) has not checked the new content yet; it takes the full file content as code, never a path. The project check (the project's check script) has not run since this change."}}'`              |
| Hook `PostToolUse` (Edit)  | `echo '{"hookSpecificOutput":{"hookEventName":"PostToolUse","additionalContext":"svelte-development: this edit changed a Svelte module (.svelte.ts). The Svelte autofixer (mcp__plugin_svelte-development_svelte__svelte-autofixer) has not checked the new content yet; it takes the full file content as code, never a path. The project check (the project's check script) has not run since this change."}}'`              |
| Hook `PostToolUse` (Edit)  | `echo '{"hookSpecificOutput":{"hookEventName":"PostToolUse","additionalContext":"svelte-development: this edit changed a Svelte module (.svelte.js). The Svelte autofixer (mcp__plugin_svelte-development_svelte__svelte-autofixer) has not checked the new content yet; it takes the full file content as code, never a path. The project check (the project's check script) has not run since this change."}}'`              |
| MCP server `svelte` (http) | `https://mcp.svelte.dev/mcp`                                                                                                                                                                                                                                                                                                                                                                                                   |
| LSP server `svelte`        | `svelteserver`                                                                                                                                                                                                                                                                                                                                                                                                                 |

<!-- END GENERATED: runtime -->

## ❓ FAQ

<details>
<summary>Does installing this plugin modify my project?</summary>

No. Installing adds the plugin to your Claude Code configuration only. Your project changes only when you ask: the component editor edits the files a task names, and `npx --no-install svelte-kit sync`, which either agent may run, regenerates the `.svelte-kit` folder. The skills never write files, and the auditor changes no source file.

</details>

<details>
<summary>I already use the Svelte team's own plugin (`svelte@svelte`). Should I install both?</summary>

No, pick one. `sv add ai-tools` can enable `svelte@svelte` in a project's `.claude/settings.json`. Both plugins connect a Svelte MCP server and a language server for the same files, and their skills give overlapping instructions. To use this one in such a project, disable the other with `/plugin disable svelte@svelte`. This plugin's components have different names, so nothing is overwritten.

</details>

<details>
<summary>What runs on my machine, what leaves it, and what can the agents change?</summary>

`svelteserver`, the language server you install, runs locally and sends nothing; the hook only prints a fixed note. The MCP server is remote: the documentation tools reach `https://mcp.svelte.dev`, and code passed to the autofixer or the playground tool is sent there (the Svelte team states it does not log, store or inspect it); the hook makes Claude run the autofixer after Svelte edits, so keep the server off and use the local `svelte-mcp` if your code must stay on your machine. The changelog checks reach `raw.githubusercontent.com`, `api.github.com` and the npm registry. Both agents use your session's model; the [auditor](agents/svelte-code-auditor.md) has no tool to edit or write files, and the [component editor](agents/svelte-component-editor.md) edits only what the task asks for. Every command goes through your permission prompts. See [Permissions](#-permissions).

</details>

<details>
<summary>Does it work on a SvelteKit 2 or Svelte 4 project?</summary>

Yes. Claude reads the installed versions first and writes code that runs on them: no `#lib` imports, `$app/env` or `defineParams` in a SvelteKit 2 project, and no runes in Svelte 4 code. It says where the newer version differs and offers the migration (`sv migrate sveltekit-3` or `sv migrate svelte-5`) instead of mixing both. The live documentation describes the newest versions, so Claude checks each API against your installed one.

</details>

<details>
<summary>Does it work on Windows?</summary>

Not tested yet. The MCP server is remote, and the language server is a Node.js program that should run anywhere Node.js does; the skills' fallback commands use `curl`, which Windows 10 and later include, and the changelog and search commands in the references also use `grep` and `awk`, which come with Git Bash. Report problems through an issue.

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
