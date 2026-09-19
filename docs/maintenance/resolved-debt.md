# Resolved Debt

Dated historical record of maintenance items resolved after this repo's
initial scaffold. Template: [`templates/resolved-debt-template.md`](../../templates/resolved-debt-template.md).

## Resolved Items

### DEBT-0014 — 2026-09-19 — Gate plugins enforce every stated minimum and test their installer and degraded modes

- **Original pending record:** none. Found by `/plugin-release-review` while building ruff-quality and shell-quality 0.1.0.
- **Resolved debt:** Four classes of gap, each caught before release:
  - The README stated Git ≥ 2.18 and Ruff ≥ 0.16, but `preflight` checked neither Git nor (outside the recommended mode) the Ruff version, although the Stop gate's `ruff format --check --output-format` needs 0.16.
  - Porting `manage.sh` from one plugin to the other silently dropped `os_kind`; `assess` and `preflight` printed `command not found` and still exited 0.
  - A test fixture built with `${4:-{\}}` produced an empty payload under `/bin/bash` 3.2 only, so the suite's post cases tested nothing there.
  - Without `jq`, the guard denies every `Write`/`Edit`/`Bash` call (intended fail-closed), but the message did not say how to recover.
- **Resolution:**
  - Both `manage.sh` preflights check Git ≥ 2.18; ruff-quality checks Ruff ≥ 0.16 in every mode.
  - Each plugin ships `scripts/test-manage.sh`: every command in a sandbox, failing on `command not found`, `unbound variable`, or `syntax error`, and asserting that preflight reports each minimum. `npm test` runs it under `bash` and `/bin/bash`.
  - Fixture builders abort the suite (`built_fail`) when jq cannot build a payload.
  - The guard's fail-closed message names the recovery (`! bash … manage.sh uninstall`), both READMEs list it under Limitations, and each `test-gate.sh` runs the guard with `PATH` lacking `jq` and a full realistic payload.
- **Positive verification:** `test-gate.sh` 99/99 (ruff-quality) and 82/82 (shell-quality), `test-manage.sh` all passing, on bash 3.2.57 and 5.3.20.
- **Negative verification:** with `os_kind` removed from the shell `manage.sh`, `test-manage.sh` reported 2 failures; with the old fixture, the ruff suite failed 23 post cases under `/bin/bash`.
- **Owner or responsible area:** `plugins/ruff-quality/skills/ruff-hooks/`, `plugins/shell-quality/skills/shell-hooks/`
- **Residual risk / follow-up:** the suites run with the local and CI runner's `jq`, Ruff, ShellCheck, and shfmt versions only (see DEBT-0012).
- **Related records:** DEBT-0012, DEBT-0013
- **Superseded by:** none

### DEBT-0013 — 2026-09-19 — A new plugin's shell suites and scripts are tested and linted before its first commit

- **Original pending record:** none. Found while building a new plugin on 2026-09-19.
- **Resolved debt:** `listShellFiles()` read `git ls-files`, so `npm test` and `lint:sh` skipped every script a new plugin adds until it was committed. A branch adding a plugin passed `npm run check` without running that plugin's 110-case suite; running it needed `git add -N`. The same listing kept tracked files that had been deleted.
- **Resolution:** `scripts/lib/shell-files.mjs` lists tracked files plus untracked files Git doesn't ignore (`--cached --others --exclude-standard`), and drops paths missing on disk. `scripts/lib/shell-files.test.mjs` builds a temporary repository with tracked, untracked, ignored, and deleted scripts and requires exactly the tracked and untracked ones. `.claude/skills/plugin-release-review/references/consistency-matrix.md` also gained a row for hook command form against the minimum Claude Code version, another class of gap found in the same review.
- **Positive verification:** with a new plugin still untracked, `npm test` ran its `test-*.sh` suite under `/opt/homebrew/bin/bash` and `/bin/bash`, and `lint:sh` picked up its scripts.
- **Negative verification:** before the fix the new test failed with `actual: [ 'deleted.sh', 'tracked.sh' ]` against `expected: [ 'tracked.sh', 'untracked.sh' ]`; the ignored script stays out.
- **Owner or responsible area:** `scripts/lib/shell-files.mjs`
- **Residual risk / follow-up:** plugin suites still run only with the local and CI runner's `jq`.
- **Related records:** DEBT-0003
- **Superseded by:** none

