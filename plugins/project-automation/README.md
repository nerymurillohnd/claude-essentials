# Project Automation

<!-- BEGIN GENERATED: header -->

[![version: 0.1.0](https://img.shields.io/badge/version-0.1.0-blue)](CHANGELOG.md) [![category: workflows](https://img.shields.io/badge/category-workflows-informational)](https://github.com/nerymurillohnd/claude-essentials/blob/main/README.md#categories) [![Claude Code: ≥ 2.1.289](https://img.shields.io/badge/Claude%20Code-%E2%89%A5%202.1.289-orange)](https://code.claude.com/docs) [![license: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE) [![CI](https://github.com/nerymurillohnd/claude-essentials/actions/workflows/validate.yml/badge.svg)](https://github.com/nerymurillohnd/claude-essentials/actions/workflows/validate.yml) [![skills: 1](https://img.shields.io/badge/skills-1-blueviolet)](#components) [![agents: 3](https://img.shields.io/badge/agents-3-blueviolet)](#components) [![runs code: no](https://img.shields.io/badge/runs%20code-no-brightgreen)](#components)

Audits a repository and builds evidence-backed Claude Code automation for it: skills, subagents, hooks, rules and settings, each verified working before it is handed over.

Part of [Claude Essentials](https://github.com/nerymurillohnd/claude-essentials), an independent community plugin marketplace for Claude Code. Not affiliated with or endorsed by Anthropic.

**Contents:** [Overview](#overview) · [Requirements](#requirements) · [Installation](#installation) · [Usage](#usage) · [Components](#components) · [Uninstall](#uninstall) · [Documentation](#documentation) · [License](#license)

<!-- END GENERATED: header -->

## Overview

Claude Code can be extended with skills, subagents, hooks, permission rules and more, but choosing the right piece for a repository, writing it with the syntax your installed version expects, and proving it works takes more than asking Claude to "set up automation". Unaided, Claude proposes plausible configuration from memory. In our baseline run on a sample repository, it proposed a deny rule for `.env.*` with an allow exception for `.env.example`, which can never apply because Claude Code evaluates deny rules before allow rules, and it missed the built-in behaviour that runs a project `verify` skill before every commit.

This plugin gives Claude a disciplined method for that job. It inventories the repository and its history for recurring manual work, checks the live Claude Code documentation and changelog for the version you have installed, proposes only automation backed by evidence and waits for your approval, then builds each approved item with a positive and a negative test and has an independent agent try to break it. You end with working automation, a short guide for your team, and a plain list of anything it could not prove.

It is for developers and teams who use Claude Code in a repository and want it set up properly, or want an existing setup audited and fixed.

The plugin ships its own eval suite in `evals/`, which runs the same request with and without the plugin on a sample repository. On 2026-10-05, with Claude Code 2.1.289 and Claude Sonnet, two runs per arm scored 1.00 with the plugin and 0.63 without it; the misses without it were the missing `verify` skill and, in one run, the unworkable deny exception. Unrelated requests did not load the skill. Re-run it with `claude plugin eval project-automation@claude-essentials --no-publish --scaffold --allow-tools Bash "WebFetch(domain:code.claude.com)"`; each run is a billed model call.

## Requirements

<!-- BEGIN GENERATED: requirements -->

- Claude Code 2.1.289 or later.

<!-- END GENERATED: requirements -->

- git, to read the repository history. Without it the audit still runs, with fewer signals.
- Web access from Claude Code to `code.claude.com` (and, when npm is installed, the npm registry) for the documentation check. Without it, the plugin says so and marks its proposals as unverified.
- macOS or Linux, or Windows with Git Bash: the agents use common shell commands (`git`, `sort`, `uniq`). On Windows without Git Bash, Claude adapts them to PowerShell.

## Installation

<!-- BEGIN GENERATED: installation -->

Inside a Claude Code session:

```text
/plugin marketplace add nerymurillohnd/claude-essentials
/plugin install project-automation@claude-essentials
```

From your shell:

```bash
claude plugin marketplace add nerymurillohnd/claude-essentials
claude plugin install project-automation@claude-essentials
```

Background auto-update is off for community marketplaces. Get fixes with `claude plugin update project-automation@claude-essentials`, or turn on **Enable auto-update** for `claude-essentials` under `/plugin` → **Marketplaces**.

<!-- END GENERATED: installation -->

## Usage

Start it in the repository you want to automate, optionally with a focus:

```text
/project-automation:automate
/project-automation:automate releases
```

Or ask in your own words, for example "audit this repo and set up Claude Code hooks and skills for it"; Claude loads the skill when the request matches.

What happens:

1. **Scope.** Claude checks your Claude Code version and the repository state, and asks once whether it may read the prompts from this project's past sessions (repeated prompts are the best signal for a skill; the answer can be no).
2. **Discover.** Two read-only agents run in parallel: `automation-scout` inventories the repository, its existing Claude Code setup and its history; `feature-researcher` reads the official docs and changelog for your version.
3. **Propose.** Claude shows a table: each row has the evidence that justifies it, the feature it would use and where it would live, effort, impact, context cost and risk, plus what it rejected and why. Broken existing automation is listed first. **Nothing is written until you approve.**
4. **Build.** For each row you approve, Claude writes the acceptance criteria, confirms the syntax on the live documentation page, creates the files and runs a positive and a negative test until both pass.
5. **Verify.** `automation-verifier` re-runs every test independently and tries inputs the author did not, such as another spelling of a guarded command.
6. **Hand over.** Claude writes a guide (by default `claude-code-automation.md` in your project's documentation folder, or at the root) and a final report listing what was built, what was not proven and what to check after a restart.

Example: in a Node.js service whose history shows repeated "fix lint errors after review" commits and whose `.claude/settings.json` points to a hook script that does not exist, the proposal ranks the broken hook first, then suggests a project `verify` skill that runs lint and tests before each commit, and explains why it prefers that to a commit-blocking hook.

The plugin never commits, pushes, installs packages, or changes files in your home directory or managed settings unless you ask for that exact action. The agents only read; files are written in phase 4, after your approval, and only those you approved. Fetching documentation sends ordinary web requests to the hosts listed under Requirements; the plugin sends nothing from your repository anywhere beyond Claude Code's normal model requests.

## Components

<!-- BEGIN GENERATED: components -->

| Type  | Name                                     | What it does                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| ----- | ---------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Skill | `/project-automation:automate`           | Audits the current repository and builds Claude Code automation for it (skills, subagents, hooks, permission rules, CLAUDE.md and rules, settings, scheduled tasks), choosing each piece from evidence in the repository, checking every configuration detail against the live Claude Code documentation for the installed version, and proving each piece works before handing it over. Use when the user asks to set up, audit, improve or automate Claude Code for a project; to add hooks, skills, subagents or permission rules to a repository; to fix Claude Code configuration that does not work; or to find recurring manual work Claude Code could take over. |
| Agent | `project-automation:automation-scout`    | Read-only inventory of a repository for Claude Code automation - existing CLAUDE.md, rules, settings, hooks, skills, agents, MCP and CI, the defects in them, and the recurring manual work visible in scripts, docs and git history, each backed by file and command evidence. Use when planning which Claude Code automation a project needs, or when checking whether its existing Claude Code setup works.                                                                                                                                                                                                                                                           |
| Agent | `project-automation:automation-verifier` | Independently verifies Claude Code automation that was just built in a repository - re-runs each item's positive and negative tests, checks file validity and portability, and tries to break each item - and reports a verdict per test with raw output. Use after creating or changing hooks, skills, subagents, permission rules or settings, before telling the user they work.                                                                                                                                                                                                                                                                                      |
| Agent | `project-automation:feature-researcher`  | Researches the live Claude Code documentation and changelog for the version installed on this machine and reports which features fit a project's automation needs, with minimum versions, source URLs and literal quotes, plus any conflict between the docs and the project's files. Use before proposing or writing Claude Code configuration (skills, hooks, subagents, permissions, settings, workflows) and when a Claude Code fact may have changed since training.                                                                                                                                                                                                |

<!-- END GENERATED: components -->

## Uninstall

<!-- BEGIN GENERATED: uninstall -->

```text
/plugin uninstall project-automation@claude-essentials
```

<!-- END GENERATED: uninstall -->

## Documentation

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

## License

<!-- BEGIN GENERATED: license -->

This plugin is released under the [MIT License](LICENSE), like the rest of Claude Essentials. Third-party material is listed in [THIRD_PARTY_NOTICES.md](https://github.com/nerymurillohnd/claude-essentials/blob/main/THIRD_PARTY_NOTICES.md).

<!-- END GENERATED: license -->
