# {{Emoji}} {{Display Name}}

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE.md)
[← Back to claude-essentials](../../README.md)

> {{One-sentence outcome in the user's language.}}

**Kind:** `agent-only` — installing this plugin gives you exactly one subagent, nothing else.

{{Plugin name}} is a Claude Code subagent for {{target users and task}}. It
{{primary behavior}} and does not {{important non-goal or boundary}}.

## ⚡ Quick start

```
/plugin marketplace add nerymurillohnd/claude-essentials
/plugin install {{plugin-id}}@claude-essentials
```

Installation is complete when: {{observable success signal.}}

Claude delegates to it automatically when {{triggering condition}}, or invoke
it explicitly via the Agent tool / `@{{agent-name}}` where your client supports it.

## 🧰 Included components

| Component | Purpose |
| --- | --- |
| [`agents/agent-name.md`](agents/agent-name.md) | Subagent role, tools, and instructions. |

## 🔐 Behavior and boundaries

### Installation effects

Installing this plugin: {{effect on Claude Code's own managed state — usually just "registers the subagent."}}

### Runtime effects on a target project

| Access or effect | What this subagent may do |
| --- | --- |
| Tools | {{List the tools this agent is granted and why.}} |
| Write | {{Exact files or target scope written; say "none" if none.}} |
| Network | {{Destinations and purpose; say "not used" if none.}} |

## ✅ Verification

### Consumer smoke test

```text
{{one verified prompt to confirm this works}}
```

Expected result: {{observable outcome}}.

## 🚧 Known limitations

| Limitation | Observable symptom | Safe recovery |
| --- | --- | --- |
| {{Known limitation 1.}} | {{What the user sees.}} | {{What to do about it.}} |

## 🔁 Update, disable, or remove

```
/plugin disable {{plugin-id}}@claude-essentials
/plugin uninstall {{plugin-id}}@claude-essentials
```

## 📄 License

MIT. See [LICENSE.md](LICENSE.md).
