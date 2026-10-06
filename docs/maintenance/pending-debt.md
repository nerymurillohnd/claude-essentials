# Pending Debt

## Purpose

A living record of unresolved technical or maintenance conditions that need
follow-up, reassessment, or verified remediation.

## Entry criteria

Add an item only when **all** of these hold:

- A specific unresolved condition is observable or supported by traceable evidence — not speculation.
- It has a meaningful operational, security, reliability, compatibility, or maintainability impact.
- There's a concrete next action, or a concrete condition that would trigger reassessment.
- It isn't already tracked by another active record (an open issue, another ADR's follow-up, etc.) unless this ledger is the designated place for it.

Don't add general improvement ideas, unverified speculation, or a copy of every backlog task.

## Record maintenance

- **Append:** check for an existing entry on the same condition first.
- **Update:** revise the entry in place when evidence, impact, ownership, or next action changes. Keep confirmed facts distinct from inference.
- **Resolve:** move the entry to `resolved-debt.md` with its ID only after the fix is verified — both that it works and that the original failure no longer reproduces. Don't just delete it.

## Open Items

Recorded 2026-10-06 from the session handoff `2026-10-06-0100` (sha `84dee5`), the repository state at `dd7227d`, and the eval and CI records cited below.

### DEBT-001 — CLAUDE.md "Current state" is stale

- **Status:** Pending
- **Category:** quality (documentation)
- **Evidence:**
  - **Confirmed facts:** `CLAUDE.md` "Current state" says `svelte-development` and the unpinned tooling are "not yet committed or pushed"; both are merged (`0ce9ebb`, `02ab6d9`). It says PR #17 is open; it merged as `dd7227d`. It does not record the `svelte-development--v0.1.0` release, the eval results, or the PR #15 revert (`7957a64`).
  - **Inferences:** none.
  - **Open questions:** none.
- **Impact / risk:** A new session reads a false picture of the repository and may act on it.
- **Owner or responsible area:** repository maintainer and Claude (`CLAUDE.md`).
- **Next action:** Update "Current state" in a docs-only commit.
- **Review condition:** Closes when "Current state" matches `git log` and the GitHub releases.
- **Related records:** handoff `2026-10-06-0100`.

### DEBT-002 — Minimum-version pin is documented as enforced but nothing enforces it

- **Status:** Pending
- **Category:** compatibility
- **Evidence:**
  - **Confirmed facts:** The official plugin reference says `metadata` is a "free-form object for your own data. Claude Code doesn't read it" (checked 2026-10-06). `minimumVersion` only limits auto-updates; `requiredMinimumVersion` is a managed setting (checked 2026-10-06). The repo writes `metadata.minClaudeCodeVersion` in `scripts/new_plugin.py:171` and shows the badge `Claude Code: ≥ 2.1.289` in `README.md:3`. ADR `ADR_2026-10-03_minimum-claude-code-version` still says CI installs exactly the pin; a 2026-10-05 note supersedes that, but the ADR is not marked superseded.
  - **Inferences:** A plugin cannot block an older Claude Code. The pin informs readers only.
  - **Open questions:** Whether `claude plugin validate --strict` reads `metadata.minClaudeCodeVersion` (not checked).
- **Impact / risk:** Users read a requirement that nothing enforces. A mod declared at 2.1.287 can run on an older Claude Code with no warning.
- **Owner or responsible area:** repository maintainer (decision); `scripts/repo.py`, `scripts/check_docs.py`, ADRs.
- **Next action:** Maintainer chooses between relabelling the pin as "tested version" and adding a plugin-side `SessionStart` check for mods. Record the choice in a new ADR that supersedes the 2026-10-03 one.
- **Review condition:** Closes when the ADR is accepted and the badge, README, and gate wording match the decision.
- **Related records:** `ADR_2026-10-03_minimum-claude-code-version`, `ADR_2026-10-05_unpinned-tooling-and-shebang-interpreters`, `.claude/rules/claude-code-version.md`.

### DEBT-003 — Session-start notice flags versions that were already reviewed

