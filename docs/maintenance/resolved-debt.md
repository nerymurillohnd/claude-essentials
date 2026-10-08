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

### DEBT-013 — 2026-10-08 — Eval trace graders see a subagent's tool calls

- **Original pending record:** DEBT-013 in `pending-debt.md` (recorded 2026-10-06), "Open question on eval trace graders and subagent tool calls".
- **Resolved debt:** Nobody knew whether trace and `tool_used` graders count tool calls made inside a subagent.
- **Resolution:** The trace of a run holds the subagent's messages, each with `parent_tool_use_id` (the `Agent` call) and `agent_id` set. `.claude/rules/testing/plugin-evals.md` records it under Evidence.
- **Positive verification:** Local pilot of 2026-10-08 (`--keep-temp`), case `10-editor-delegation`, treatment arm: after the `Agent` call to `svelte-development:svelte-component-editor`, 13 tool calls (Read, Bash, ToolSearch, `get-documentation`, Write, `svelte-autofixer`) carry `parent_tool_use_id` and `agent_id` `ac13328bc543c4915` in `out/trace.jsonl`.
- **Negative verification:** The main thread's own calls in the same trace carry neither field, so the two can be told apart.
- **Owner or responsible area:** `.claude/rules/testing/plugin-evals.md`.
- **Residual risk / follow-up:** Observed on Claude Code 2.1.294 with a background subagent; re-check if the trace format changes.
- **Related records:** DEBT-005.
- **Superseded by:** none.

### DEBT-005 — 2026-10-08 — The LSP eval cases measure the plugin

