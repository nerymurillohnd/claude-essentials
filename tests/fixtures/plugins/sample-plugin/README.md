# Sample Plugin

<!-- BEGIN GENERATED: header -->

[![version: 0.1.0](https://img.shields.io/badge/version-0.1.0-blue)](CHANGELOG.md) [![category: development](https://img.shields.io/badge/category-development-informational)](https://github.com/nerymurillohnd/claude-essentials/blob/main/README.md#categories) [![Claude Code: ≥ 2.1.289](https://img.shields.io/badge/Claude%20Code-%E2%89%A5%202.1.289-orange)](https://code.claude.com/docs) [![license: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE) [![CI](https://github.com/nerymurillohnd/claude-essentials/actions/workflows/validate.yml/badge.svg)](https://github.com/nerymurillohnd/claude-essentials/actions/workflows/validate.yml) [![skills: 1](https://img.shields.io/badge/skills-1-blueviolet)](#-components) [![runs code: no](https://img.shields.io/badge/runs%20code-no-brightgreen)](#-components)

Fixture plugin used only by the gate tests; never listed in the catalog.

Part of [Claude Essentials](https://github.com/nerymurillohnd/claude-essentials), an independent community plugin marketplace for Claude Code. Not affiliated with or endorsed by Anthropic.

**Contents:** [Overview](#-overview) · [What it does](#-what-it-does) · [Prerequisites](#-prerequisites) · [Installation](#-installation) · [Usage](#-usage) · [Components](#-components) · [FAQ](#-faq) · [Update and uninstall](#-update-and-uninstall) · [Documentation](#-documentation) · [License](#-license)

<!-- END GENERATED: header -->

## 📖 Overview

A fixture plugin that the gate tests copy into a temporary repository, so the tests never depend on which plugins the catalog lists. It is not distributed and runs no tools.

## 🎯 What it does

| Situation                                             | What the plugin does                      | Result                                               |
| ----------------------------------------------------- | ----------------------------------------- | ---------------------------------------------------- |
| You want to check that the marketplace's plugins load | `/sample-plugin:hello` greets you by name | A greeting that names the plugin and its marketplace |

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
/plugin install sample-plugin --marketplace nerymurillohnd/claude-essentials
```

Or in two steps; skip the first line if you already added the marketplace:

```text
/plugin marketplace add nerymurillohnd/claude-essentials
/plugin install sample-plugin@claude-essentials
```

From your shell:

```bash
claude plugin marketplace add nerymurillohnd/claude-essentials
claude plugin install sample-plugin@claude-essentials
```

<!-- END GENERATED: installation -->

## 🚀 Usage

Run the skill with an optional name:

```text
/sample-plugin:hello Ada
```

Claude greets you by that name and confirms that `sample-plugin` from `claude-essentials` is installed and its skills load. Without a name it greets you as "there". The skill runs only when you invoke it.

## 🧩 Components

<!-- BEGIN GENERATED: components -->

| Type  | Name                                            | What it does                                                                                                                                                              |
| ----- | ----------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Skill | [`/sample-plugin:hello`](skills/hello/SKILL.md) | Greets the user and confirms that plugins from the Claude Essentials marketplace load correctly. Use when the user runs /sample-plugin:hello to check their installation. |

<!-- END GENERATED: components -->

## ❓ FAQ

<details>
<summary>Does installing this plugin modify my project?</summary>

No. It adds one skill to Claude Code and writes nothing in your project.

</details>

<details>
<summary>Does the skill run on its own?</summary>

No. It runs only when you type `/sample-plugin:hello`.

</details>

<details>
<summary>Does it need network access?</summary>

No. It only prints a greeting.

</details>

## 🔄 Update and uninstall

<!-- BEGIN GENERATED: uninstall -->

**Update.** Background auto-update is off for community marketplaces. From your shell:

```bash
claude plugin update sample-plugin@claude-essentials
```

Or in a session: `/plugin` → **Installed** → the plugin → **Update now**. The new version loads in your next session; in a session that is already open, run `/reload-plugins`. To update automatically, turn on **Enable auto-update** for `claude-essentials` under `/plugin` → **Marketplaces**.

**Check the installed version** with `/plugin list`.

**Disable or uninstall.** In a session:

```text
/plugin disable sample-plugin@claude-essentials
/plugin uninstall sample-plugin@claude-essentials
```

From your shell:

```bash
claude plugin disable sample-plugin@claude-essentials
claude plugin uninstall sample-plugin@claude-essentials
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
