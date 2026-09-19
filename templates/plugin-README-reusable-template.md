<!--
  Reusable plugin README template for claude-essentials — the master copy.
  The three shapes in templates/plugin-*/README.md are pre-filled instances of
  this file; keep them in sync when this file changes.

  HOW TO USE
  1. Copy to plugins/{{plugin-id}}/README.md, replace every {{placeholder}},
     and delete this comment.
  2. Keep every REQUIRED section, in this order, with these exact headings.
     A section that doesn't apply still says so explicitly ("None — this
     plugin ships no agents."). Never leave one empty or delete it: a plugin
     that doesn't state its limits misleads by omission.
       REQUIRED: What it does · What it does not do · Installation · Skills ·
       Agents · Hooks and side effects · MCP, permissions, and network ·
       Requirements · Verification · Compatibility · Examples · Security ·
       Limitations · Changelog · License
       OPTIONAL: Other components (only when present) · FAQ
  3. The **Kind:** line must match the kind `npm run validate` derives from
     the plugin's files: bundle | skill-only | agent-only (ADR-0001).
  4. Write for the person deciding whether to install: outcomes first, exact
     effects, no marketing. Every claim must be true of the published version.

  FORMATTING CONVENTIONS
  - Badge row: version (dynamic, reads plugin.json on main — never hardcode),
    license, kind, surfaces, then one badge per external requirement.
  - GitHub alerts: > [!NOTE] context · > [!TIP] shortcut · > [!IMPORTANT] must
    know before installing · > [!WARNING] risky default · > [!CAUTION]
    irreversible or data-affecting behavior. At most one alert per section.
  - Tables for anything with more than two attributes; `code` for names, paths,
    commands; **bold** for the one fact a skimmer must not miss; *italics*
    sparingly for terms.
  - Command blocks: `text` for prompts and slash commands typed inside Claude,
    `bash` for shell commands.
  - Status vocabulary (Compatibility, Verification): ✅ Supported · ⚠️ Partial ·
    🧪 Not tested · ❌ Not supported. "✅" requires a dated verification from an
    install of the REMOTE marketplace on that surface; never from --plugin-dir.

  REQUIREMENT BADGE CATALOG (shields.io; logos are simple-icons slugs — check
  https://simpleicons.org). Characters: "-" → "--", "_" → "__", space → "_",
  "≥" → %E2%89%A5.
    ![Node.js](https://img.shields.io/badge/Node.js-%E2%89%A522-5FA04E?logo=nodedotjs&logoColor=white)
    ![Python](https://img.shields.io/badge/Python-%E2%89%A53.12-3776AB?logo=python&logoColor=white)
    ![uv](https://img.shields.io/badge/uv-required-DE5FE9?logo=uv&logoColor=white)
    ![npm](https://img.shields.io/badge/npm-required-CB3837?logo=npm&logoColor=white)
    ![pnpm](https://img.shields.io/badge/pnpm-required-F69220?logo=pnpm&logoColor=white)
    ![Bash](https://img.shields.io/badge/Bash-%E2%89%A53.2-4EAA25?logo=gnubash&logoColor=white)
    ![jq](https://img.shields.io/badge/jq-%E2%89%A51.6-555555)
    ![Git](https://img.shields.io/badge/Git-%E2%89%A52.40-F05032?logo=git&logoColor=white)
    ![GitHub CLI](https://img.shields.io/badge/gh-required-181717?logo=github&logoColor=white)
    ![Ruff](https://img.shields.io/badge/Ruff-%E2%89%A50.16-D7FF64?logo=ruff&logoColor=black)
    ![ShellCheck](https://img.shields.io/badge/ShellCheck-%E2%89%A50.10-4EAA25)
    ![shfmt](https://img.shields.io/badge/shfmt-%E2%89%A53.12-00ADD8)
    ![Docker](https://img.shields.io/badge/Docker-required-2496ED?logo=docker&logoColor=white)
    ![MCP](https://img.shields.io/badge/MCP-{{server}}-000000?logo=modelcontextprotocol&logoColor=white)
    ![LSP](https://img.shields.io/badge/LSP-{{language--server}}-555555)
    ![Hooks](https://img.shields.io/badge/hooks-{{events}}-orange)
    ![Network](https://img.shields.io/badge/network-{{none|optional|required}}-lightgrey)
-->

# {{Emoji}} {{Display Name}}

[![Version](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2Fnerymurillohnd%2Fclaude-essentials%2Fmain%2Fplugins%2F{{plugin-id}}%2F.claude-plugin%2Fplugin.json&query=%24.version&label=version&color=blue)](CHANGELOG.md)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Kind](https://img.shields.io/badge/kind-{{bundle|skill--only|agent--only}}-8A2BE2)](../../docs/decisions/adr-0001-marketplace-distribution-model.md)
[![Claude Code](https://img.shields.io/badge/Claude_Code-{{status}}-D97757?logo=claude&logoColor=white)](#-compatibility)
[![Claude Cowork](https://img.shields.io/badge/Claude_Cowork-{{status}}-D97757?logo=claude&logoColor=white)](#-compatibility)
{{One requirement badge per external dependency, from the catalog above — or none.}}

[← claude-essentials](../../README.md) · [Install](#-installation) · [Skills](#-skills) ·
[Security](#-security) · [Limitations](#-limitations) · [Changelog](CHANGELOG.md)

> **{{One-sentence outcome, in the user's words: what they get, not how it's built.}}**

**Kind:** `{{bundle | skill-only | agent-only}}` — {{a full workflow: multiple components working together | exactly one skill, nothing else | exactly one subagent, nothing else}}.

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

| Skill | Invoke | Claude uses it when | Invocation |
| --- | --- | --- | --- |
| [`{{skill-name}}`](skills/{{skill-name}}/SKILL.md) | `/{{plugin-id}}:{{skill-name}}` | {{Trigger condition, in the user's words.}} | {{Claude + user \| user only \| Claude only}} |

{{Or: "None — this plugin ships no skills."}}

## 🤖 Agents

| Agent | Role | Tools | Model |
| --- | --- | --- | --- |
| [`{{agent-name}}`](agents/{{agent-name}}.md) | {{Bounded responsibility.}} | `{{Read, Grep, Glob}}` | `{{inherit}}` |

{{Or: "None — this plugin ships no agents."}}

## 🪝 Hooks and side effects

| Event | Matcher | What it does | Blocks? |
| --- | --- | --- | --- |
| `{{PostToolUse}}` | `{{Edit\|Write}}` | {{Exact action and files touched.}} | {{Yes/No — and on what}} |

{{Or: "None — this plugin registers no hooks and has no side effects beyond the
components' own actions described under Security."}}

## 🔌 MCP, permissions, and network

| Server | Transport | Endpoint | Auth | Tools and consequences |
| --- | --- | --- | --- | --- |
| `{{server}}` | `{{stdio \| http}}` | {{Command or URL}} | {{None \| OAuth \| token via `userConfig` (sensitive)}} | {{Each tool: what it reads or changes.}} |

- **Least privilege:** {{scopes or permissions actually required, and why}}.
- **Cowork:** {{verified working in Cowork | not tested in Cowork | not usable in Cowork, and why (e.g. needs a local process or private network)}}.

{{Or: "None — no MCP servers, no network access, no credentials."}}

## 🧩 Other components

<!-- OPTIONAL: keep only when the plugin ships LSP servers, monitors, commands,
     output styles, or settings.json. Delete otherwise. -->

| Component | Path | Purpose | Surface |
| --- | --- | --- | --- |
| {{LSP server}} | [`.lsp.json`](.lsp.json) | {{Language and binary.}} | Claude Code only |

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
| `{{triggers-on-natural-request}}` | Skill fires on natural phrasing | {{0.00}} | {{0.00}} | {{+0.00}} | {{YYYY-MM-DD, model}} |
| `{{ignores-unrelated-request}}` | Skill does **not** fire on unrelated work | {{0.00}} | {{0.00}} | {{0.00}} | {{YYYY-MM-DD, model}} |

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