### DEBT-0011 — 2026-09-19 — Non-runtime changes are pushed directly to `main`; the checks run before the push

- **Original pending record:** none. The maintainer raised it on 2026-09-19 after a README-only commit was rejected by the required-checks ruleset.
- **Resolved debt:** DEBT-0005 removed every bypass from the required-checks ruleset, and `version-check` only ran on pull requests. So every change needed a PR, even a one-word README fix. The maintainer's rule was never that: only a change that alters a plugin's behavior needs a version bump and a PR. The requirement came from the repo-protocols plan's recommendation.
- **Resolution:**
  - The repository admin role is a bypass actor (mode *Always*) on ruleset 23655894. The maintainer made this change in the GitHub UI.
  - `.claude/hooks/guard-push.sh` denies a direct push to `main` unless the tree is clean, `check:versions` reports `bump: none`, and `npm run check` passes. A runtime change is sent to a PR.
  - `version-check` also runs on pushes to `main`, against the commit before the push.
  - `CLAUDE.md`, `docs/contributing/versioning.md`, `.claude/rules/plugin-delivery.md`, and `pr-delivery` describe the split: direct push for non-runtime changes, a PR for version bumps.
- **Positive verification:** `push-guard.test.mjs` allows a clean non-runtime push to `main`. The first direct push after this change went through the real gate.
- **Negative verification:** `push-guard.test.mjs` denies a runtime change, failing version rules, a failing check, and a dirty tree.
- **Owner or responsible area:** GitHub rulesets, `.claude/hooks/guard-push.sh`, `.github/workflows/ci.yml`
- **Residual risk / follow-up:** A push made outside Claude Code skips the local gate; CI's `check` and `version-check` on `main` catch it after the push, not before. The deletion, force-push, and tag rulesets keep no bypass.
- **Related records:** DEBT-0005 (superseded), [ADR-0003 amendment 2026-09-19](../decisions/adr-0003-plugin-versioning-and-tagging.md), [ADR-0002](../decisions/adr-0002-project-hooks.md)
- **Superseded by:** none

### DEBT-0010 — 2026-09-19 — Delivery gaps from block-no-verify 0.1.x closed with a push guard, a delivery checklist, and project rules

- **Original pending record:** none. Found while shipping block-no-verify 0.1.0–0.1.1 and fixed in the following PR.
- **Resolved debt:** Shipping one plugin took three review rounds. The README eval table went stale after the skill description changed. A push after the #11 merge recreated the deleted branch `docs/block-no-verify-catalog` with a commit that never reached `main` (fixed in #12). The tag push failed server-side on reruns. "Done" was reported before every step was verified.
- **Resolution:**
  - `.claude/hooks/guard-push-merged-branch.sh` (PreToolUse, Bash) denies pushing a branch that was published before but no longer exists on the remote.
  - The repo skill `pr-delivery` starts a checklist that `checklist-gate.sh` enforces. Its verify commands prove that every plugin version is tagged on origin, the feature branch is gone locally and remotely, `main` equals `origin/main`, and the tree is clean.
  - `checklist.sh start` refuses while another checklist is unfinished. Verify commands receive `$CHECKLIST_SUBJECT`.
  - `.claude/rules/plugin-delivery.md` records the working rules: design first, continuous review, Bash 3.2 and degraded-mode testing, edit verification, current numbers, branch hygiene, tagging, and the definition of done.
  - `scripts/lib/text-files.test.mjs` fails when a tracked or new text file holds a raw control character. A tool turned a written NUL escape into the byte twice, the second time in this change.
- **Positive verification:** `scripts/lib/push-guard.test.mjs` shows a deleted published branch is denied in eight spellings, under `bash` and `/bin/bash`. `checklist-gate.test.mjs` shows the subject reaches verify commands. The delivery verify commands pass against the real repository after #12.
- **Negative verification:** New branches, live branches, deletions, tag pushes, and non-push commands are allowed, and an unreachable remote fails open. A second checklist start is refused, and the delivery `branches` verify fails while the feature branch still exists.
- **Owner or responsible area:** `.claude/hooks/`, `.claude/skills/pr-delivery/`, `.claude/rules/`
- **Residual risk / follow-up:** Both are guardrails for Claude sessions, not controls. The push guard fails open offline and doesn't see pushes made outside Claude. The merge and CI items are evidence Claude records, not commands the gate re-runs, because re-running them would need GitHub credentials in the hook.
- **Related records:** [ADR-0002](../decisions/adr-0002-project-hooks.md), [ADR-0003](../decisions/adr-0003-plugin-versioning-and-tagging.md), DEBT-0008
- **Superseded by:** none

