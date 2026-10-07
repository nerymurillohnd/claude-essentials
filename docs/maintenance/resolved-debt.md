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

### DEBT-002 — 2026-10-07 — Minimum-version pin removed instead of enforced

- **Original pending record:** DEBT-002 in `pending-debt.md` (recorded 2026-10-06), "Minimum-version pin is documented as enforced but nothing enforces it".
- **Resolved debt:** `repo.MIN_CLAUDE_CODE` (2.1.289) fed the README badges, the new-plugin default and five documented copies, but Claude Code does not read `metadata.minClaudeCodeVersion`, so the minimum never blocked an older install.
- **Resolution:** The maintainer chose to remove the pin (session of 2026-10-07). `MIN_CLAUDE_CODE`, `PIN_SITES` and the default `minClaudeCodeVersion` of new plugins are gone; a plugin declares one only when it needs a specific version, and its README then shows it. `/cc-currency` starts from the last reviewed release in `.claude/rules/claude-code-version.md`. Recorded in ADR no-pinned-claude-code-version, which supersedes ADR minimum-claude-code-version.
- **Positive verification:** `scripts/check.py` passed all 10 gates, including 159 tests with the new `MinimumVersionTest`; `scripts/validate_adrs.py` accepted 30 records; `grep -rnE "MIN_CLAUDE_CODE\b|PIN_SITES"` outside `docs/adr/decisions/` finds only `MOD_MIN_CLAUDE_CODE`, the mods floor. README generation for a plugin without a declared minimum, run in a scratch interpreter, printed no badge and the row `A current release`.
- **Negative verification:** `git diff --stat -- plugins` is empty, so `svelte-development` (which declares 2.1.289) is unchanged and needs no release.
- **Owner or responsible area:** repository maintainer; `scripts/repo.py`, `scripts/check_docs.py`, `scripts/sync_readmes.py`, ADRs.
- **Residual risk / follow-up:** The generated plugin README sentence "older than the minimum?" still reads as if a minimum existed; changing it rewrites every plugin README and needs a plugin release, so it waits for the next one.
- **Related records:** ADR no-pinned-claude-code-version; DEBT-003.
- **Superseded by:** none.

### DEBT-003 — 2026-10-07 — Session-start version notice removed

- **Original pending record:** DEBT-003 in `pending-debt.md` (recorded 2026-10-06), "Session-start notice flags versions that were already reviewed".
- **Resolved debt:** The `session-status` hook printed a note on every session while Claude Code was newer than the pin, so it could not tell a real change from a reviewed one.
- **Resolution:** The comparison and `_NEWER_NOTE` are removed from `scripts/claude_hooks.py` together with the pin; the hook prints the branch, changed files and the Read reminder. The maintainer runs `/cc-currency` before schema, component, release or distribution work (CLAUDE.md, Non-negotiable rules).
- **Positive verification:** `ClaudeHooksTest.test_session_status_names_the_project_and_the_rule_loading` asserts the status has no `/cc-currency` note; `scripts/check.py` passed all 10 gates.
- **Negative verification:** The session no longer warns when Claude Code is newer than the last review; this is accepted in the ADR.
- **Owner or responsible area:** `scripts/claude_hooks.py`, `.claude/rules/automation.md`.
- **Residual risk / follow-up:** A release that changes a rule is found only when `/cc-currency` runs.
- **Related records:** ADR no-pinned-claude-code-version; DEBT-002.
- **Superseded by:** none.
