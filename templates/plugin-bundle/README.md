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

Installation is complete when: {{observable success signal.}}

```text
{{One canonical example prompt or action.}}
```

## 🧰 Included components

| Component | Purpose |
| --- | --- |
| [`skills/skill-name/SKILL.md`](skills/skill-name/SKILL.md) | Replace with a real skill, or delete if unused. |
| [`agents/agent-name.md`](agents/agent-name.md) | Replace with a real agent, or delete if unused. |

## 🔐 Behavior and boundaries

### Installation effects

Installing this plugin: {{effect on Claude Code's own managed state.}}

Installing this plugin does **not** by itself: {{what stays untouched until it actually runs.}}

### Runtime effects on a target project

| Access or effect | What it may do |
| --- | --- |
| Read | {{Exact paths, payloads, or project data read.}} |
| Write | {{Exact files or target scope written; say "none" if none.}} |
| Network | {{Destinations and purpose; say "not used" if none.}} |

## ✅ Verification

### Consumer smoke test

```text
{{one verified prompt or command to confirm this works}}
```

Expected result: {{observable outcome}}.

### Maintainer checks

```bash
npm run check
```

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
