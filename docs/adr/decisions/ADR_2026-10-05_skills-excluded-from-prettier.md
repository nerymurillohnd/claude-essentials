---
status: accepted
date: 2026-10-05
decision-makers:
  - "Nery Samuel Murillo (maintainer)"
consulted:
  - "Claude Code by Anthropic (research, drafting and verification)"
---

# Skill folders and CLAUDE.md files excluded from Prettier

## Purpose

Keep content the model reads compact, by excluding every `skills/` folder and the `CLAUDE.md` and `CLAUDE.local.md` instruction files from Prettier while the rest of the repository stays under the `format` gate.

## Scope

Every path matching `**/skills/**`: plugin skills (`plugins/*/skills/`), the project's own skills (`.claude/skills/`) and the gate-test fixture's skills (`tests/fixtures/plugins/sample-plugin/skills/`). Also every `CLAUDE.md` (any depth) and `CLAUDE.local.md`, which load into every session; the maintainer added them later the same day. Agents, rules, READMEs, docs, JSON and YAML stay formatted.

## Context and problem statement

Prettier always pads Markdown tables so their columns align, and has no option to turn that off. Skills and their references are read by the model, not rendered for people: padding costs context on every load and pushes rules out of the first 5,000 tokens that auto-compaction keeps of each skill. Measured on `svelte-development` on 2026-10-05, table padding was 15.3 % of all skill and agent text, 29 % of `svelte-best-practices/SKILL.md` and 47 % of `known-doc-errata.md`. The project's skill-writing guidance asks for compact tables; the `format` gate required Prettier's padded ones.

## Decision drivers

- Context the model spends on whitespace instead of rules.
- Gates are never weakened to make a failure pass: the exclusion must be a deliberate, recorded scope change.
- Keep every other file formatted.

## Considered options

- Exclude `**/skills/**` from Prettier in `.prettierignore`
- Keep Prettier everywhere and write skill tables as lists
- Keep Prettier everywhere and accept the padding

## Decision outcome

Chosen option: **exclude `**/skills/**`, `CLAUDE.md` and `CLAUDE.local.md`**, decided by the maintainer in this session on 2026-10-05. Prettier reads `.prettierignore` together with `.gitignore`, both for `prettier --check .` in the `format` gate and for the formatting hook, which passes single files and skips ignored ones. Skill tables are written compact (`| a | b |`, separator `|---|---|`).

### Consequences

- Good, because skills load with less whitespace and keep their tables.
- Bad, because nothing checks the formatting of skill files any more; `claude plugin validate --strict`, the `repo` gate (portability, placeholders) and the `docs` gate (links) still run on them.

### Confirmation

`prettier --file-info <skill file>` reports `"ignored": true`; `scripts/check.py format` passes. Revisit if Prettier adds an option to keep tables unaligned.

## Pros and cons of the options

### Exclude skill folders

- Good, because tables stay tables and cost less.
- Bad, because skill Markdown loses automatic formatting.

### Lists instead of tables

- Good, because the gate stays as it was.
- Bad, because maps, errata and comparisons lose their structure.

### Accept the padding

- Good, because nothing changes.
- Bad, because every load pays for the whitespace.

## More information

Prettier ignore files: https://prettier.io/docs/ignore. Skill size and compaction limits: https://code.claude.com/docs/en/skills.
