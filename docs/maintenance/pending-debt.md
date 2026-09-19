# Pending Debt

Use this file for unresolved maintenance work, known limitations, deferred
remediation, and follow-up tasks. Template: [`templates/pending-debt-template.md`](../../templates/pending-debt-template.md).

## Open Items

### DEBT-0012 — Plugin hook suites run only against the CI runner's jq

- **Status:** Pending
- **Category:** quality
- **Evidence:**
  - **Confirmed facts:** `verify-completion`'s `analyze.jq` first used `capture(...)?.field` (jq 1.8 syntax) and a variable named `$end` (reserved in jq 1.6). Its 110-case suite passed on the maintainer's jq 1.8.2, failed 55 cases on jq 1.7.1 and failed to compile on jq 1.6 (2026-09-19). After the fix it passes on jq 1.6 (built from the release tarball), 1.7.1, and 1.8.2. `npm test` runs `plugins/**/test-*.sh` only with the `jq` on `PATH`; the GitHub runner provides one version.
  - **Inferences:** Any plugin that claims "jq ≥ 1.6" (both current plugins do) can regress on older jq without CI noticing; jq 1.6 is what Ubuntu 22.04 ships.
  - **Open questions:** Whether to download pinned jq 1.6 and 1.7.1 binaries in CI (Linux x86-64 release assets exist for both) or run the suites in an `ubuntu:22.04` container.
- **Impact / risk:** A hook that fails to compile fails open, so users on older jq silently lose enforcement.
- **Owner or responsible area:** `.github/workflows/ci.yml`, `scripts/lib/plugin-shell-tests.test.mjs`
- **Next action:** Run every plugin shell suite under each jq version a plugin README claims, with the versions pinned in CI.
- **Review condition:** Close when CI fails on a jq-1.8-only construct in a plugin that claims jq ≥ 1.6.
- **Related records:** [verify-completion design](../superpowers/specs/2026-09-19-verify-completion-design.md)

### DEBT-0009 — Released CHANGELOG entries can be rewritten without CI noticing

- **Status:** Pending
- **Category:** quality
- **Evidence:**
  - **Confirmed facts:** In a seeded-defect copy of the repository, the released `## [0.1.0]` entry of `block-no-verify` was edited (a false "Python 3 handler" line) and `npm run check` plus `npm run check:versions` still passed. Only the review skill caught it (2026-09-18).
  - **Inferences:** A released entry is a record of what shipped under an immutable tag; editing it silently rewrites history for users reading the CHANGELOG.
  - **Open questions:** Whether `check:versions` should compare each tagged `## [X.Y.Z]` section with its content at tag `<id>--vX.Y.Z`, and how to allow deliberate typo fixes (a label such as `changelog: amend`).
- **Impact / risk:** Misleading release notes; low frequency.
- **Owner or responsible area:** `scripts/lib/version-plan.mjs`, `scripts/check-versions.mjs`
- **Next action:** Extend `check:versions` to diff tagged sections against their tag, with a test and an explicit override label.
- **Review condition:** Close when CI fails on an edited released entry and the override is documented.
- **Related records:** DEBT-0008 in [resolved-debt.md](resolved-debt.md)

### DEBT-0006 — The repo marketplace schema rejects `renames: null`

- **Status:** Pending
- **Category:** correctness
- **Evidence:**
  - **Confirmed facts:** In `schemas/marketplace.schema.json`, `renames.additionalProperties` is `{ "type": "string" }`. Ajv rejects `{"renames": {"old": null}}` with `/renames/old must be string` and accepts `{"old": "new"}` (reproduced 2026-09-18). Claude Code documents `null` as the value for a removed plugin ([plugin-marketplaces](https://code.claude.com/docs/en/plugin-marketplaces)). [versioning.md](../contributing/versioning.md) tells contributors to use `null` on removal, and `version-check` requires a `renames` entry for every removed plugin.
  - **Inferences:** The first plugin removal will fail `npm run validate` while following the documented procedure.
  - **Open questions:** none.
- **Impact / risk:** Blocks the documented removal flow. The workaround would be a string value, which misstates the removal as a rename.
- **Owner or responsible area:** `schemas/marketplace.schema.json`, `scripts/validate-marketplace.mjs`
- **Next action:** Allow `["string", "null"]` and add a unit test for both values. `schemas/claude-code/marketplace.schema.json` already models this correctly. Planned for phase 1 of the [spec-alignment design](../superpowers/specs/2026-09-18-marketplace-spec-alignment-design.md).
- **Review condition:** Close when the test passes and a removal fixture validates.
- **Related records:** [ADR-0003](../decisions/adr-0003-plugin-versioning-and-tagging.md)

### DEBT-0007 — The plugin-shape READMEs link to an `evals/` directory the templates don't ship

- **Status:** Pending
- **Category:** quality
- **Evidence:**
  - **Confirmed facts:** `templates/plugin-{bundle,skill-only,agent-only}/README.md` link to `evals/` in their Verification section. No template contains `evals/` (link check run 2026-09-18, PR #6).
  - **Inferences:** A plugin copied from a template ships a broken link until its author adds an eval suite.
  - **Open questions:** The exact grader-file syntax for "skill must not fire" (`tool_used`, `min`/`max`, `arm`) must be verified against [plugin-evals](https://code.claude.com/docs/en/plugin-evals) before scaffolding it.
- **Impact / risk:** A broken link in every new plugin, and the spec's "evals required" rule is not enforced yet.
- **Owner or responsible area:** `templates/`, `scripts/lib/`
- **Next action:** Add a verified `evals/` skeleton (a trigger case and a non-trigger case) to each shape, plus the structural validator. Planned for phase 2 of the [spec-alignment design](../superpowers/specs/2026-09-18-marketplace-spec-alignment-design.md).
- **Review condition:** Close when every shape ships `evals/`, the link resolves, and `npm run validate` enforces the suite shape.
- **Related records:** [PR #6](https://github.com/nerymurillohnd/claude-essentials/pull/6)
