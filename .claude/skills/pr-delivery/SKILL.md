---
name: pr-delivery
description: Delivers a change in the claude-essentials repository from an open branch to a verified finish (PR merged, CI and the Tag plugin versions workflow green on main, every plugin version tagged on origin, the feature branch deleted locally and remotely, main synced, and a clean tree), with a checklist a Stop hook enforces so the work can't be reported as done early. Use it whenever a change here is about to be pushed, turned into a PR, merged, or "shipped", and whenever the user asks to merge, clean up, sync main, finish, or close out a change, even if they only say "mergea y limpia" or "déjalo todo listo".
argument-hint: "[branch]"
arguments: branch
hooks:
  Stop:
    - hooks:
        - type: command
          command: '"${CLAUDE_PROJECT_DIR}/.claude/hooks/checklist-gate.sh"'
          timeout: 300
---

# PR delivery

A change here is done when the remote and local repositories prove it, not when
a PR has been opened or a merge button pressed. This skill holds the finish line
the rules in `.claude/rules/plugin-delivery.md` describe, and a Stop hook keeps
the turn open until it is reached.

## Start

Branch: `$branch`, or the current branch if that is empty. It must be the
feature branch, not `main`. Start the checklist from the repository root before
pushing anything:

```bash
.claude/hooks/lib/checklist.sh start .claude/skills/pr-delivery/checklist.json "<branch>" "${CLAUDE_SESSION_ID}"
```

If another checklist is still in progress (for example a `plugin-release-review`),
`start` refuses. Finish that one first. Mark each item as it is reached, with the
evidence that proves it:

```bash
.claude/hooks/lib/checklist.sh check <item-id> "<evidence>"
```

While items are open, the Stop hook will not let the turn end. Once all are
marked, it re-runs the verify commands (remote tags, branch gone, main synced,
clean tree plus `npm run validate`) with `$CHECKLIST_SUBJECT` set to the branch,
and reopens any that fail.

## Flow

1. **Before the PR.** For changes under `plugins/`, run `/plugin-release-review
   <id>` to completion on the final head. When the skill description, evals, or
   scripts changed, re-measure the README numbers (eval table, test counts,
   timings) in this branch. Run `npm run check` and `npm run check:versions`.
2. **PR.** Only a change that bumps a plugin version needs one; anything else
   is pushed straight to `main`, where `guard-push.sh` runs the checks first.
   Push the branch and open the PR with the repository template and
   labels from `.github/labels.json`. Use the GitHub MCP server for PR reads,
   checks, labels, and the merge when it is connected; use `gh` only for what it
   lacks (Actions runs and logs, ref deletion).
3. **Checks.** Fix real failures on the branch and push again. Every push changes
   the head SHA, so re-read the PR before trusting any earlier observation.
4. **Merge.** Merge only with the user's explicit approval for this PR and head
   SHA, using the method the repository enforces. Confirm GitHub reports it as
   merged.
5. **After merge.** Wait for CI and `Tag plugin versions` on the merge commit. If
   the tag push fails with `fatal error in commit_refs`, dispatch a fresh run
   (`gh workflow run tag-versions.yml --ref main`) instead of re-running. Never
   create the tag by hand.
6. **Clean up.** Delete the remote branch if GitHub didn't, switch to `main`,
   `git pull --ff-only`, `git fetch --prune`, and delete the local branch. Never
   push to the merged branch again. The `guard-push.sh` hook denies
   it, and follow-up work starts on a new branch from `main`.

When a step needs a decision only the user can make (approving the merge,
dropping a change), mark the item `checklist.sh needs-user <item-id>
"<question>"` and ask. Use `checklist.sh abort "<their words>"` only when the
user explicitly stops the delivery.

## Report

Close with the PR URL, the merged SHA, the workflow runs and their conclusions,
the tags on origin, and the final `git status -sb`. Report only what the
checklist verified.
