<!-- agent-only shape of templates/plugin-README-reusable-template.md (the master). Replace every {{placeholder}}; keep every section; delete this comment. -->

# {{Emoji}} {{Display Name}}

[![Version](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2Fnerymurillohnd%2Fclaude-essentials%2Fmain%2Fplugins%2F{{plugin-id}}%2F.claude-plugin%2Fplugin.json&query=%24.version&label=version&color=blue)](CHANGELOG.md)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Kind](https://img.shields.io/badge/kind-agent--only-8A2BE2)](../../docs/decisions/adr-0001-marketplace-distribution-model.md)
[![Claude Code](https://img.shields.io/badge/Claude_Code-{{status}}-D97757?logo=claude&logoColor=white)](#-compatibility)
[![Claude Cowork](https://img.shields.io/badge/Claude_Cowork-{{status}}-D97757?logo=claude&logoColor=white)](#-compatibility)
{{One requirement badge per external dependency, from the catalog above — or none.}}

[← claude-essentials](../../README.md) · [Install](#-installation) · [Agent](#-agents) ·
[Security](#-security) · [Limitations](#-limitations) · [Changelog](CHANGELOG.md)

> **{{One-sentence outcome, in the user's words: what they get, not how it's built.}}**

**Kind:** `agent-only` — exactly one subagent, nothing else.

{{Display Name}} helps {{target users}} {{do what, in which situation}}. It
{{primary behavior}}, and it does **not** {{the single most important non-goal}}.

> [!CAUTION]
> {{The single most important permission, hook, write, network, or data-loss
> boundary. Delete this alert only when the plugin is read-only and offline.}}

## 🎯 What it does

| Scenario | How this plugin helps | Expected result |
| --- | --- | --- |
| {{A concrete starting problem.}} | {{The behavior applied to it.}} | {{Observable outcome.}} |
| {{A second scenario.}} | {{Behavior.}} | {{Outcome.}} |

## 🚫 What it does not do

- **Does not** {{non-goal 1 — the thing users most often assume it does}}.
- **Does not** {{non-goal 2 — e.g. write outside X, call external services, run without approval}}.
- **Not a fit when** {{a situation where another tool is the better choice}}.

## ⚡ Installation

**Claude Code** — add the marketplace once, then install:

```text
/plugin marketplace add nerymurillohnd/claude-essentials
/plugin install {{plugin-id}}@claude-essentials
```

**Claude Cowork** — **Customize → Plugins → Add marketplace**, enter
`nerymurillohnd/claude-essentials`, then install **{{Display Name}}** from the list.

> [!TIP]
> Installation is complete when {{observable success signal — e.g. `/plugin list` shows `{{plugin-id}}` as enabled}}.

### What installing changes

| | Effect |
| --- | --- |
| **Does** | {{Claude Code/Cowork managed state only — e.g. "registers one skill and one hook".}} |
| **Does not** | {{What stays untouched until a component actually runs.}} |

### Update, disable, or remove

```text
/plugin marketplace update claude-essentials
/plugin disable {{plugin-id}}@claude-essentials
/plugin uninstall {{plugin-id}}@claude-essentials
```

In Cowork, use **Update** on the marketplace, and **Uninstall** on the plugin
under **Customize → Plugins**. {{State what uninstall does not revert, if anything.}}

## 🧠 Skills

None — this plugin ships exactly one subagent and no skills.

## 🤖 Agents

| Agent | Role | Tools | Model |
| --- | --- | --- | --- |
| [`agent-name`](agents/agent-name.md) | {{Bounded responsibility.}} | `{{Read, Grep, Glob}}` | `{{inherit}}` |

Claude delegates to it when {{trigger condition}}; you can also ask for it by name
(`@agent-name`) where your client supports mentions.

## 🪝 Hooks and side effects

None — this plugin registers no hooks and has no side effects beyond what [Security](#-security) lists.

## 🔌 MCP, permissions, and network

None — no MCP servers, no network access, no credentials.

## 📋 Requirements

| Requirement | Minimum | Check | Why |
| --- | --- | --- | --- |
| Claude Code | {{version, or "any with plugin support"}} | `claude --version` | {{Feature that needs it.}} |
| {{Tool}} | {{version}} | `{{tool --version}}` | {{Why this plugin calls it.}} |

{{When there are executable dependencies, add:}}

```bash
"${CLAUDE_PLUGIN_ROOT}"/scripts/check-requirements.sh
```

It only checks; it never installs anything or asks for credentials.

{{Or: "None beyond Claude Code or Cowork."}}

## ✅ Verification

**Consumer smoke test** — after installing from the remote marketplace, in {{a stated working directory}}:

```text
{{One verified prompt or command.}}
```

Expected result: {{observable outcome}}.

**Behavioral evals** — [`evals/`](evals/) runs with `claude plugin eval`, which compares a
run with the plugin against a baseline without it:

| Case | Checks | With | Without | Δ | Last run |
| --- | --- | ---: | ---: | ---: | --- |
| `{{delegates-on-natural-request}}` | Agent is delegated to on natural phrasing | {{0.00}} | {{0.00}} | {{+0.00}} | {{YYYY-MM-DD, model}} |
| `{{ignores-unrelated-request}}` | Agent is **not** used for unrelated work | {{0.00}} | {{0.00}} | {{0.00}} | {{YYYY-MM-DD, model}} |

<details>
<summary>Maintainer checks</summary>

From the marketplace root:

```bash
npm run check
claude plugin validate plugins/{{plugin-id}} --strict
claude plugin eval plugins/{{plugin-id}} --no-publish --max-cost-usd {{5}}
```

</details>

## 🧭 Compatibility

| Surface | Status | Last verified | Notes |
| --- | --- | --- | --- |
| Claude Code | {{✅ Supported}} | {{YYYY-MM-DD, Claude Code x.y.z}} | {{Notes.}} |
| Claude Cowork | {{🧪 Not tested}} | {{—}} | {{Which components are inactive there, e.g. LSP, monitors.}} |
| Claude Chat (web, desktop) | ❌ Not supported | — | Plugins aren't used in Chat. |

## 💡 Examples

**{{Example 1 title}}**

```text
{{Prompt the user types.}}
```

→ {{What Claude does and what the user sees.}}

**{{Example 2 title}}**

```text
{{Prompt.}}
```

→ {{Outcome.}}

## 🔐 Security

| Access | What it may do |
| --- | --- |
| Read | {{Exact paths, payloads, or project data read.}} |
| Write | {{Exact files or scope written — or "none".}} |
| Process | {{Commands or servers started — or "none".}} |
| Network | {{Destinations and purpose — or "not used".}} |
| Credentials | {{None, or which `userConfig` values (stored as sensitive).}} |

- **Human approval:** {{what runs only after the user approves it}}.
- **Trust:** review the current hook and script sources before enabling this in a critical repository.
- **Report a vulnerability** privately via the [security policy](../../SECURITY.md). Never post secrets in issues.

## 🚧 Limitations

| Limitation | What you'll see | Safe recovery |
| --- | --- | --- |
| {{Known limitation.}} | {{Observable symptom.}} | {{What to do.}} |

## ❓ FAQ

<!-- OPTIONAL: keep only questions users actually ask. -->

<details>
<summary>Does installing this plugin modify my project?</summary>

{{Precise answer.}}

</details>

## 📝 Changelog

Every published version is in [CHANGELOG.md](CHANGELOG.md), and each version is tagged
`{{plugin-id}}--v<version>`. Current version: see the badge above.

## 📄 License

[Apache-2.0](LICENSE) © {{copyright holder}}. {{Declare bundled third-party
material and its license here, or delete this sentence.}}

---

<sub>Part of [claude-essentials](../../README.md) · [Report an issue](https://github.com/nerymurillohnd/claude-essentials/issues/new/choose) · [Security](../../SECURITY.md) · Not an official Anthropic product.</sub>
