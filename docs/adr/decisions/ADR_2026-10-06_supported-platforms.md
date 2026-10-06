---
status: accepted
date: 2026-10-06
decision-makers:
  - "Nery Samuel Murillo (maintainer)"
consulted:
  - "Claude Code by Anthropic (research, drafting and verification)"
---

# Plugins support macOS, Linux and Windows with Git Bash

## Purpose

Fix the platforms every plugin in this marketplace is built and documented for, so hooks and scripts can be written once, in bash, and every README states the same prerequisite in the same place.

## Scope

Every plugin under `plugins/`, the plugin and root README templates (`templates/readme/`), the generated `requirements` block (`scripts/sync_readmes.py`) and the root README Quick start. It does not change the agents the marketplace targets: these plugins are for Claude Code only.

## Context and problem statement

`svelte-development` 0.2.0 ships bash hook scripts. Claude Code runs shell-form hook commands with `sh -c` on macOS and Linux, with Git Bash on Windows, and with PowerShell when Git Bash is not installed (hooks reference, "Exec form and shell form", read 2026-10-06). Under PowerShell a bash script fails; the hook error does not block anything, but the plugin loses its checks. The setup guide calls Git for Windows recommended on native Windows and lists WSL as a Linux setup.

Two ways out: declare the platforms the plugins need, or build per-platform variants (PowerShell scripts, or install-time converters such as multi-agent marketplaces use). Which one fits a Claude Code-only marketplace that is starting out?

## Decision drivers

- One implementation per hook or script, reviewable and testable on the maintainer's machine and on CI's Linux runners.
- Users learn before installing whether a plugin works on their machine.
- Follow what Claude Code already assumes on Windows (Git Bash for the Bash tool and for hooks) instead of working around it.
- No new architecture until a real user need justifies it.

## Considered options

- Support macOS, Linux (WSL included) and Windows with Git Bash, and say so in every README
- Also support Windows without Git Bash, with PowerShell variants or install-time converters

## Decision outcome

Chosen option: **Support macOS, Linux (WSL included) and Windows with Git Bash**, because it keeps one bash implementation, matches Claude Code's own Windows shell, and costs one generated line per README.

The generated `requirements` block of every plugin README lists the operating system before Claude Code, with the Git for Windows link; the root README Quick start lists the platform, Claude Code and each plugin's own prerequisites in install order; the plugin template asks authors to list their tools in install order, with every binary's install command before the Installation section.

### Consequences

- Good, because hooks and scripts stay single-source bash, checked by shellcheck and the `repo` gate.
- Good, because the prerequisite is generated, so no plugin README can omit it.
- Bad, because Windows users without Git Bash are unsupported; their sessions show hook errors and lose what the hooks do.

### Confirmation

The `readmes` gate fails while a plugin README's generated `requirements` block is stale. Revisit when an issue shows demand for Windows without Git Bash, or when a plugin needs a component that bash cannot provide.

## Pros and cons of the options

### Support macOS, Linux and Windows with Git Bash

- Good, because one implementation per script.
- Good, because Git Bash is what Claude Code already prefers on Windows.
- Bad, because it excludes Windows setups that use only PowerShell.

### Also support Windows without Git Bash

- Good, because no Windows user is excluded.
- Bad, because every hook or script needs a second implementation or a conversion step, tested on a platform the maintainer does not run.

## More information

Sources, read 2026-10-06: [hooks reference](https://code.claude.com/docs/en/hooks) (`shell` field; shell form runs `sh -c` on macOS and Linux, Git Bash on Windows, PowerShell without it), [setup guide](https://code.claude.com/docs/en/setup) ("Set up on Windows"), [code intelligence](https://code.claude.com/docs/en/plugins/code-intelligence) (install the language server binary before the plugin; Claude Code finds it on the `PATH` of the shell that starts `claude`).
