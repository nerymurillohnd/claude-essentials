# Resolved Debt

## Purpose

An auditable history of maintenance/technical debt that's been corrected and
verified — what was wrong, what changed, and the evidence supporting closure.
Doesn't replace `pending-debt.md`; entries move here from there.

Preserve resolved entries as dated historical records. If a later change
invalidates a resolution, keep the original entry and open a new pending item
that links back to it — don't rewrite history.

## Resolved Items

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
