<!--
  Reusable root README template for claude-essentials.

  This is the structure the repo's actual README.md follows. When the
  catalog grows, update README.md to match this shape rather than letting
  the two drift — this file documents the intended shape, README.md is the
  live instance.
-->

# 🧩 claude-essentials

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> A Git-backed marketplace of Claude Code plugins, skills, and agents.

**Explore:** [Plugins](#-plugin-catalog) · [Install](#-quick-start) ·
[Documentation](#-documentation-map) · [Contribute](#-contributing) ·
[Support](#-support-and-project-links)

claude-essentials is for people who want to extend Claude Code with focused,
installable capabilities instead of rebuilding the same workflow each time.

Every entry in the catalog is a plugin (Claude Code's only distribution unit),
but three different *kinds* ship through that one mechanism — see
[ADR-0001](docs/decisions/adr-0001-marketplace-distribution-model.md):

| Kind | What installing it gives you |
|---|---|
| `bundle` | Multiple skills/agents/commands/hooks working together |
| `skill-only` | Exactly one skill, nothing else |
| `agent-only` | Exactly one subagent, nothing else |

Each plugin's README explains what it does, what it can access, which tools
it needs, and what side effects or approvals apply.

## 🧩 Plugin catalog

| Plugin | Kind | Best for | Install ID |
| --- | --- | --- | --- |
| [{{Display Name}}](plugins/{{plugin-id}}/README.md) | `{{kind}}` | {{User-facing outcome summary.}} | `{{plugin-id}}` |

_Choose a plugin by outcome, then open its linked README for requirements,
permissions, side effects, and examples._

## ⚡ Quick start

Add the marketplace and install the plugin you need:

```
/plugin marketplace add nerymurillohnd/claude-essentials
/plugin install <plugin-id>@claude-essentials
/plugin list
```

`main` exposes the current catalog and is the supported installation reference.

Read the linked plugin README before installing a plugin with hooks, file
writes, network access, or other side effects.

## 🔁 Update, disable, or remove

```
/plugin marketplace update claude-essentials
/plugin disable <plugin-id>@claude-essentials
/plugin uninstall <plugin-id>@claude-essentials
/plugin marketplace remove claude-essentials
```

See the [official Claude Code plugin docs](https://code.claude.com/docs/en/discover-plugins)
for current host, marketplace, manifest, and distribution behavior.

## 📦 What is included

| Path | Role |
| --- | --- |
| `.claude-plugin/marketplace.json` | Generated catalog — do not hand-edit `plugins[]`. |
| `SECURITY.md` | Vulnerability reporting channel and scope. |
| `CODE_OF_CONDUCT.md` | Community standards and enforcement. |
| `plugins/<plugin-id>/` | Self-contained distributable plugin packages. |
| `plugins/*/.claude-plugin/plugin.json` | Authored plugin identity, version, and component declarations. |
| `docs/` | Architecture, contributor, and decision documentation. |
| `schemas/`, `scripts/`, `templates/` | Repository schemas, generators, validators, and starting points. |
| `.github/` | CI: Biome + catalog generation/validation on every PR. |

The schemas, generator, and validator in this repository are maintainer
tooling used to build and check the marketplace. They are not installed into
a user's project — installing a plugin only brings that plugin's own declared
components.

## 🧭 Documentation map

| Need | Start here |
| --- | --- |
| Choose or install a plugin | This README and the plugin catalog above. |
| Understand plugin behavior | The plugin's `README.md`, then its `SKILL.md` or agent file. |
| Contribute or maintain packages | [docs/contributing/plugins.md](docs/contributing/plugins.md). |
| Review decisions | [docs/decisions/](docs/decisions/). |
| Review maintenance status | [docs/maintenance/](docs/maintenance/). |

## 🤝 Contributing

```bash
npm install
npm run check
```

For a plugin change, update its manifest, README, and changelog together,
then run `npm run check`. The catalog is generated from validated package
manifests — don't hand-edit generated metadata.

See [docs/contributing/plugins.md](docs/contributing/plugins.md) for the full
walkthrough.

## ❓ FAQ

<details>
<summary>Can I install just one skill, or just one agent?</summary>

Yes — look for `kind: skill-only` or `kind: agent-only` in the catalog table.
Installing that plugin gives you exactly that one component, nothing else.
See [ADR-0001](docs/decisions/adr-0001-marketplace-distribution-model.md) for
why this is a plugin either way.
</details>

<details>
<summary>Does installing a plugin change anything outside Claude Code's own config?</summary>

No, unless the plugin's own README says otherwise. Read each plugin's
permissions/boundaries section before installing.
</details>

## 🔒 Security

Report a vulnerability privately — see [SECURITY.md](SECURITY.md). Don't open
a public issue for an unpatched one.

## 🆘 Support and project links

- [Issues](https://github.com/nerymurillohnd/claude-essentials/issues)
- [Security policy](SECURITY.md)
- [Code of Conduct](CODE_OF_CONDUCT.md)
- [MIT License](LICENSE)

claude-essentials is community-maintained and is not an official Anthropic
product.
