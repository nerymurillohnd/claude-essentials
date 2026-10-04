---
status: accepted
date: 2026-10-04
decision-makers:
  - "Nery Samuel Murillo (maintainer)"
---

# Claude Code automation for maintaining the marketplace

## Purpose

Decide which Claude Code features the repository uses to maintain itself, so the maintainer and Claude scaffold, review, release and document the marketplace the same way every session and the rules in CLAUDE.md are enforced by configuration rather than by memory.

## Scope

`.claude/settings.json`, `scripts/claude_hooks.py`, `scripts/check_docs.py` (the `docs` gate), `scripts/drive_plugin.py`, `scripts/add_component.py`, the project skills and agent in `.claude/`, the saved workflows in `.claude/workflows/`, `.claude/rules/automation.md`, and the branch convention. Plugins shipped to users are out of scope: these files maintain the repository and are never distributed.

## Context and problem statement

The repository is maintained by one person and Claude Code. Its rules (signed commits, no publication without approval for that exact action, versions only through `bump_version.py`, generated README blocks only through `sync_readmes.py`, a clean room against the maintainer's earlier projects, docs that match the code) lived in CLAUDE.md, rules and skills, so they held only as long as the model remembered them. Copies of pins, gate lists and script names were spread over the docs with nothing to catch drift. Claude Code 2.1.289 offers permission rules, hooks, project skills, subagents and saved dynamic workflows that can carry these rules. Which of them should the repository adopt, and how?

## Decision drivers

- Hard rules belong in configuration Claude Code enforces, not in prose: permission `ask` rules are evaluated before the auto-mode classifier and always prompt (official docs, auto-mode-config).
- Repository tooling stays standard-library Python under `scripts/`, covered by ruff, basedpyright and the gate tests.
- Nothing may install or enable this repository's plugins in the maintainer's configuration, publish anything, or read the forbidden sources.
- Procedures belong in skills, area facts in path-scoped rules, and CLAUDE.md keeps facts every session needs.
- Every automation must be testable without a model call where possible, and demonstrated where not.

## Considered options

- Permission rules plus stdlib hooks, project skills, one review agent, saved workflows and a `docs` gate
- Prose only (CLAUDE.md and skills), no hooks or settings
- A plugin of our own installed in the maintainer's configuration for this tooling
- Mods (in-process TypeScript) for the guards and a status pane

## Decision outcome

Chosen option: **permission rules plus stdlib hooks, project skills, one review agent, saved workflows and a `docs` gate**, because it enforces the rules mechanically, stays inside the repository's existing toolchain and gates, and installs nothing in the maintainer's configuration.

- `.claude/settings.json`: `permissions.ask` for every push, pull request, release, label, workflow run, tag push and GitHub MCP write; `permissions.deny` for commits that skip signing or hooks and force pushes; `worktree.baseRef: head`.
- `scripts/claude_hooks.py` (PreToolUse, PostToolUse, SessionStart): asks before pushes the text rules cannot see (`git -C`, `bash -c`), denies signing bypasses, hand edits of plugin versions and generated README blocks, and reads or searches that reach a forbidden source listed in the untracked CLAUDE.local.md; runs prettier on edited Markdown, JSON and YAML; prints the repository state and a Claude Code version notice at session start. Python formatting is left to the maintainer's LSP plugin.
- The `docs` gate fails on drift between code and docs: pinned versions, the gate list, script and check.py target names, rule `paths`, links and `docs/*.md` references.
- Project skills: `new-plugin`, `add-component`, `release-plugin` (see [ADR release-orchestration](ADR_2026-10-04_release-orchestration.md)), `review-pr` with the `plugin-reviewer` agent, `run-marketplace`, `sync-docs`, `cc-currency`, alongside `verify` and `plugin-versioning`.
- Saved workflows `review-pr-deep`, `drift-audit` and `rules-currency` for fan-out work, each under ten agents.
- Branch convention: short-lived `<plugin>/<topic>` branches, deleted on merge (replaced by ADR branch-naming).

### Consequences

- Good, because publication, signing and the clean room no longer depend on the model remembering a rule.
- Good, because drift between pins, gates, scripts and docs fails `python3 scripts/check.py` locally and in CI.
- Good, because the hooks are unit-tested decisions; the guards were also demonstrated live in a session.
- Bad, because hooks run `python3` on every tool call for anyone who opens the repository in Claude Code; CONTRIBUTING.md says so.
- Bad, because shell parsing is best effort: a push hidden behind a variable or a relative `cd` can still reach the permission prompt only through the text rules.
- Bad, because skills and workflows are prompts: they guide Claude, and the gates and permission prompts remain the enforcement.

### Confirmation

`python3 scripts/check.py` runs the `docs` gate, `claude plugin validate .claude --strict` and the hook, docs and driver tests. `/review-pr` is run on every plugin pull request. Revisit when a collaborator joins (required reviews and status checks), when Claude Code changes hook or permission semantics (`cc-currency`), or when mods stabilize.

## Pros and cons of the options

### Prose only

- Good, because nothing runs on tool calls.
- Bad, because an auto-mode session may push or skip a rule when the instruction is compacted away.

### A plugin installed in the maintainer's configuration

- Good, because it would work in every repository.
- Bad, because the non-negotiable rules forbid installing this repository's plugins in the maintainer's real configuration, and the tooling is specific to this repository.

### Mods

- Good, because they can draw a live status pane and gate tool calls in process.
- Bad, because they are unsandboxed, their API changes between releases, an installed mod can approve a call a PreToolUse hook denied, and they need TypeScript tooling the maintainer has not agreed to.

## More information

Research: the official docs and changelog for Claude Code 2.1.285 to 2.1.289, read on 2026-10-04 (skills, sub-agents, hooks, permissions, settings, workflows, plugin CLI, plugin evals, code review, scheduled tasks, routines). The Claude Code version watcher stays a SessionStart notice plus `/cc-currency`; scheduled routines were not adopted because they run without permission prompts and can push `claude/` branches.

The branch convention bullet is replaced by [ADR branch-naming](ADR_2026-10-04_branch-naming.md) (2026-10-04): the approval recorded here had no traceable source, and the convention now covers non-plugin branches too.
