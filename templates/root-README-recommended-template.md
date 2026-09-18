<!--
  Reusable root README template for claude-essentials — the master copy.
  README.md at the repository root is the live instance: when this file
  changes, update README.md in the same PR so the two never drift.

  REQUIRED SECTIONS (in order): What this is · Plugin catalog · Quick start ·
  Update, disable, or remove · Compatibility · Requirements · Support policy ·
  Security · Documentation map · Repository layout · Contributing · FAQ ·
  License. The public-repository alert under the header is required too.

  Formatting follows templates/plugin-README-reusable-template.md: dynamic
  badges (never hardcoded counts or versions), one GitHub alert per section at
  most, tables for multi-attribute data, `text` blocks for commands typed in
  Claude and `bash` blocks for shell.

  CATALOG ROWS: one per plugin, sorted by name. Columns follow the plugin's
  README: Claude Code / Claude Cowork use its Compatibility status vocabulary
  (✅ Supported · ⚠️ Partial · 🧪 Not tested · ❌ Not supported), and
  "Additional requirements" lists its Requirements beyond Claude itself, or
  "None".
-->

<div align="center">

# 🧩 claude-essentials

**Top-tier Claude plugins, skills, and agents — in one public, versioned marketplace.**

[![CI](https://github.com/nerymurillohnd/claude-essentials/actions/workflows/ci.yml/badge.svg)](https://github.com/nerymurillohnd/claude-essentials/actions/workflows/ci.yml)
[![Plugins](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2Fnerymurillohnd%2Fclaude-essentials%2Fmain%2F.claude-plugin%2Fmarketplace.json&query=%24.plugins.length&label=plugins&color=8A2BE2)](#-plugin-catalog)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Claude Code](https://img.shields.io/badge/Claude_Code-supported-D97757?logo=claude&logoColor=white)](#-compatibility)
[![Claude Cowork](https://img.shields.io/badge/Claude_Cowork-per_plugin-D97757?logo=claude&logoColor=white)](#-compatibility)
[![PRs welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

[Catalog](#-plugin-catalog) · [Install](#-quick-start) · [Compatibility](#-compatibility) ·
[Docs](#-documentation-map) · [Contribute](#-contributing) · [Security](#-security)

</div>

> [!IMPORTANT]
> **This is a public repository.** Everything here — plugins, issues, pull
> requests — is visible to anyone. Never post secrets, tokens, private paths,
> or customer data in an issue or PR. claude-essentials is community-maintained
> and is **not** an official Anthropic product.

## 🎯 What this is

claude-essentials is a Git-hosted plugin marketplace for **Claude Code** and
**Claude Cowork**. Add it once, then install only the plugins you need —
each one is self-contained, explicitly versioned, and documents exactly what it
reads, writes, and reaches over the network.

Every entry is a plugin (Claude's only distribution unit), in one of three
kinds ([ADR-0001](docs/decisions/adr-0001-marketplace-distribution-model.md)):

| Kind | Installing it gives you |
| --- | --- |
| `bundle` | Several skills, agents, hooks, or servers that work together |
| `skill-only` | Exactly one skill, nothing else |
| `agent-only` | Exactly one subagent, nothing else |

## 🧩 Plugin catalog

| Plugin | Description | Kind | Claude Code | Claude Cowork | Additional requirements |
| --- | --- | --- | :---: | :---: | --- |
| [{{Display Name}}](plugins/{{plugin-id}}/README.md) | {{One-line outcome.}} | `{{kind}}` | {{✅}} | {{🧪}} | {{None}} |

Pick by outcome, then read the plugin's README — **What it does not do**,
**Security**, and **Limitations** — before installing anything with hooks,
file writes, or network access.

## ⚡ Quick start

**Claude Code**

```text
/plugin marketplace add nerymurillohnd/claude-essentials
/plugin install <plugin-id>@claude-essentials
/plugin list
```

**Claude Cowork** — open **Customize → Plugins → Add marketplace**, enter
`nerymurillohnd/claude-essentials` (or `https://github.com/nerymurillohnd/claude-essentials`),
then install plugins from the list.

> [!WARNING]
> Add the marketplace by its **Git** address as shown above, never by a raw
> `marketplace.json` URL. A URL-based marketplace fetches only that one file, so
> plugins with relative sources — every plugin here — can't be resolved.

## 🔁 Update, disable, or remove

| Action | Claude Code | Claude Cowork |
| --- | --- | --- |
| Refresh the catalog | `/plugin marketplace update claude-essentials` | **Update** on the marketplace |
| Update a plugin | `/plugin update <plugin-id>@claude-essentials` | Checked automatically against the marketplace |
| Turn one off | `/plugin disable <plugin-id>@claude-essentials` | Disable its components in the plugin page |
| Remove one | `/plugin uninstall <plugin-id>@claude-essentials` | **Uninstall** under **Customize → Plugins** |
| Remove the marketplace | `/plugin marketplace remove claude-essentials` | — |

Plugins use explicit semantic versions: an installed plugin only changes when
its `version` does ([versioning](docs/contributing/versioning.md)).

## 🧭 Compatibility

Plugins run in **Claude Code** and **Claude Cowork**. They aren't used in
Claude Chat (web or desktop). Each plugin's README states the surfaces it was
actually verified on; which components it ships decides where it can work:

| Component | Claude Code | Claude Cowork |
| --- | :---: | :---: |
| Skills | ✅ | ✅ |
| Subagents | ✅ | ✅ |
| Hooks | ✅ | ✅ |
| MCP servers (connectors) | ✅ | ✅ — the plugin's README states any reachability or sign-in limits |
| LSP servers, monitors, `bin/` executables, plugin `settings.json` | ✅ | ❔ not listed in Cowork's docs — treat as Claude Code only |

<sub>Sources: [Cowork: install plugins](https://claude.com/docs/cowork/guide/plugins) ·
[Claude Code: plugins reference](https://code.claude.com/docs/en/plugins-reference). Verified 2026-09-18.</sub>

## 📋 Requirements

| Requirement | Details |
| --- | --- |
| Claude Code or Claude Cowork | A version with plugin marketplace support. This repo validates against the Claude Code version pinned as `CLAUDE_CODE_VERSION` in [`ci.yml`](.github/workflows/ci.yml). |
| Git access to GitHub | To add and update the marketplace. |
| Per-plugin requirements | Listed in the catalog and in each plugin's **Requirements** section, with a check command for each. |

## 🛟 Support policy

| | |
| --- | --- |
| **Supported** | The latest version of each plugin on `main`, on the surfaces its README marks ✅. |
| **Not supported** | Older plugin versions (update first), untested surfaces, and plugins loaded from a local checkout. |
| **Questions** | [Discussions](https://github.com/nerymurillohnd/claude-essentials/discussions) |
| **Bugs and requests** | [Issue forms](https://github.com/nerymurillohnd/claude-essentials/issues/new/choose) — see [issues.md](docs/contributing/issues.md) |
| **Response** | Best effort by the maintainer; there is no SLA. |

## 🔒 Security

> [!CAUTION]
> Plugins run with your permissions. Read a plugin's **Security** section and
> review its hooks and scripts before enabling it in a critical repository.

Report a vulnerability **privately** through
[GitHub Security Advisories](https://github.com/nerymurillohnd/claude-essentials/security/advisories/new),
as described in [SECURITY.md](SECURITY.md). Don't open a public issue for an
unpatched one, and never include secrets in any report.

## 📚 Documentation map

| I want to… | Start here |
| --- | --- |
| Choose and install a plugin | The [catalog](#-plugin-catalog), then the plugin's README |
| Understand a plugin's behavior | Its README, then its `SKILL.md` or agent file |
| Add or change a plugin | [CONTRIBUTING.md](CONTRIBUTING.md) → [plugins.md](docs/contributing/plugins.md) → [versioning.md](docs/contributing/versioning.md) |
| Report a problem or propose a plugin | [Issue forms](https://github.com/nerymurillohnd/claude-essentials/issues/new/choose) |
| Understand why things are built this way | [Decision records](docs/decisions/) |
| Check open maintenance work | [Maintenance ledgers](docs/maintenance/) |

## 📦 Repository layout

| Path | Role |
| --- | --- |
| [`plugins/<plugin-id>/`](plugins/) | Self-contained, distributable plugins |
| [`.claude-plugin/marketplace.json`](.claude-plugin/marketplace.json) | The catalog Claude reads — generated from each `plugin.json`, never hand-edited |
| [`schemas/`](schemas/) | This repo's manifest contract, plus [upstream-faithful Claude Code schemas](schemas/claude-code/) |
| [`scripts/`](scripts/), [`templates/`](templates/) | Maintainer tooling and starting points — never installed into your project |
| [`docs/`](docs/) | Decisions, contributor guides, maintenance ledgers, audits |
| [`.github/`](.github/) | CI, issue forms, labels, triage |

## 🤝 Contributing

```bash
npm install
npm run check
```

Every change to what Claude loads bumps the plugin's `version` and adds a dated
CHANGELOG entry. CI enforces this and tags `<plugin-id>--v<version>` on merge.
Start with [CONTRIBUTING.md](CONTRIBUTING.md).

## ❓ FAQ

<details>
<summary>Can I install just one skill, or just one agent?</summary>

Yes — pick a `skill-only` or `agent-only` plugin from the catalog. Installing it
gives you exactly that one component. See
[ADR-0001](docs/decisions/adr-0001-marketplace-distribution-model.md) for why it's
still a plugin.

</details>

<details>
<summary>Does installing a plugin change my project?</summary>

No. Installing only registers the plugin with Claude. A plugin acts on a project
when one of its components runs, as described in its README's **Security**
section.

</details>

<details>
<summary>How do I get updates?</summary>

Refresh the marketplace, then update the plugin (see
[Update, disable, or remove](#-update-disable-or-remove)). You only receive a new
version when the plugin's `version` changes.

</details>

## 📄 License

[Apache-2.0](LICENSE). Each plugin carries its own `LICENSE` with the same terms
([ADR-0005](docs/decisions/adr-0005-apache-2-0-license.md)).

---

<div align="center"><sub>Maintained by <a href="https://github.com/nerymurillohnd">Nery Samuel Murillo Tejada</a> · Not an official Anthropic product · <a href="CODE_OF_CONDUCT.md">Code of Conduct</a></sub></div>
