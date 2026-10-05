---
status: accepted
date: 2026-10-05
decision-makers:
  - "Nery Samuel Murillo (maintainer)"
---

# Remove the @claude workflow

## Purpose

Stop running Claude Code on GitHub in response to `@claude` mentions, and keep only the automatic pull request review.

## Scope

`.github/workflows/claude.yml` and the rules and docs that describe it. `.github/workflows/claude-code-review.yml`, the `CLAUDE_CODE_OAUTH_TOKEN` secret and the Claude GitHub App installation are unchanged.

## Context and problem statement

[ADR claude-github-action](ADR_2026-10-04_claude-github-action.md) adopted two workflows: the pull request review and `claude.yml`, which answers `@claude` in issues, pull requests and reviews. A run triggered with `@claude` can push `claude/` branches with the app's token without a local approval prompt, which sits outside this repository's rule that no push happens without the maintainer's explicit approval of that exact action. Whether those pushes were allowed, and whether `claude.yml` hits the same `permissions.ask` denial the review job had, were still open. Reinstalling the app on 2026-10-05 also opened pull request #13 with the generic workflows, which the repository's SHA-pinning policy rejected. Should the repository keep `claude.yml`?

## Decision drivers

- No push, branch or publication without the maintainer's explicit approval for that exact action.
- Claude works on this repository locally, where signing, hooks, gates and permission prompts apply.
- Fewer workflows holding the Claude token means less to audit.

## Considered options

- Remove `claude.yml`
- Keep `claude.yml` and settle its push and permission questions

## Decision outcome

Chosen option: **remove `claude.yml`**, because the maintainer decided on 2026-10-05 to drop the `@claude` workflow, and local sessions already cover every task it offered under the repository's approval rules.

### Consequences

- Good, because no workflow can push a branch to this repository without a local approval.
- Good, because the open questions about `@claude` pushes and its `permissions.ask` behavior no longer apply.
- Bad, because a third party's issue can no longer be handed to Claude with one comment on GitHub; it is handled in a local session.

### Confirmation

`.github/workflows/claude.yml` is absent, and the rules and docs list only `claude-code-review` as a Claude workflow. Revisit if the maintainer wants Claude to act from GitHub again.

## More information

Replaces the `claude.yml` part of [ADR claude-github-action](ADR_2026-10-04_claude-github-action.md), which stays accepted for the review workflow. Decided by the maintainer in a Claude Code session on 2026-10-05.