### DEBT-0008 — 2026-09-18 — Plugin README contract and root catalog row are enforced by `npm run validate`

- **Original pending record:** none — found and fixed in the same change (post-release review of `block-no-verify` 0.1.0).
- **Resolved debt:** Nothing enforced the plugin README template beyond the `**Kind:**` line, and the contributing guide never asked for a root README catalog row. `block-no-verify` 0.1.0 shipped with the root catalog still showing "No plugins published yet", the template's Cowork install and update steps replaced, and two requirement badges (Bash, jq) that were not in the template's badge catalog.
- **Resolution:**
  - `scripts/lib/readme-contract.mjs`, run by `npm run validate` (and so by `npm run check` and CI), derives the required sections, their order, and the allowed badges from `templates/plugin-README-reusable-template.md`. It rejects missing, unknown, or reordered sections, `{{placeholders}}`, more than one alert per section, unlabeled code blocks, badges outside the catalog, a Version badge that doesn't read the plugin's own `plugin.json`, and Installation without the Claude Code and Cowork steps. It also requires one root catalog row per plugin, sorted, whose link, kind, and surface statuses match the plugin.
  - `docs/contributing/plugins.md`, the PR template, and `CLAUDE.md` state the catalog-row step and what `validate` checks.
  - Bash and jq were added to the template's badge catalog; the root catalog and the plugin README were corrected.
  - Follow-up checks from a seeded-defect test of the review skill: each plugin `LICENSE` must match the canonical Apache-2.0 SHA-256 and `plugin.json` must declare `Apache-2.0`; "≥" requirement badges must match the Requirements table and the catalog row; a `network-none` plugin must not ship scripts that call network tools; every CHANGELOG heading needs a link definition. The three plugin-shape CHANGELOG templates were re-synced with the master (guidance sentence, compare links).
  - The judgment layer became the repo skill `.claude/skills/plugin-release-review/`, whose checklist is enforced by the `checklist-gate.sh` Stop hook (ADR-0002 amendment).
