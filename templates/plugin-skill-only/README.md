# {{Emoji}} {{Display Name}}

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE.md)
[← Back to claude-essentials](../../README.md)

> {{One-sentence outcome in the user's language.}}

**Kind:** `skill-only` — installing this plugin gives you exactly one skill, nothing else.

{{Plugin name}} is a Claude Code skill for {{target users and task}}. It
{{primary behavior}} and does not {{important non-goal or boundary}}.

## ⚡ Quick start

```
/plugin marketplace add nerymurillohnd/claude-essentials
/plugin install {{plugin-id}}@claude-essentials
```

Installation is complete when: {{observable success signal.}}

Claude invokes it automatically when {{triggering condition}}, or you can run
it directly:

```text
/{{skill-name}}
```

## 🧰 Included components

| Component | Purpose |
| --- | --- |
| [`skills/skill-name/SKILL.md`](skills/skill-name/SKILL.md) | Authoritative behavior and triggering conditions. |

## 🔐 Behavior and boundaries

### Installation effects

Installing this plugin: {{effect on Claude Code's own managed state — usually just "registers the skill."}}

### Runtime effects on a target project

| Access or effect | What this skill may do |
| --- | --- |
| Read | {{Exact paths, payloads, or project data read.}} |
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