- **Status:** Pending
- **Category:** quality (noise)
- **Evidence:**
  - **Confirmed facts:** `scripts/claude_hooks.py:410-413` compares the installed version with `repo.MIN_CLAUDE_CODE` and prints a note. The note appeared for 2.1.290 and 2.1.291; both were reviewed and changed no rule (`.claude/rules/claude-code-version.md`).
  - **Inferences:** The notice fires on every session until the pin moves, so it cannot tell a real change from a reviewed one.
  - **Open questions:** Whether the maintainer wants the notice at all (see DEBT-002).
- **Impact / risk:** Alert fatigue; a real change that needs review may be ignored.
- **Owner or responsible area:** repository maintainer; `scripts/claude_hooks.py`.
- **Next action:** Decide with DEBT-002. Either remove the notice, or compare against the last reviewed version recorded in the rule file.
- **Review condition:** Closes when the notice matches the decision, with a test in `tests/`.
- **Related records:** DEBT-002.

### DEBT-004 — `svelte-development` skills do not trigger on their own

- **Status:** Pending
- **Category:** quality (plugin behavior)
- **Evidence:**
  - **Confirmed facts:** In eval run `37395261454` the three trigger cases (`trigger-best-practices`, `trigger-docs-autofixer`, `trigger-lsp`) scored 0 in both arms, so the skills never triggered without an explicit request.
  - **Inferences:** The `description` and `when_to_use` fields do not match the phrasing users use.
  - **Open questions:** Whether the fix belongs in the descriptions or in the hooks.
