---
status: superseded
date: 2026-10-03
decision-makers:
  - "Nery Samuel Murillo (maintainer)"
superseded-by: ADR_2026-10-07_no-pinned-claude-code-version.md
---

# Minimum Claude Code version 2.1.289 for tooling and new plugins

## Purpose

Fix the Claude Code version the repository tooling relies on and the default minimum new plugins declare.

## Scope

`repo.MIN_CLAUDE_CODE` (used by `scripts/check.py` to install Claude Code on CI), `CLAUDE_CODE_VERSION` in the release workflow, `metadata.minClaudeCodeVersion` in new plugins.

## Context and problem statement

The full release notes from 2.1.280 to 2.1.289 show validator fixes this repository depends on: names Claude Code cannot install now fail (2.1.283), `outputStyles`, `themes`, `monitors` and `lspServers` paths are checked (2.1.283), MCP checks and the unquoted `${CLAUDE_PLUGIN_ROOT}` warning (2.1.281), and the plugin was skipped when its folder also held a marketplace manifest (fixed in 2.1.289).

## Decision drivers

- The validator must actually check what the gates assume it checks.
- Users need an honest minimum version in each plugin README.

## Considered options

- Pin 2.1.289 for tooling and default new plugins to it
- Track the latest release automatically

## Decision outcome

Chosen option: **pin 2.1.289**. CI installs exactly this version with the official installer. New plugins declare `metadata.minClaudeCodeVersion` 2.1.289, which authors may lower only after testing on that version. Mods must declare at least 2.1.287.

### Consequences

- Good, because CI results are reproducible.
- Bad, because the pin must be raised deliberately, after the docs-and-changelog routine in CLAUDE.md.

### Confirmation

`repo.MIN_CLAUDE_CODE` and the release workflow pin change together in one pull request that records the reviewed changelog window in `.claude/rules/claude-code-version.md`.

## Pros and cons of the options

### Pinned version

- Good, because a new release cannot break CI without review.
- Bad, because the repository may lag behind new validator checks until the pin moves.

### Latest release

- Good, because new checks arrive immediately.
- Bad, because unreviewed behavior changes can break or silently weaken gates.

## More information

Docs: [Claude Code changelog](https://code.claude.com/docs/en/changelog).

Pointer note (2026-10-05): [ADR unpinned-tooling-and-shebang-interpreters](ADR_2026-10-05_unpinned-tooling-and-shebang-interpreters.md) replaces the part of this record in which CI installs exactly the pinned version: CI now installs the latest Claude Code. `repo.MIN_CLAUDE_CODE` remains the minimum new plugins declare. Approved by the maintainer in the Claude Code session of 2026-10-05.
