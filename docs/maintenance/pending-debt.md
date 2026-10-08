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

### DEBT-004 — `svelte-development` skills do not trigger on their own

- **Status:** Pending
- **Category:** quality (plugin behavior)
- **Evidence:**
  - **Confirmed facts:** In eval run `37395261454` the three trigger cases (`trigger-best-practices`, `trigger-docs-autofixer`, `trigger-lsp`) scored 0 in both arms, so the skills never triggered without an explicit request.
  - **Confirmed facts (2026-10-08):** In eval run `37719700088` (0.3.0, PR #18) the treatment arm scored `trigger-best-practices` 1.0, `trigger-docs-autofixer` 0.67 and `trigger-lsp` 1.0 (deltas +0.25, +0.33, +1.0), but the `skill-fired` indicator of `trigger-docs-autofixer` stayed 0, and task cases that do not name Svelte (`version-gate-kit2`, `tool-choice-*`, `routing-lsp-first`) kept a delta of 0. The run artifact holds no traces, so whether a skill loaded is not visible.
  - **Confirmed facts (2026-10-08, local pilot of the rebuilt 11-case suite, one run per arm, Sonnet 5.5 agent, Opus 5.5 judge, $2.61):** a skill loaded in the treatment arm of cases 01, 04, 05, 07, 08 and 10, including requests with no file open (01, 07, 08). It did not load for the rename in 09 or the review in 11, and the review was done inline instead of by `svelte-code-auditor`. In 05 (SvelteKit 2 project) Claude loaded the skill, then wrote a SvelteKit 2 matcher and called the migration "out of scope" instead of proposing it first.
  - **Inferences:** The `description` and `when_to_use` fields did not match the phrasing users use; 0.4.1 rewrote the descriptions (what and when only) and removed `when_to_use`.
  - **Open questions:** Whether the fix belongs in the descriptions or in the hooks.
- **Impact / risk:** The plugin's main value depends on the user naming the skill.
- **Owner or responsible area:** `plugins/svelte-development/skills/*/SKILL.md`.
  - **Confirmed facts (2026-10-08, CI run `37749514321`, PR #19, three runs per arm, $7.75, mean delta +0.175):** case 05 proposed the SvelteKit 3 migration before writing in 1 of 3 treatment runs; case 09 ran the project check at most once instead of before and after; case 11 delegated to `svelte-code-auditor` in 1 of 3; in case 01 one treatment run called the autofixer without `desired_svelte_version` and the mock's `expect:` guard aborted it.
- **Next action:** Decide with the maintainer which skill wording to tighten for cases 01, 05, 09 and 11, release a patch, and re-run the suite.
- **Review condition:** Closes when a CI eval run shows the trigger cases above 0 in the treatment arm.
- **Related records:** run `37395261454` (closed draft PR #16); handoff open items.

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

### DEBT-014 — Plugin evals ran on any labeled pull request

- **Status:** Pending (fix merged on `main` as `07dfa66`; behavior on a pull request unverified)
- **Category:** cost
- **Evidence:**
  - **Confirmed facts:** `.github/workflows/plugin-evals.yml` ran its eval job for any pull request labelled `run-evals`, including pull requests that change no plugin. Inside the loop, plugins without changes make no model call, but the job still started a runner and installed Claude Code. `07dfa66` adds a `changes` job so the eval job skips when no plugin file changed; `Validate` passed on it (run `37455669608`).
  - **Inferences:** none.
  - **Open questions:** none.
- **Impact / risk:** Avoidable CI minutes on every labelled pull request; model cost only when a plugin changes.
- **Owner or responsible area:** `.github/workflows/plugin-evals.yml`.
- **Next action:** Verify with one labelled pull request that changes no plugin (the eval job must show as skipped) and one that does.
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

### DEBT-016 — Issue forms not confirmed in a signed-in browser

- **Status:** Pending
- **Category:** quality (issue intake)
- **Evidence:**
  - **Confirmed facts:** The API lists the three contact links of `.github/ISSUE_TEMPLATE/config.yml`; GitHub shows issue forms only to signed-in users. `51e96f6` gave the bug report dropdowns a neutral first option. The chooser screenshot of 2026-10-06 (DEBT-012) shows the security entries; no record says whether the two forms, the three contact links and the dropdown defaults were checked.
  - **Inferences:** none.
  - **Open questions:** Whether both forms render and their dropdowns start on the neutral option.
- **Impact / risk:** A broken form would stop bug reports or plugin proposals with no failure in CI.
- **Owner or responsible area:** repository maintainer (signed-in browser); `.github/ISSUE_TEMPLATE/`.
- **Next action:** Open `/issues/new/choose` signed in and check the two forms, the three contact links and the dropdown defaults.
- **Review condition:** Closes when the check is recorded with its date.
- **Related records:** DEBT-012; `51e96f6`.

### DEBT-017 — No rule makes plugins declare every external tool they run

- **Status:** Pending (maintainer decision)
- **Category:** compatibility
- **Evidence:**
  - **Confirmed facts:** `svelte-development` starts `svelteserver` and runs the project's `svelte-check`; its README lists them as prerequisites because the README template asks authors to (ADR `ADR_2026-10-06_supported-platforms`, `.claude/rules/plugins/readmes.md`). No rule or gate checks that a plugin's hooks, LSP and MCP servers only run declared tools, or that a plugin relies on no version-specific tool feature.
  - **Inferences:** A plugin can depend on an undeclared tool and fail on a user's machine while passing every gate.
  - **Open questions:** Whether the rule should be a review checklist item or a gate.
- **Impact / risk:** Plugins that fail silently for users who lack a tool or run another version of it.
- **Owner or responsible area:** repository maintainer (decision); `.claude/rules/plugins/authoring.md`, `docs/quality-bar.md`.
- **Next action:** Maintainer decides; if accepted, add the rule and the matching review or gate check.
- **Review condition:** Closes on the decision and the matching change.
- **Related records:** `ADR_2026-10-06_supported-platforms`.

### DEBT-018 — `drive_plugin.py` sessions run on the maintainer's login

- **Status:** Pending (maintainer decision)
- **Category:** quality (test isolation)
- **Evidence:**
  - **Confirmed facts:** `.claude/rules/testing/drive-plugin.md` records that credentials are keyed to `CLAUDE_CONFIG_DIR`, so an isolated configuration has no login, and the driver runs with the maintainer's own login. `claude plugin eval` is the clean-room check meanwhile.
  - **Inferences:** A `CLAUDE_CODE_OAUTH_TOKEN` in the driver's environment would authenticate an isolated configuration, as it does on CI.
  - **Open questions:** Where the token would live locally without exposing it to the plugin under test.
- **Impact / risk:** Smoke tests are not a clean room; the maintainer's account state can affect results.
- **Owner or responsible area:** repository maintainer (decision); `scripts/drive_plugin.py`.
- **Next action:** Maintainer decides; if accepted, pass the token by environment variable reference and update the rule.
- **Review condition:** Closes on the decision and, if accepted, a driven session with an isolated configuration.
- **Related records:** `.claude/rules/testing/drive-plugin.md`; DEBT-006, DEBT-007 (same token).

### DEBT-019 — The language-server probe fails inside a sandboxed Bash

- **Status:** Pending
- **Category:** quality (plugin behavior)
- **Evidence:**
  - **Confirmed facts:** `svelte-lsp-navigation` step 0 runs `command -v svelteserver` before the first LSP call and skips the language server when it prints nothing. In the 2026-10-08 smoke and pilot (case 08) it printed nothing inside the eval's Bash sandbox, which reads only the directories on `PATH` and not the symlink targets in them, while the LSP server, started by Claude Code outside the sandbox, answered `findReferences` in case 09.
  - **Confirmed facts (CI run `37749514321`):** on the GitHub runner the treatment arm of case 08 called the LSP tool in 3 of 3 runs, so the probe failure is specific to machines whose global binaries are symlinks outside `PATH` (nvm on macOS).
  - **Inferences:** Any user who runs Bash sandboxed with such a symlinked global install gets text search instead of semantic answers.
  - **Open questions:** Whether to probe with an LSP call (`documentSymbol` on a `.svelte` file) instead of Bash.
- **Impact / risk:** The plugin's language-server value is lost silently, and the LSP eval cases score 0 for the probe, not for the plugin.
- **Owner or responsible area:** `plugins/svelte-development/skills/svelte-lsp-navigation/SKILL.md` (procedure step 0, rule 9).
- **Next action:** Replace the Bash probe with an LSP call and its "No LSP server available" answer, release a patch, re-run cases 08 and 09.
- **Review condition:** Closes when case 08 calls the LSP tool in a sandboxed run.
- **Related records:** DEBT-005 (resolved); `.claude/rules/testing/plugin-evals.md` (sandbox bullets).

### DEBT-020 — Code review findings on the `svelte-development` 0.4.1 skills

- **Status:** Pending (maintainer decision)
- **Category:** quality (plugin behavior)
- **Evidence:**
  - **Confirmed facts:** `/code-review` of `svelte-development/activation` on 2026-10-08 reported, in the skills: ground rule 5 ("nothing new compared with the run before your change") against "diagnostics clean" in the best-practices step 6 and the navigation step 8; the `src/routes/**` path pattern, which also matches React and Solid projects and misses monorepo apps; and a docs-and-autofixer description that no longer names code pasted in the chat or the playground link.
  - **Inferences:** The review also inferred that `paths` narrows when a skill loads; the 2026-10-08 pilot contradicts it, because skills loaded for requests with no file open (cases 01, 07, 08).
  - **Open questions:** none.
- **Impact / risk:** Contradictory finishing rules and over-broad activation in non-Svelte projects.
- **Owner or responsible area:** `plugins/svelte-development/skills/*/SKILL.md`.
- **Next action:** Maintainer decides which to fix in a patch release; add a negative eval case for a React project with `src/routes/` if the pattern stays.
- **Review condition:** Closes when each finding is fixed or rejected with a reason.
- **Related records:** DEBT-004, DEBT-019.
