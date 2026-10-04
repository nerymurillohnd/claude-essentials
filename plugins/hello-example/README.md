# Hello Example

<!-- BEGIN GENERATED: header -->

[![version: 0.1.0](https://img.shields.io/badge/version-0.1.0-blue)](CHANGELOG.md) [![category: development](https://img.shields.io/badge/category-development-informational)](https://github.com/nerymurillohnd/claude-essentials/blob/main/README.md#categories) [![Claude Code: ≥ 2.1.289](https://img.shields.io/badge/Claude%20Code-%E2%89%A5%202.1.289-orange)](https://code.claude.com/docs) [![license: MIT](https://img.shields.io/badge/license-MIT-green)](https://github.com/nerymurillohnd/claude-essentials/blob/main/LICENSE) [![CI](https://github.com/nerymurillohnd/claude-essentials/actions/workflows/validate.yml/badge.svg)](https://github.com/nerymurillohnd/claude-essentials/actions/workflows/validate.yml) [![skills: 1](https://img.shields.io/badge/skills-1-blueviolet)](#components) [![runs code: no](https://img.shields.io/badge/runs%20code-no-brightgreen)](#components)

Example plugin that proves the Claude Essentials pipeline end to end; safe to remove.

Part of [Claude Essentials](https://github.com/nerymurillohnd/claude-essentials), an independent community plugin marketplace for Claude Code. Not affiliated with or endorsed by Anthropic.

**Contents:** [Overview](#overview) · [Requirements](#requirements) · [Installation](#installation) · [Usage](#usage) · [Components](#components) · [Uninstall](#uninstall) · [Documentation](#documentation) · [License](#license)

<!-- END GENERATED: header -->

## Overview

A minimal plugin that exists to prove the Claude Essentials pipeline end to end: scaffolding, validation, the isolated install test and releases. Install it to check that the marketplace works in your Claude Code setup; it changes nothing and runs no tools. Maintainers remove it once real plugins cover the same pipeline.

## Requirements

<!-- BEGIN GENERATED: requirements -->

- Claude Code 2.1.289 or later.

<!-- END GENERATED: requirements -->

No other requirements.

## Installation

<!-- BEGIN GENERATED: installation -->

Inside a Claude Code session:

```text
/plugin marketplace add nerymurillohnd/claude-essentials
/plugin install hello-example@claude-essentials
```

From your shell:

```bash
claude plugin marketplace add nerymurillohnd/claude-essentials
claude plugin install hello-example@claude-essentials
```

Background auto-update is off for community marketplaces. Get fixes with `claude plugin update hello-example@claude-essentials`, or turn on **Enable auto-update** for `claude-essentials` under `/plugin` → **Marketplaces**.

<!-- END GENERATED: installation -->

## Usage

Run the skill with an optional name:

```text
/hello-example:hello Ada
```

Claude greets you by that name and confirms that `hello-example` from `claude-essentials` is installed and its skills load. Without a name it greets you as "there". The skill runs only when you invoke it.

## Components

<!-- BEGIN GENERATED: components -->

| Type  | Name                   | What it does                                                                                                                                                              |
| ----- | ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Skill | `/hello-example:hello` | Greets the user and confirms that plugins from the Claude Essentials marketplace load correctly. Use when the user runs /hello-example:hello to check their installation. |

<!-- END GENERATED: components -->

## Uninstall

<!-- BEGIN GENERATED: uninstall -->

```text
/plugin uninstall hello-example@claude-essentials
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

This plugin is released under the [MIT License](https://github.com/nerymurillohnd/claude-essentials/blob/main/LICENSE), like the rest of Claude Essentials. Third-party material is listed in [THIRD_PARTY_NOTICES.md](https://github.com/nerymurillohnd/claude-essentials/blob/main/THIRD_PARTY_NOTICES.md).

<!-- END GENERATED: license -->
