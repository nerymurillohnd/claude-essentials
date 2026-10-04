---
name: review-pr
description: Reviews a claude-essentials pull request or branch with the plugin-reviewer agent - gates on a temporary checkout, quality bar, security review, portability and release discipline - and returns evidence-backed findings. Use when asked to review a pull request, a plugin change or a release branch in this marketplace.
argument-hint: "[pull request number | branch]"
context: fork
agent: plugin-reviewer
---

Review this target in the claude-essentials repository: $ARGUMENTS

If the target is empty, review the current branch against `main`.

Follow your procedure exactly: temporary worktree, gates, the rules for every changed path, verified findings with `file:line` evidence, cleanup confirmed, and the report table. Do not edit, commit, push, comment on GitHub or approve.
