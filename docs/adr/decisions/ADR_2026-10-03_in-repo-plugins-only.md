---
status: accepted
date: 2026-10-03
decision-makers:
  - "Nery Samuel Murillo (maintainer)"
---

# In-repository plugins only

## Purpose

Decide where plugin code lives and which plugin sources the catalog may use.

## Scope

`plugins/<name>/`, the `source` of every entry in `.claude-plugin/marketplace.json`, and contribution rules.

## Context and problem statement

A marketplace entry can point at a relative path, a GitHub repository, a git URL, a git subdirectory, an npm package, an archive or a command. External sources can change outside this repository's review.

## Decision drivers

- Every line users install must pass this repository's gates and review.
- Security review of hooks, MCP servers and mods must see the exact code users get.
- Simple, predictable versioning and tagging.

## Considered options

- Relative-path sources under `plugins/<name>/` only
- Also external sources pinned to a commit SHA

## Decision outcome

Chosen option: **relative-path sources under `plugins/<name>/` only**. Every entry's `source` is exactly `./plugins/<name>`.

### Consequences

- Good, because portability, self-containment, security and release gates run on the real code.
- Good, because `plugin.json` can be read before install for relative-path entries, so users see full metadata.
- Bad, because authors who prefer their own repositories must contribute here instead.

### Confirmation

`scripts/check_repo.py` fails on any other `source`. Revisit with a new ADR if external sources become necessary; a pinned `sha` would then be mandatory.

## Pros and cons of the options

### In-repo only

- Good, because review covers everything shipped.
- Bad, because the repository grows with every plugin.

### External sources pinned by SHA

- Good, because authors keep their repositories.
- Bad, because gates only see metadata, and each update needs a catalog change anyway.

## More information

Docs: [Plugin sources](https://code.claude.com/docs/en/plugins/marketplace-reference#plugin-sources).