- **Positive verification:** `npm run check` passes; `scripts/lib/readme-contract.test.mjs` and `scripts/lib/checklist-gate.test.mjs` cover each rule with fixtures and check this repository's files. In a seeded-defect copy of the repo, the review skill found all six planted defects plus three real 0.1.0 bugs, and the extended validator now catches three of the six mechanically.
- **Negative verification:** Run against the tree before the fix, the validator reports all four gaps found by the manual review (badges Bash/jq, Cowork install steps, Cowork update line, placeholder catalog row).
- **Owner or responsible area:** `scripts/lib/`, `templates/`, `docs/contributing/`
- **Residual risk / follow-up:** Content quality (accuracy of claims, tone) still needs review; the validator checks structure and consistency only.
- **Related records:** [ADR-0001](../decisions/adr-0001-marketplace-distribution-model.md), [PR #10](https://github.com/nerymurillohnd/claude-essentials/pull/10)
- **Superseded by:** none

### DEBT-0001 — 2026-09-18 — `claude plugin validate --strict` runs in `npm run check` and CI

- **Original pending record:** DEBT-0001 in [pending-debt.md](pending-debt.md) (removed on resolution; see git history).
- **Resolved debt:** Only the repo's Ajv schemas gated manifests, so drift from Claude Code's own rules could go unnoticed. The open questions were whether CI can run the CLI without authentication, and whether `--strict` rejects `kind`.
- **Resolution:**
  - CI installs a pinned Claude Code CLI on the runner only (`CLAUDE_CODE_VERSION` in `ci.yml` and `tag-versions.yml`); locally the scripts use the maintainer's `claude` on `PATH`. It is not a repo dependency.
  - `npm run validate:claude` (`scripts/validate-claude.mjs`) runs `claude plugin validate --strict --json` on `.` and on every `plugins/<name>`, because the root run doesn't check plugin contents. It tolerates only the empty-marketplace warning while `plugins/` is empty.
  - The check runs in `npm run check` and the CI `check` job.
  - `kind` became derived ([ADR-0001 amendment](../decisions/adr-0001-marketplace-distribution-model.md)).
- **Positive verification:** Three fixture plugins copied from the templates pass `--strict` in a scratch clone (plan Task 2 Step 10). The CLI ran with a clean `HOME` and no credentials.
- **Negative verification:** A broken `SKILL.md` fails at `plugins/<name>` (exit 1). A skill-only plugin that gains an agent fails the README Kind check. Before the amendment, `kind` failed `--strict` on every plugin.
- **Owner or responsible area:** `scripts/`, `.github/workflows/ci.yml`, `.github/workflows/tag-versions.yml`
- **Residual risk / follow-up:** `CLAUDE_CODE_VERSION` must be bumped deliberately, and a newer local `claude` can disagree with CI until it is (DEBT-0004).
- **Related records:** [ADR-0001](../decisions/adr-0001-marketplace-distribution-model.md), [ADR-0002](../decisions/adr-0002-project-hooks.md), [ADR-0003](../decisions/adr-0003-plugin-versioning-and-tagging.md)
- **Superseded by:** none

### DEBT-0002 — 2026-09-18 — Explicit semver adopted, enforced in CI, tagged by `claude plugin tag`

- **Original pending record:** DEBT-0002 in [pending-debt.md](pending-debt.md) (removed on resolution; see git history).
- **Resolved debt:** The templates pinned `"version": "0.1.0"` without a stated strategy, the CHANGELOG template linked bare-version tags, and nothing required a version bump.
- **Resolution:** [ADR-0003](../decisions/adr-0003-plugin-versioning-and-tagging.md).
  - `version` is required and must be canonical semver (schema).
  - `version-check` enforces a bump plus a dated CHANGELOG entry on every PR that changes a plugin's runtime files (a closed list exempts README/docs/LICENSE/CHANGELOG and `plugin.json` metadata), including `claude plugin tag --dry-run`.
  - The `Tag plugin versions` workflow runs `claude plugin tag --push` for every untagged version. There are no GitHub Releases: plugins reach users through the marketplace.
  - The templates and [versioning.md](../contributing/versioning.md) document the rule.
- **Positive verification:** `npm test` passes the version-plan and changelog suites. In the scratch-clone scenario, `check-versions` exits 0 for a new plugin and a committed bump, and `tag-versions --dry-run` selects only untagged versions.
- **Negative verification:** In the same scenario, an unbumped change exits 1 with "still 0.1.0", a missing CHANGELOG entry exits 1, `--verify-tag` on a dirty tree exits 1, and the schema rejects a missing, `v`-prefixed, or build-metadata version.
- **Owner or responsible area:** `schemas/`, `scripts/`, `.github/workflows/`, `templates/`
- **Residual risk / follow-up:** The live tagging workflow and tag ruleset stay unverified until the first plugin version (ADR-0003 Confirmation).
- **Related records:** [ADR-0003](../decisions/adr-0003-plugin-versioning-and-tagging.md), [ADR-0002](../decisions/adr-0002-project-hooks.md)
- **Superseded by:** none

### DEBT-0003 — 2026-09-18 — Shell scripts are linted by `npm run check` and CI

- **Original pending record:** DEBT-0003 in [pending-debt.md](pending-debt.md) (removed on resolution; see git history).
- **Resolved debt:** Only Claude's own edits were linted, by the PostToolUse hook. `npm run check` and CI had no shell linter, so edits by a person, another program, or a merge could regress the hooks unnoticed.
- **Resolution:**
  - A repo-local `.shellcheckrc` mirrors the maintainer's policy: the same ten optional checks, and no global disables.
  - `npm run lint:sh` (`scripts/lint-shell.mjs`) runs `shellcheck -x` and `shfmt -d` on every tracked shell script. It finds them with the hook's rule: `.sh` files, plus files with an `sh`/`bash` shebang (`scripts/lib/shell-files.mjs`).
  - `lint:sh` is part of `npm run check`.
  - The CI `check` job installs ShellCheck 0.11.0 and shfmt 3.14.1 from their official releases, verifies each download with `sha256sum --check`, and then runs `lint:sh`.
- **Positive verification:** All 5 hook scripts pass under the repo rc. Unit tests cover shell-script detection (`shell-files.test.mjs`). The SHA-256 of both downloads was verified locally against GitHub's asset digests.
- **Negative verification:** A tracked script containing `echo $1` makes `lint:sh` fail with SC2086.
- **Owner or responsible area:** `.shellcheckrc`, `scripts/lint-shell.mjs`, `.github/workflows/ci.yml`
- **Residual risk / follow-up:** The tool versions in CI are bumped by hand, together with their checksums. Contributors need ShellCheck and shfmt installed locally.
- **Related records:** [ADR-0002](../decisions/adr-0002-project-hooks.md)
- **Superseded by:** none

### DEBT-0004 — 2026-09-18 — Actions pinned by SHA, Dependabot enabled, Claude Code CLI pin kept consistent

- **Original pending record:** DEBT-0004 in [pending-debt.md](pending-debt.md) (removed on resolution; see git history).
- **Resolved debt:** Workflows that hold write tokens referenced actions by mutable major tags. Nothing updated the actions or the npm dev dependencies. The `CLAUDE_CODE_VERSION` pins could drift apart between workflows, and from the maintainer's local CLI, without anyone noticing.
- **Resolution:**
  - Every `uses:` in `.github/workflows/` is pinned to a full commit SHA, with a version comment: `actions/checkout` v7.0.1, `actions/setup-node` v7.0.0, `actions/stale` v11.0.0.
  - `.github/dependabot.yml` updates `npm` and `github-actions` weekly. Dependabot also maintains SHA pins that carry a version comment. Alerts and security updates are enabled.
  - `npm run validate` fails if two workflows that install Claude Code set different values of `CLAUDE_CODE_VERSION`, if one sets none, or if a value isn't canonical semver.
  - `npm run validate:claude` prints a note when the local `claude` differs from CI's pin.
- **Positive verification:** `actionlint` is clean. `npm run validate` passes on the real workflows (both at 2.1.276). The unit tests for `checkClaudeCodeVersions` pass.
- **Negative verification:** The unit tests confirm a missing pin, a `v`-prefixed pin, and diverging pins are each reported.
- **Owner or responsible area:** `.github/workflows/`, `.github/dependabot.yml`, `scripts/lib/repo-metadata.mjs`
- **Residual risk / follow-up:** Dependabot can't bump `CLAUDE_CODE_VERSION`, because it's an env value, so it's bumped by hand in both workflows at once; validation enforces that they match.
- **Related records:** [ADR-0003](../decisions/adr-0003-plugin-versioning-and-tagging.md), [ADR-0004](../decisions/adr-0004-issue-and-label-protocol.md)
- **Superseded by:** none

### DEBT-0005 — 2026-09-18 — The `main` status-check ruleset no longer lets admins bypass it

- **Original pending record:** none. Found and fixed the same day, so it never had a pending entry.
- **Resolved debt:** The repo-protocols plan specified "no bypass actors" for `main`. The live ruleset "Require green checks to merge into main" (id 23655894) was created with the repository admin role as a bypass actor in mode `always`. That let the only maintainer push straight to `main`, or merge a red PR, without `check` or `version-check`. `version-check` runs only on `pull_request` events, so any direct push to `main` needed that bypass.
- **Resolution:** On 2026-09-18, `bypass_actors` was set to `[]` with `gh api -X PUT repos/nerymurillohnd/claude-essentials/rulesets/23655894`. The ruleset's name, target, enforcement, conditions, and rules are unchanged; a diff before the change confirmed that only `bypass_actors` would differ. All three rulesets now have no bypass actors.
- **Positive verification:** The ruleset reads back `enforcement=active`, `bypass=[]`, `current_user_can_bypass=never`. `gh api repos/nerymurillohnd/claude-essentials/rules/branches/main` returns `deletion`, `non_fast_forward`, `required_status_checks`.
- **Negative verification:** The maintainer's `current_user_can_bypass` is `never`. A direct push to `main` was not attempted: it would be rejected now, and attempting it would itself be the prohibited action.
- **Owner or responsible area:** GitHub repository rulesets
- **Residual risk / follow-up:** If GitHub Actions can't run, nothing can merge. The remedy is a deliberate, audited, temporary ruleset edit — never a standing bypass. Every change to `main` goes through a PR, including docs-only changes.
- **Related records:** [repo-protocols plan](../superpowers/plans/2026-09-18-repo-protocols.md), [ADR-0003](../decisions/adr-0003-plugin-versioning-and-tagging.md)
- **Superseded by:** DEBT-0011 (2026-09-19): the maintainer allows direct pushes to `main` for non-runtime changes, gated locally.

