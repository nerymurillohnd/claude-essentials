---
status: accepted
date: 2026-10-03
decision-makers:
  - "Nery Samuel Murillo (maintainer)"
---

# Sourcing policy: automate and source first, hand-write last

## Purpose

Decide how every repository artifact is produced, so nothing is hand-written that a tool, official template or open standard already provides.

## Scope

Every file in the repository: community health files, CI, templates, tooling and plugin scaffolds.

## Context and problem statement

Hand-written boilerplate drifts, carries mistakes and costs review time. Copying one template verbatim imports its assumptions and license obligations.

## Decision drivers

- Prefer what stays current by itself (generators, native features) over static copies.
- Respect licenses and record attribution.
- Keep hand-written content to what is genuinely specific to this project.

## Considered options

- Ordered sourcing procedure with a sourcing log
- Write everything by hand
- Copy one complete template repository

## Decision outcome

Chosen option: **ordered sourcing procedure with a sourcing log**. For each artifact, in order:

1. A native generator or tool (`claude plugin init`, `claude plugin tag`, `claude plugin validate`, the GitHub license and gitignore APIs, issue-form labels).
2. An official template or platform documentation (GitHub docs, Claude Code docs).
3. Established open standards and widely adopted templates (Keep a Changelog, SemVer, Conventional Commits, Contributor Covenant, MADR).
4. Hand-writing, only for what is ours (quality bar, security policy, CLAUDE.md, plugin rules).

High-value artifacts are synthesized from several sources rather than copied from one. Every decision and attribution is recorded in [docs/sourcing-log.md](../../sourcing-log.md) and [THIRD_PARTY_NOTICES.md](../../../THIRD_PARTY_NOTICES.md).

### Consequences

- Good, because generated artifacts stay aligned with their sources.
- Bad, because adapting a generator's output needs post-processing code (for example, `scripts/new_plugin.py` adapts the layout `claude plugin init` writes for skills-directory plugins).

### Confirmation

The sourcing log has a row per artifact class; reviewers reject unexplained hand-written boilerplate. Re-evaluate deferred tools (git-cliff, release-please, Dependabot, link checking) when the catalog grows.

## Pros and cons of the options

### Ordered procedure

- Good, because each choice is justified and traceable.
- Bad, because it is slower than writing a file directly.

### Copy one template repository

- Good, because it is fast.
- Bad, because it imports someone else's decisions and licensing obligations wholesale.

## More information

See [ADR clean-room-policy](ADR_2026-10-03_clean-room-policy.md) for the boundary: generic engineering sources are allowed; other Claude Code plugin collections are not.
