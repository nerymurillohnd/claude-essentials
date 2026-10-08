---
name: sync-docs
description: Finds and fixes drift between the claude-essentials code and its documentation - gate lists, script names, rule paths, links, guides, rules, ADRs, the sourcing log and CLAUDE.md Current state. Use after changing scripts, gates, tooling, workflows or rules, before a commit that touches them, or when asked to sync, update or audit the docs.
---

# Sync the documentation

The code is the source of truth; documents follow it. Mechanical drift is caught by the `docs` gate; meaning drift needs reading.

```
- [ ] 1 Mechanical   scripts/check_docs.py; fix at the source of truth
- [ ] 2 Changed      for each changed file, update the docs that describe it
- [ ] 3 Records      sourcing log, ADR, rule dates, Current state
- [ ] 4 Deep audit   /drift-audit when many docs changed or before a release
- [ ] 5 Verify       scripts/check.py
```

1. **Mechanical.** Run `scripts/check_docs.py`. Each line names a file and the value it must have. Fix the copy, not the constant, unless the constant is what changed.
2. **Changed files.** List them with `git diff --name-only main...HEAD` plus `git status --short`. For each, update what describes it:

   | Changed | Update |
   | --- | --- |
   | `scripts/*.py`, a gate | `docs/testing.md`, `.claude/rules/testing/gates.md` (`.claude/rules/testing/drive-plugin.md` for `drive_plugin.py`), CLAUDE.md Commands, the script's docstring |
   | Release flow | `docs/releasing.md`, `.claude/skills/plugin-versioning`, `.claude/skills/release-plugin`, `.claude/rules/releasing.md` |
   | Hooks, settings, skills, agents, workflows | `.claude/rules/automation.md`, CLAUDE.md Read before acting |
   | Repository settings, rulesets, Actions allowlist | `.claude/rules/ci-github.md` |
   | A tool or template added | `docs/sourcing-log.md`, `THIRD_PARTY_NOTICES.md` |
   | A decision | a new dated ADR from `templates/adr/`; mark the old one `superseded` |
   | A Claude Code fact | the rule in `.claude/rules/`, with date and version |

3. **Records.** Rewrite CLAUDE.md "Current state" to the repository's real state (what passes, what is open, what awaits the maintainer). Run `scripts/validate_adrs.py` after an ADR change.
4. **Deep audit.** For drift a pattern cannot catch (a guide that describes a flow the code no longer has), ask the maintainer to start the `/drift-audit` workflow (workflows run many agents and start only on request) and fix what it confirms.
5. **Verify.** `scripts/check.py` must pass; report the raw summary line.

## Gotchas

- Read documents with the Read tool: path-scoped rules in `.claude/rules/` load on Read, Write and Edit and, since 2.1.293, when one file is viewed with `cat`, `head`, `tail`, `sed -n` or `grep`.
- Never edit between `BEGIN GENERATED` and `END GENERATED`; run `scripts/sync_readmes.py`.
- CLAUDE.md stays under 200 lines; procedures belong in skills, area facts in path-scoped rules.
