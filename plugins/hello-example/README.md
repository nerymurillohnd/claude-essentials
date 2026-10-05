# Hello Example

<!-- BEGIN GENERATED: header -->

[![version: 0.1.1](https://img.shields.io/badge/version-0.1.1-blue)](CHANGELOG.md) [![category: development](https://img.shields.io/badge/category-development-informational)](https://github.com/nerymurillohnd/claude-essentials/blob/main/README.md#categories) [![Claude Code: ≥ 2.1.289](https://img.shields.io/badge/Claude%20Code-%E2%89%A5%202.1.289-orange)](https://code.claude.com/docs) [![license: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE) [![CI](https://github.com/nerymurillohnd/claude-essentials/actions/workflows/validate.yml/badge.svg)](https://github.com/nerymurillohnd/claude-essentials/actions/workflows/validate.yml) [![skills: 1](https://img.shields.io/badge/skills-1-blueviolet)](#-components) [![runs code: no](https://img.shields.io/badge/runs%20code-no-brightgreen)](#-components)

Example plugin that proves the Claude Essentials pipeline end to end; safe to remove.

Part of [Claude Essentials](https://github.com/nerymurillohnd/claude-essentials), an independent community plugin marketplace for Claude Code. Not affiliated with or endorsed by Anthropic.

**Contents:** [Overview](#-overview) · [What it does](#-what-it-does) · [Prerequisites](#-prerequisites) · [Installation](#-installation) · [Usage](#-usage) · [Components](#-components) · [FAQ](#-faq) · [Update and uninstall](#-update-and-uninstall) · [Documentation](#-documentation) · [License](#-license)

<!-- END GENERATED: header -->

## 📖 Overview

A minimal plugin that exists to prove the Claude Essentials pipeline end to end: scaffolding, validation, the isolated install test and releases. Install it to check that the marketplace works in your Claude Code setup; it changes nothing and runs no tools. Maintainers remove it once real plugins cover the same pipeline.

## 🎯 What it does

| Situation                                                                  | What the plugin does                   | Result                                                                                     |
| -------------------------------------------------------------------------- | -------------------------------------- | ------------------------------------------------------------------------------------------ |
| You just added the marketplace and want proof it works                     | Greets you with `/hello-example:hello` | A reply that confirms the plugin from `claude-essentials` is installed and its skill loads |
| You want to check that your Claude Code version supports community plugins | Runs one skill that needs no tools     | A reply with no errors, or the exact error your setup returns                              |

## 📋 Prerequisites

<!-- BEGIN GENERATED: requirements -->

| Requirement | Minimum | Check              |
| ----------- | ------- | ------------------ |
| Claude Code | 2.1.289 | `claude --version` |

Not installed, or older than the minimum? Follow the [setup guide](https://code.claude.com/docs/en/setup), or run `claude update` to update an existing install.

<!-- END GENERATED: requirements -->

No other prerequisites.

## ⚡ Installation

<!-- BEGIN GENERATED: installation -->

Inside a Claude Code session, in one command. It asks you to confirm adding the `claude-essentials` marketplace, then opens the plugin's details, where you install it:

```text
/plugin install hello-example --marketplace nerymurillohnd/claude-essentials
```

Or in two steps; skip the first line if you already added the marketplace:

```text
/plugin marketplace add nerymurillohnd/claude-essentials
/plugin install hello-example@claude-essentials
```

From your shell:

```bash
claude plugin marketplace add nerymurillohnd/claude-essentials
claude plugin install hello-example@claude-essentials
```

<!-- END GENERATED: installation -->

## 🚀 Usage

Run the skill with an optional name:

```text
/hello-example:hello Ada
```

Claude greets you by that name and confirms that `hello-example` from `claude-essentials` is installed and its skills load. Without a name it greets you as "there". The skill runs only when you invoke it.

## 🧩 Components

<!-- BEGIN GENERATED: components -->

| Type  | Name                                            | What it does                                                                                                                                                              |
| ----- | ----------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Skill | [`/hello-example:hello`](skills/hello/SKILL.md) | Greets the user and confirms that plugins from the Claude Essentials marketplace load correctly. Use when the user runs /hello-example:hello to check their installation. |

<!-- END GENERATED: components -->

## ❓ FAQ

<details>
<summary>Does installing this plugin modify my project?</summary>

No. Installing copies the plugin into Claude Code's plugin cache on your machine and touches nothing in your project. The skill only replies in the conversation when you run it.

</details>

<details>
<summary>Does it run any code or tools?</summary>

No. It has one skill with no hooks, servers or scripts, and the skill asks for no tools.

</details>

<details>
<summary>Why does this plugin exist?</summary>

It proves that the marketplace installs and loads a plugin end to end. It has no other use and is safe to remove.

</details>

## 🔄 Update and uninstall

<!-- BEGIN GENERATED: uninstall -->

**Update.** Background auto-update is off for community marketplaces. From your shell:

```bash
claude plugin update hello-example@claude-essentials
```

Or in a session: `/plugin` → **Installed** → the plugin → **Update now**. The new version loads in your next session; in a session that is already open, run `/reload-plugins`. To update automatically, turn on **Enable auto-update** for `claude-essentials` under `/plugin` → **Marketplaces**.

**Check the installed version** with `/plugin list`.

**Disable or uninstall.** In a session:

```text
/plugin disable hello-example@claude-essentials
/plugin uninstall hello-example@claude-essentials
```

From your shell:

```bash
claude plugin disable hello-example@claude-essentials
claude plugin uninstall hello-example@claude-essentials
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