- **Impact / risk:** The plugin's main value depends on the user naming the skill.
- **Owner or responsible area:** `plugins/svelte-development/skills/*/SKILL.md`.
- **Next action:** Revise the descriptions, release a patch, and re-measure with the `run-evals` label on the PR.
- **Review condition:** Closes when a CI eval run shows the trigger cases above 0 in the treatment arm.
- **Related records:** run `37395261454` (closed draft PR #16); handoff open items.

### DEBT-005 — LSP and tool-choice eval cases show a delta of 0; cause unknown

- **Status:** Pending
- **Category:** quality (measurement)
- **Evidence:**
  - **Confirmed facts:** Run `37395261454`: `lsp-priority` 0, `lsp-dynamic-code` 0.25, and the tool-choice cases (docs, project-check, references) delta 0. The LSP cases ran on a fixture whose `src/lib` was never committed (`.gitignore` hid it until 2026-10-06), so their zeros are not evidence about the plugin.
  - **Inferences:** The zeros may come from the fixture, the isolated `PATH` on CI, or ToolSearch not loading the LSP tool.
  - **Open questions:** Whether `svelteserver` reaches the eval's isolated `PATH` on CI; whether the model loads the LSP tool through ToolSearch.
- **Impact / risk:** The plugin's LSP and tool-choice value is unmeasured.
- **Owner or responsible area:** `plugins/svelte-development/evals/`, `.github/workflows/plugin-evals.yml`.
- **Next action:** Commit the fixture's `src/lib`, then inspect transcripts from a fresh CI run.
- **Review condition:** Closes when a rerun shows LSP and tool-choice cases with transcripts that prove the tool was called, or when the cases are removed with a recorded reason.
- **Related records:** DEBT-004, the open items in handoff `2026-10-06-0100`.

### DEBT-006 — `CLAUDE_CODE_OAUTH_TOKEN` disappeared without a known cause

- **Status:** Pending
- **Category:** security
- **Evidence:**
  - **Confirmed facts:** The repository secret was gone between 22:46 and 22:52 UTC on 2026-10-05 (API total_count 0), which caused eval run `37385153881` to fail with `auth_failed`. The maintainer restored it with `/install-github-app` at 22:59 UTC.
  - **Inferences:** none.
  - **Open questions:** Who or what deleted it; the account security log was not checked.
- **Impact / risk:** Evals and the review job fail silently when the secret is missing, and it may recur.
- **Owner or responsible area:** repository maintainer (GitHub account and secrets).
- **Next action:** Check the account security log for the 22:46–22:52 UTC window.
- **Review condition:** Closes with a recorded cause, or when the secret has held for 30 days with no unexplained change.
- **Related records:** DEBT-007 (same secret).

### DEBT-007 — Review job: one permission denial not investigated; token exposure not researched

- **Status:** Pending
- **Category:** security
- **Evidence:**
  - **Confirmed facts:** The last run of `claude-code-review` reported one permission denial. The `CLAUDE_CODE_OAUTH_TOKEN` secret is also used by `plugin-evals.yml`.
  - **Inferences:** A review job that can read the token can expose it if it runs untrusted code.
  - **Open questions:** What the denied call was; whether the action or the project's `Read(...)` deny rules protect the token on the runner.
- **Impact / risk:** A secret reachable from an agent run; an unexplained denial may hide a misconfigured permission.
- **Owner or responsible area:** `.github/workflows/claude-code-review.yml`, `.claude/settings.json`.
- **Next action:** Read the denial details from the last run's log. Research the token's location on the runner against the action's documentation. Do not test with the real token.
- **Review condition:** Closes when the denial is explained and the token's exposure is documented with a verified mitigation.
- **Related records:** DEBT-006; `.claude/rules/ci-github.md`.

### DEBT-008 — Claude review posting after the `--setting-sources user` change is unverified

- **Status:** Pending
- **Category:** quality (CI)
- **Evidence:**
  - **Confirmed facts:** PR #6's review posted nothing because a project `permissions.ask` rule denied `gh pr comment`. PR #7 (`f5884f8`) added `--setting-sources user` so the review can post.
  - **Inferences:** The fix is probably correct.
  - **Open questions:** Whether the review posts on the next pull request; `.claude/rules/ci-github.md` says that pull request shows it.
- **Impact / risk:** The review may stay silent without any failure.
- **Owner or responsible area:** `.github/workflows/claude-code-review.yml`.
- **Next action:** Check the review's output on the next pull request that changes plugins or workflows.
- **Review condition:** Closes when a review comment is posted and linked in the record.
- **Related records:** `.claude/rules/ci-github.md`; PR #7.

### DEBT-009 — `test-install` session scenario has no unit test

- **Status:** Pending
- **Category:** quality (test coverage)
- **Evidence:**
  - **Confirmed facts:** The handoff open items record that the session scenario of `scripts/test_install.py` has no unit test.
  - **Inferences:** A regression in that scenario would reach CI without a targeted failure.
  - **Open questions:** Whether the scenario is covered end-to-end by `scripts/check.py test-install`.
- **Impact / risk:** Silent regressions in the isolated session install.
- **Owner or responsible area:** `scripts/test_install.py`, `tests/`.
- **Next action:** Add a unit test for the session scenario, or record why end-to-end coverage is enough.
- **Review condition:** Closes when the test exists and runs in the gates, or when the decision not to add it is recorded.
- **Related records:** `.claude/rules/testing/isolated-install.md`.

### DEBT-010 — Commit scopes are not a closed list

- **Status:** Pending
- **Category:** quality (conventions)
- **Evidence:**
  - **Confirmed facts:** `scripts/check_commit_msg.py` accepts any kebab-case scope. The branch-naming ADR (`ADR_2026-10-04_branch-naming`) reserves `marketplace`, `scripts`, `ci` and `docs`.
  - **Inferences:** A typo in a scope passes the gate.
  - **Open questions:** Whether the maintainer wants a closed list.
- **Impact / risk:** Inconsistent history that is hard to filter.
- **Owner or responsible area:** `scripts/check_commit_msg.py`.
- **Next action:** Maintainer decides; if closed, change the checker and add a test.
- **Review condition:** Closes on the decision and the matching change.
- **Related records:** `ADR_2026-10-04_branch-naming`.

### DEBT-011 — `assert_*` helper naming is unconfirmed

- **Status:** Pending
- **Category:** quality (conventions)
- **Evidence:**
  - **Confirmed facts:** `tests/test_integrity.py` on `main` uses the `assert_*` naming, which has not been confirmed by the maintainer.
  - **Inferences:** none.
  - **Open questions:** Whether the convention is accepted.
- **Impact / risk:** Low; a naming rule may be reversed later at a cost.
- **Owner or responsible area:** repository maintainer; `tests/test_integrity.py`, `.claude/rules/testing/gates.md`.
- **Next action:** Maintainer confirms or rejects; if rejected, change the test and the rule file together.
- **Review condition:** Closes on the decision.
- **Related records:** `.claude/rules/testing/gates.md`.

### DEBT-012 — Issue chooser lists "Report a security vulnerability" twice

- **Status:** Pending
- **Category:** quality (issue intake)
- **Evidence:**
  - **Confirmed facts:** The `/issues/new/choose` screenshot (2026-10-06) shows two entries titled "Report a security vulnerability": one with a shield icon, and one external link to `SECURITY.md`. Both lead to private reporting.
  - **Inferences:** The shield entry is GitHub's built-in private reporting; the external link comes from `.github/ISSUE_TEMPLATE/config.yml`.
  - **Open questions:** Whether `config.yml` declares the link the built-in entry already shows.
- **Impact / risk:** Confusing intake; no security impact, since both routes are private.
- **Owner or responsible area:** `.github/ISSUE_TEMPLATE/config.yml`.
- **Next action:** Read `config.yml`; remove the duplicate contact link if the built-in entry covers it.
- **Review condition:** Closes when the chooser shows one security entry.
- **Related records:** `SECURITY.md`.

### DEBT-013 — Open question on eval trace graders and subagent tool calls

- **Status:** Pending
- **Category:** quality (measurement)
- **Evidence:**
  - **Confirmed facts:** `.claude/rules/testing/plugin-evals.md` lists this as open.
  - **Inferences:** none.
  - **Open questions:** Whether trace graders see tool calls made inside a subagent.
- **Impact / risk:** Trace-based scores for the auditor and editor agents may be wrong.
- **Owner or responsible area:** `.claude/rules/testing/plugin-evals.md`.
- **Next action:** Settle from the `editor-follows-skill` and `auditor-read-only` transcripts and record the answer.
- **Review condition:** Closes when the rule file records the answer.
- **Related records:** DEBT-005.

### DEBT-014 — Plugin evals ran on any labeled pull request

- **Status:** Pending (fix on branch `ci/evals-only-for-plugins`, not merged)
- **Category:** cost
- **Evidence:**
  - **Confirmed facts:** `.github/workflows/plugin-evals.yml` ran its eval job for any pull request labelled `run-evals`, including pull requests that change no plugin. Inside the loop, plugins without changes make no model call, but the job still started a runner and installed Claude Code.
  - **Inferences:** The branch's change adds a `changes` job so the eval job skips when no plugin file changed.
  - **Open questions:** none.
- **Impact / risk:** Avoidable CI minutes on every labelled pull request; model cost only when a plugin changes.
- **Owner or responsible area:** `.github/workflows/plugin-evals.yml`.
- **Next action:** Review and merge the branch after the maintainer approves. Verify with one pull request that changes no plugin (the eval job must show as skipped) and one that does.
- **Review condition:** Closes when the change is merged and both pull requests behave as described.
- **Related records:** `ADR_2026-10-05_plugin-evals-in-ci`, `ADR_2026-10-06_inherited-eval-models-and-full-results`.

### DEBT-015 — Required reviews and status checks off on `main`

- **Status:** Pending (decision recorded; revisit on a trigger)
- **Category:** security
- **Evidence:**
  - **Confirmed facts:** `.claude/rules/ci-github.md` records that required reviews and status checks are off, because the maintainer is the only collaborator.
  - **Inferences:** A second collaborator would be able to push without review.
  - **Open questions:** none.
- **Impact / risk:** Low today; rises as soon as a second collaborator has write access.
- **Owner or responsible area:** repository maintainer; repository rulesets.
- **Next action:** None until a second collaborator exists. Then enable required reviews before granting access.
- **Review condition:** A second collaborator is added to the repository.
- **Related records:** `.claude/rules/ci-github.md`.