- **Original pending record:** DEBT-005 in `pending-debt.md` (recorded 2026-10-06), "LSP and tool-choice eval cases show a delta of 0; cause unknown".
- **Resolved debt:** The LSP and tool-choice cases scored a delta of 0, and nobody knew whether the language server reached the eval runs.
- **Resolution:** The suite was rebuilt (`2a73a9c`): the tool-choice cases became graders inside task cases, and the LSP cases run on the committed fixture. The CI run proves the language server answers in a run.
- **Positive verification:** CI run `37749514321` (PR #19, 2026-10-08, Claude Code 2.1.294, three runs per arm): case `08-lsp-where-used` called the LSP tool in 3 of 3 treatment runs and in none of the baseline runs, delta +0.38; case `09-rename-proven-by-check` passed `lsp-used` in the treatment arm.
- **Negative verification:** The baseline arm failed `lsp-used` and `lsp-before-text-search` in 3 of 3 runs, so the graders still tell the arms apart.
- **Owner or responsible area:** `plugins/svelte-development/evals/`.
- **Residual risk / follow-up:** Locally, on machines whose global binaries are symlinks, the skill's Bash probe still fails (DEBT-019).
- **Related records:** DEBT-004, DEBT-013, DEBT-019.
- **Superseded by:** none.

### DEBT-004 — 2026-10-08 — `svelte-development` skills load and route the work

- **Original pending record:** DEBT-004 in `pending-debt.md` (recorded 2026-10-06), "`svelte-development` skills do not trigger on their own".
- **Resolved debt:** Skills did not load for tasks that do not name Svelte (a SvelteKit 2 route rule, a prop rename), audits were not delegated to the auditor, and the autofixer was called without `desired_svelte_version` or on part of a review.
- **Resolution:** 0.5.0 removes the `paths` that limited activation, adds a `SessionStart` note in Svelte projects and a hint before Svelte writes, makes routing to the agents ground rule 0, and requires the Svelte version and full coverage for the autofixer.
- **Positive verification:** CI eval run `37802833418` (PR #20, 2026-10-08, Claude Code 2.1.294, agent `claude-sonnet-5-5`, judge `claude-opus-5-5`, three runs per arm, $8.41): 11/11 cases, every one of the 33 treatment runs scored 1.00, mean delta +0.233 against +0.175 for 0.4.0 (run `37749514321`). `skill-fired` 3/3 in every case that has it, including 05 (was 1/3) and 09 (was 0/3); `proposes-migration` 3/3 (was 1/3); `checked-before-and-after` 3/3 (was 0/3); `auditor-dispatched` 3/3 (was 1/3); no autofixer abort (run `37749514321` had one).
- **Negative verification:** the baseline arm still fails every plugin-specific grader (`skill-fired` absent, `auditor-dispatched` 0/3, `checked-before-and-after` 0/3), and the two negative cases (React, README) stay at 1.00 in both arms, so no skill loads where it should not.
- **Owner or responsible area:** `plugins/svelte-development/`.
- **Residual risk / follow-up:** the pre-edit hint is once per session, so a subagent's Svelte edit can use it up before the main thread edits inline; the `SessionStart` note covers the main thread.
- **Field test before the fix (2026-10-08, 0.4.0 in a real Astro 7 + Svelte 5.57 project, Opus 5.5):** a read-only architecture audit of the product purchase island loaded `svelte-lsp-navigation` and `svelte-docs-and-autofixer` unprompted, made six successful LSP calls, ran the project's own check and proposed no SvelteKit API, but did the audit inline instead of delegating to `svelte-code-auditor`, and ran the autofixer on 2 of the 11 components it reviewed. The follow-up fix (a history-state bug the audit reproduced) was delegated to `svelte-component-editor`, written test-first, autofixed on the whole file, and the `Stop` hook ran `svelte-check` once after the edits and passed silently (fingerprint `checked-*` at 04:31; hint files for docs, check and CLI at 04:14).
- **Related records:** DEBT-019, DEBT-020.
- **Superseded by:** none.

### DEBT-019 — 2026-10-08 — The language server is probed with an LSP call

- **Original pending record:** DEBT-019 in `pending-debt.md` (recorded 2026-10-08), "The language-server probe fails inside a sandboxed Bash".
- **Resolved debt:** The skill's step 0 ran `command -v svelteserver` in Bash, which a sandbox cannot answer for a symlinked global install, so Claude skipped a working server.
- **Resolution:** 0.5.0 probes with `documentSymbol` on a `.svelte` file, with a warm-up before deciding, in the skill, its references and the auditor; `command -v` stays only as advice for the user's own shell.
- **Positive verification:** CI eval run `37802833418` (PR #20, 2026-10-08, Claude Code 2.1.294, agent `claude-sonnet-5-5`, judge `claude-opus-5-5`, three runs per arm, $8.41): 11/11 cases, every one of the 33 treatment runs scored 1.00, mean delta +0.233 against +0.175 for 0.4.0 (run `37749514321`); `lsp-used` 3/3 in cases 08 and 09. A local pilot on the maintainer's macOS with nvm (the machine where the Bash probe had failed) called the LSP tool twice with the shipped `.lsp.json`.
- **Negative verification:** the baseline arm calls no LSP tool (`lsp-used` 0/3 in 08 and 09), so the graders still tell the arms apart.
- **Owner or responsible area:** `plugins/svelte-development/skills/svelte-lsp-navigation/`.
- **Residual risk / follow-up:** case 08's `lsp-before-text-search` now counts only `Grep`; the maintainer accepted that change on 2026-10-08 after its first 0.5.0 failure, since its trace showed `Glob` locating the file. Without that grader, case 08's delta is +0.222.
- **Related records:** DEBT-004, DEBT-005.
- **Superseded by:** none.

### DEBT-020 — 2026-10-08 — Review findings on the 0.4.0 skills fixed

- **Original pending record:** DEBT-020 in `pending-debt.md` (recorded 2026-10-08), "Code review findings on the `svelte-development` 0.4.0 skills".
- **Resolved debt:** `paths` narrowed activation and `src/routes/**` matched non-Svelte projects; ground rule 5 contradicted "diagnostics clean"; the docs-and-autofixer description lost the pasted-code and playground triggers.
- **Resolution:** 0.5.0 removes `paths`; ground rule 5, the best-practices procedure, the navigation checklist and the editor agent share one finishing rule (no error in the changed files, a baseline only for changes other files use, never stash or reset the user's work); the description names pasted code and the playground link.
- **Positive verification:** CI eval run `37802833418` (PR #20, 2026-10-08, Claude Code 2.1.294, agent `claude-sonnet-5-5`, judge `claude-opus-5-5`, three runs per arm, $8.41): 11/11 cases, every one of the 33 treatment runs scored 1.00, mean delta +0.233 against +0.175 for 0.4.0 (run `37749514321`); the skills docs read 2026-10-08 confirm `paths` limits activation; `scripts/check.py` passes with the three ground-rule copies identical.
- **Negative verification:** the React and README negative cases stay at 1.00 in both arms with no Svelte skill loaded.
- **Owner or responsible area:** `plugins/svelte-development/skills/`, `agents/svelte-component-editor.md`.
- **Residual risk / follow-up:** none known.
- **Related records:** DEBT-004.
- **Superseded by:** none.
