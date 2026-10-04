---
status: accepted
date: 2026-10-03
decision-makers:
  - "Nery Samuel Murillo (maintainer)"
---

# Clean-room policy for Claude Code content

## Purpose

Keep the marketplace independent: every Claude Code specific comes from official sources, never from other plugin collections.

## Scope

Marketplace and manifest schema, plugin structure and components, validation, distribution, and any plugin content contributed to this repository.

## Context and problem statement

Other plugin collections exist. Copying or imitating them would import their assumptions, possible license problems and outdated behavior, and would make this marketplace a derivative instead of an independent project.

## Decision drivers

- Correctness: official docs and the changelog are the only authoritative sources for Claude Code behavior.
- Independence and licensing hygiene.
- Reproducibility: every rule traces to a dated official source.

## Considered options

- Official docs and changelog only, plus runtime verification
- Also learn from other plugin collections

## Decision outcome

Chosen option: **official docs and changelog only, plus runtime verification**. Contributors and maintainers do not reference, browse, copy or imitate any other Claude Code or AI-assistant marketplace or plugin collection. Generic repository engineering (READMEs, changelogs, CI, licenses) is exempt and follows [ADR 0004](0004-sourcing-policy.md). Pasted material from other projects is checked before use, and anything platform-specific to another assistant is rejected.

### Consequences

- Good, because every Claude Code statement in the repository has an official source and date.
- Bad, because good ideas from other collections cannot be adopted directly; they must be rediscovered from the docs.

### Confirmation

Reviewers check sources in pull requests; the pull request template asks for them. The docs-and-changelog routine in CLAUDE.md runs before any schema, release or component work.

## Pros and cons of the options

### Official sources only

- Good, because nothing depends on another project's interpretation.
- Bad, because it takes more research per change.

### Learn from other collections

- Good, because it is faster.
- Bad, because it copies their mistakes and blurs licensing and independence.

## More information

Official sources: [Claude Code docs index](https://code.claude.com/docs/llms.txt) and [changelog](https://code.claude.com/docs/en/changelog).
