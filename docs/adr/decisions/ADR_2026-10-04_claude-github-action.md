---
status: accepted
date: 2026-10-04
decision-makers:
  - "Nery Samuel Murillo (maintainer)"
---

# Claude Code GitHub Action for pull request reviews and @claude requests

## Purpose

Decide whether the repository runs Claude Code on GitHub, and under which limits, after the maintainer installed the Claude GitHub App and its workflows with `/install-github-app`.

## Scope

`.github/workflows/claude-code-review.yml`, `.github/workflows/claude.yml`, the `CLAUDE_CODE_OAUTH_TOKEN` repository secret, the Claude GitHub App installation and the repository's allowed-actions list. Local review (`/code-review`, `/review-pr`) is unchanged.

## Context and problem statement

[ADR claude-code-automation](ADR_2026-10-04_claude-code-automation.md) kept reviews local. The maintainer then installed the Claude GitHub App, which opened pull request #3 with the two generic workflows Claude Code generates. They failed this repository's checks: unpinned actions, credentials persisted by checkout, non-conventional commit messages, and an action outside the allowed-actions list. Should the repository adopt them, and how?

## Decision drivers

- Every action pinned by SHA, `permissions: {}` at workflow level, `persist-credentials: false` (the repository's workflow conventions and zizmor).
- Third parties may open issues but not pull requests (`pull_request_creation_policy: collaborators_only`); nothing they write may make Claude act.
- Reviews on GitHub must add something the local reviews do not.

## Considered options

- Adopt both workflows, hardened
- Adopt only the review workflow
- Close pull request #3 and keep reviews local

## Decision outcome

Chosen option: **adopt both workflows, hardened**, because the review workflow catches bugs on every pull request even when the local review was skipped, and the `@claude` workflow lets the maintainer hand a third party's issue to Claude from GitHub, while the action's own checks keep third parties from triggering it.

- `claude-code-review.yml` reviews every push with a repository-specific prompt instead of the generated workflow's `code-review` plugin, which skips a pull request that already has a Claude comment: the maintainer requires every update to be reviewed again. Each run re-checks earlier findings, reviews correctness and this repository's rules, posts inline comments and one summary.
- `claude.yml` answers `@claude` in issues, pull requests and reviews. The action rejects any triggering user without write access to the repository and any bot (official Claude Code GitHub Actions docs, "Who can trigger runs").
- Both pin `anthropics/claude-code-action` to the commit of v1.0.241 (which ships Claude Code 2.1.289) and checkout v7.0.1 by SHA, set `permissions: {}`, `persist-credentials: false` and job timeouts, and authenticate with the `CLAUDE_CODE_OAUTH_TOKEN` secret.
- `anthropics/claude-code-action@*` is added to the repository's allowed actions, and so is the action it runs internally that GitHub does not own, `oven-sh/setup-bun`, pinned to the SHA the action uses.

### Consequences

- Good, because every pull request gets an automatic bug review, and issues can be delegated to Claude with one comment.
- Bad, because each run uses the maintainer's Claude subscription.
- Bad, because the Claude GitHub App holds broad permissions GitHub does not let an installer narrow, and a run the maintainer triggers with `@claude` can push `claude/` branches with the app's token without a local approval prompt; triggering it is the approval.
- Bad, because the allowed-actions list applies to actions nested inside other actions: updating `claude-code-action` means checking its internal `uses:` again and updating the `oven-sh/setup-bun` entry.

### Confirmation

zizmor, actionlint and the GitHub workflow schema check both files in `python3 scripts/check.py`. Revisit when a collaborator joins, when the action's major version changes, or if a review run posts noise the maintainer does not want.

## More information

Pull request #3 is closed in favour of the pull request that adds these hardened files.

- 2026-10-05: [ADR remove-claude-mention-workflow](ADR_2026-10-05_remove-claude-mention-workflow.md) removes `claude.yml`; the review workflow part of this record still applies.
