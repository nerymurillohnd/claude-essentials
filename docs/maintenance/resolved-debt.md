# Resolved Debt

## Purpose

An auditable history of maintenance/technical debt that's been corrected and
verified — what was wrong, what changed, and the evidence supporting closure.
Doesn't replace `pending-debt.md`; entries move here from there.

Preserve resolved entries as dated historical records. If a later change
invalidates a resolution, keep the original entry and open a new pending item
that links back to it — don't rewrite history.

## Resolved Items

### DEBT-001 — 2026-10-06 — CLAUDE.md "Current state" matches the repository

- **Original pending record:** DEBT-001 in `pending-debt.md` (recorded 2026-10-06), "CLAUDE.md "Current state" is stale".
- **Resolved debt:** "Current state" called merged work unpushed, listed PR #17 as open, and omitted the 0.1.0 release and the PR #15 revert.
- **Resolution:** "Current state" now holds only live facts: the ledger pointer, the catalog version and its missing tag, the plugin's scope and deferred features, and the decisions awaiting the maintainer. History moved out: it is in `git log`, the ADRs, the rules and this ledger. Its pending items were checked against `pending-debt.md`, and the three missing ones were added as DEBT-016 to DEBT-018 (`b36db96`).
- **Positive verification:** Every fact in the section was checked on 2026-10-06: `plugin.json` version 0.2.0 and PR #17 merged as `dd7227d`; `git tag -l` and `gh release list` show `svelte-development--v0.1.0` as the latest release and no 0.2.0 tag; the remote MCP decision is in `docs/sourcing-log.md`. `scripts/check.py` passed all 10 gates.
- **Negative verification:** The section no longer says any merged work is unpushed or any merged pull request is open; it states no commit or pull request state except PR #17, which `gh pr list` shows as merged.
- **Owner or responsible area:** repository maintainer and Claude (`CLAUDE.md`).
- **Residual risk / follow-up:** The section can drift again; it now points new debt to this ledger instead of accumulating history.
- **Related records:** handoff `2026-10-06-0100`; DEBT-016, DEBT-017, DEBT-018.
- **Superseded by:** none.

### DEBT-008 — 2026-10-06 — Claude review posts after the `--setting-sources user` change

- **Original pending record:** DEBT-008 in `pending-debt.md` (recorded 2026-10-06), "Claude review posting after the `--setting-sources user` change is unverified".
- **Resolved debt:** PR #6's review posted nothing because a project `permissions.ask` rule denied `gh pr comment`; whether PR #7's fix let the review post was unverified.
- **Resolution:** PR #7 (`f5884f8`) passes `--setting-sources user` to `claude-code-action`; no further change was needed.
- **Positive verification:** The `claude` app commented on both pull requests opened after PR #7: 6 comments on PR #14 (first: <https://github.com/nerymurillohnd/claude-essentials/pull/14#issuecomment-6004314917>) and 9 on PR #17 (first: <https://github.com/nerymurillohnd/claude-essentials/pull/17#issuecomment-6008531297>), counted with `gh pr view <n> --json comments` on 2026-10-06.
- **Negative verification:** The original failure, a review run that posts nothing, did not recur on either pull request.
- **Owner or responsible area:** `.github/workflows/claude-code-review.yml`.
- **Residual risk / follow-up:** The review job's unexplained permission denial and the token's exposure stay open in DEBT-007.
- **Related records:** PR #7; `.claude/rules/ci-github.md`; DEBT-007.
- **Superseded by:** none.
