---
paths:
  - "CLAUDE.md"
  - "AGENTS.md"
  - ".claude/**"
---

# Other Claude Code features this repository uses

- A project skill named `verify` (or `simplify`) runs before every commit since 2.1.286.
- `AGENTS.md` is read only if there is no `CLAUDE.md` or if `CLAUDE.md` imports it (2.1.277+).
- Rules in `.claude/rules` with `paths:` also load on Write or Edit (2.1.288).
- `/doctor prompt-audit` (2.1.283) reviews prompts written for older models, stale paths and stale commands.
