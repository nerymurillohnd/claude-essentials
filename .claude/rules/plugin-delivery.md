# Plugin delivery

How a change goes from idea to a tagged version on `main` without the rework
loops seen while shipping `block-no-verify` 0.1.0–0.1.1 (three review rounds,
stale eval numbers, a recreated merged branch, a stuck tag). The procedure
lives in three repo skills whose checklists a Stop hook enforces; the
mechanical parts are enforced by `make check`, the version-check job, and
the hooks in `.claude/settings.json` (the push guard denies pushes to a merged
branch). This file keeps only the policy every session needs.

## The procedure is in the skills

- Design: `/plugin-design <id>` for every new plugin or major change. Its
  checklist is the definition of a finished design; build nothing before the
  maintainer approves it.
- Review: `/plugin-release-review <id>` on the first complete draft and after
  every change to runtime files, the README, or `plugin.json`.
- Delivery: `/pr-delivery [branch]` from push to finish, after `repo-auditor`
  returns `VERDICT: PASS` for the PR's head. Its checklist is the
  definition of done (merged, CI and tags green, branch deleted, `main`
  synced, clean tree).

Working knowledge for plugin files and shell scripts loads with those files
(`plugin-authoring.md`, `shell-scripts.md`).

## Always

- Use the GitHub MCP server for every GitHub read and mutation it supports
  (PRs, checks, reviews, labels, tags, merge). Use `gh` only for what it lacks:
  Actions logs, runs and reruns, ruleset and merge-method policy, and deleting
  refs.
- Everything that belongs to a change ships in its PR. If something is found
  after merge, it gets its own PR from a fresh branch off the updated `main`,
  in the same session, never a push to the merged branch.
