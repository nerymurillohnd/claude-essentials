# {{Emoji}} {{Display Name}}

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE.md)
[← Back to claude-essentials](../../README.md)

> {{One-sentence outcome in the user's language.}}

**Kind:** `bundle` — a full workflow: multiple skills/agents/commands/hooks working together.

{{Plugin name}} is a Claude Code plugin for {{target users and task}}. It
{{primary behavior}} and does not {{important non-goal or boundary}}.

> [!CAUTION]
> {{One concise statement of the most important permission, hook, write, network,
> or data-loss boundary. Omit this alert only when the plugin has no meaningful
> risk beyond ordinary read-only operation.}}

## ⚡ Quick start

```
/plugin marketplace add nerymurillohnd/claude-essentials
/plugin install {{plugin-id}}@claude-essentials
```

```text
{{One canonical example prompt or action.}}
```

## 🧰 Included components

| Component | Purpose |
| --- | --- |
| [`skills/skill-name/SKILL.md`](skills/skill-name/SKILL.md) | Replace with a real skill, or delete if unused. |
| [`agents/agent-name.md`](agents/agent-name.md) | Replace with a real agent, or delete if unused. |

## 🔐 Behavior and boundaries

| Access or effect | What this plugin may do |
| --- | --- |
| Read | {{Exact paths, payloads, or project data read.}} |
| Write | {{Exact files or target scope written; say "none" if none.}} |
| Network | {{Destinations and purpose; say "not used" if none.}} |

## 🔁 Update, disable, or remove

```
/plugin disable {{plugin-id}}@claude-essentials
/plugin uninstall {{plugin-id}}@claude-essentials
```

## 📄 License

MIT. See [LICENSE.md](LICENSE.md).
