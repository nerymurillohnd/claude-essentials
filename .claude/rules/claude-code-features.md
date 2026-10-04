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
- `/doctor prompt-audit [path]` (2.1.283) reviews prompts written for older models, stale paths and stale commands; it is interactive, so use it as a review step for plugin content.
- The `verify` skill is skipped for docs-only and tests-only commits, and plugin skills do not count; ours runs `python3 scripts/check.py`.
- Verified on 2.1.289 on 2026-10-04 (docs and runtime); the automation built on them is in `.claude/rules/automation.md`:
  - Project `permissions.ask` rules are evaluated before the auto-mode classifier and always prompt; a saved "don't ask again" allow rule never overrides a project ask rule.
  - `claude plugin validate .claude --strict` validates the project's own skills and agents (2.1.233+).
  - Hook decisions: exit 2 or JSON `permissionDecision` blocks; exit 1, a missing script and a timeout do not.
  - `--restricted` drops Bash, the other code-running tools and WebFetch; the `default` preset of `--tools` does not bring them back, naming them does (`--tools default,Bash,WebFetch`).
  - Credentials are keyed to `CLAUDE_CONFIG_DIR`, so a session with an isolated config is not logged in; `claude plugin eval` runs each case with a temporary home and configuration.
  - Saved workflows in `.claude/workflows/<file>.js` run as `/<meta.name>`; `export const meta` must stay a plain literal.
  - Observed: an `agents` directory created mid-session became available without a restart, although the sub-agents page says a new directory needs one.
