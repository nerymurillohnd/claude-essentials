# Pending Debt

Use this file for unresolved maintenance work, known limitations, deferred
remediation, and follow-up tasks. Template: [`templates/pending-debt-template.md`](../../templates/pending-debt-template.md).

## Open Items

### DEBT-0019 — `agent-self-knowledge` ships a URL fetcher with no scheme or host validation

- **Status:** Pending (risk accepted)
- **Category:** security
- **Evidence:**
  - **Confirmed facts:** `plugins/agent-self-knowledge/skills/claude-code-docs/scripts/ccdocs.py` defines `cmd_raw`, which passes its argument straight to `fetch()` with no scheme or host check. The skill's `allowed-tools` grants `Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/ccdocs.py *)`, so any argument runs without a per-command approval prompt. Both vectors were reproduced on 2026-09-20: `raw file://<path>` printed a local canary file, and `raw https://example.com` fetched an unrelated host.
  - **Inferences:** Content the model reads (a documentation page, an issue, a web result) could induce a `raw` call that exfiltrates local data, since no prompt intervenes. The plugin is published publicly, so every installer inherits the capability.
  - **Open questions:** None. The vector is confirmed and the fix is known.
- **Impact / risk:** Arbitrary local file read and arbitrary outbound request, without user approval, on any machine where the plugin is enabled. The maintainer, Nery Samuel Murillo Tejada, accepted this explicitly on 2026-09-20 after seeing the reproduction and the proposed fix, to avoid any change to a retrieval behavior that had just been validated. Evidence that the fix is behaviorally inert: the clean-session test that validated the skill used `find`, `grep`, `outline`, `page`, `changelog` and `version` — `raw` was never called.
- **Owner or responsible area:** `plugins/agent-self-knowledge/skills/claude-code-docs/scripts/ccdocs.py`
- **Next action:** Add a host allowlist in `fetch()` restricted to `code.claude.com`, `raw.githubusercontent.com` and `registry.npmjs.org`, rejecting every other host and every non-`https` scheme; or remove `raw`. Either is a runtime change and needs a version bump and a CHANGELOG entry.
- **Review condition:** Close when `raw file:///etc/hosts` and `raw https://example.com` both exit non-zero with an explicit rejection, covered by a case in the plugin's test suite.
- **Related records:** [design spec](../superpowers/specs/2026-09-20-agent-self-knowledge-design.md), [plugin CHANGELOG](../../plugins/agent-self-knowledge/CHANGELOG.md)

### DEBT-0023 — `agent-self-knowledge` can report a settings key as not found when it exists undocumented

- **Status:** Pending
- **Category:** correctness
- **Evidence:**
  - **Confirmed facts:** The settings schema inside the installed Claude Code 2.1.278 binary defines `worktree.location`, described as "Directory under which Claude Code Desktop creates the worktrees of SSH sessions that run on this machine ... The CLI (--worktree, EnterWorktree, agent isolation) does not read it yet." The same key returns 0 hits across the 99,415 lines of `https://code.claude.com/docs/llms-full.txt`, which documents only `baseRef`, `bgIsolation`, `sparsePaths` and `symlinkDirectories` under `worktree`. Both measured on 2026-09-20. In the clean-session test the skill reported the key as non-existent.
  - **Inferences:** `ccdocs.py` reads the published documentation, the upstream changelog and the npm registry. None of the three carries the settings schema, so the skill's three-search negative protocol cannot distinguish "not documented" from "does not exist" for any settings key.
  - **Open questions:** How many other keys are in the shipped schema but not the docs. Whether the schema is exposed anywhere fetchable, or only inside the binary.
- **Impact / risk:** The bounded negative claim is the skill's headline behavior, and for settings keys it can be a false negative — the exact failure mode the plugin exists to prevent. A user told a key does not exist may build a workaround for a problem the product already solves.
- **Owner or responsible area:** `plugins/agent-self-knowledge/skills/claude-code-docs/`
- **Next action:** Decide whether the skill should read the installed binary's settings schema (for example `strings` over the executable, or a documented dump command if one exists) before reporting any settings key as absent, and whether that is worth the scope. Until then the README Limitations row carries the constraint.
- **Review condition:** Close when a settings key that exists only in the shipped schema is reported as undocumented-but-present, verified with `worktree.location` as the reproduction, and covered by an eval case.
- **Related records:** [design spec](../superpowers/specs/2026-09-20-agent-self-knowledge-design.md), [DEBT-0019](#debt-0019--agent-self-knowledge-ships-a-url-fetcher-with-no-scheme-or-host-validation)

### DEBT-0022 — `claude plugin validate --strict` accepts skill frontmatter that no YAML parser can read

- **Status:** Pending
- **Category:** tooling
- **Evidence:**
  - **Confirmed facts:** On 2026-09-20, four `SKILL.md` files in this repository carried a `description` written as a plain YAML scalar containing a colon followed by a space (`block-no-verify`, `ruff-hooks`, `shell-hooks`, `verify-completion`). The repository's `yaml` dependency rejects all four with `Nested mappings are not allowed in compact mappings at line 2, column 14`. `claude plugin validate --strict` on Claude Code 2.1.278 returned success for every one of them, and the full `npm run check` pipeline passed.
  - **Inferences:** Claude Code either extracts frontmatter line by line or parses it leniently, so a description that a conforming parser truncates or rejects still loads locally. Any consumer that reads the file with a standard YAML parser — an editor, a linter, a marketplace indexer, a future Claude Code release — would see a different description, or none.
  - **Open questions:** Which parser Claude Code uses, and whether the leniency is deliberate. Not established: what the runtime actually loads for such a description.
- **Impact / risk:** The only validator this repository can run against a published plugin does not catch a malformed skill description, which is the field that decides whether the skill is ever invoked. Four plugins were one commit away from publishing it.
- **Owner or responsible area:** `scripts/lib/skill-frontmatter.test.mjs`
- **Next action:** Report the gap upstream with the reproduction above. Locally, keep the repository's own gate as the authority and extend it if other frontmatter fields turn out to be parsed the same way.
- **Review condition:** Close when `claude plugin validate --strict` fails a plugin whose skill frontmatter is not valid YAML, verified with the same reproduction.
- **Related records:** [DEBT-0021](#debt-0021--plugin-name-restrictions-are-undocumented-upstream), [plugin-authoring rule](../../.claude/rules/plugin-authoring.md)

### DEBT-0021 — Plugin name restrictions are undocumented upstream

- **Status:** Pending
- **Category:** docs
- **Evidence:**
  - **Confirmed facts:** The maintainer reported on 2026-09-20 that a plugin name containing "Claude" is rejected, while the same word is accepted in a repository name, a marketplace name, and a skill name; the plugin was renamed to `agent-self-knowledge` as a result. A search of the full documentation corpus (99,415 lines of `llms-full.txt`) finds reserved-name rules only for MCP servers ("Claude Browser", "Claude Preview", `workspace`) and for agent names containing `:`. Nothing documents a restriction on plugin names.
  - **Inferences:** Either the restriction is enforced somewhere other than `claude plugin validate` (marketplace submission or claude.ai organization sync), or it comes from a rule that exists in code but not in the docs.
  - **Open questions:** Which surface rejects the name, with which exact message, and whether it applies to any occurrence of "claude" or only to certain forms.
- **Impact / risk:** A contributor can pick a name that passes every local gate and is rejected later, after the README, badges, tags and directory all carry it.
- **Owner or responsible area:** `docs/contributing/plugins.md`
- **Next action:** Reproduce the rejection, capture the exact message and the surface that emits it, then document the constraint in the contributing guide and report the documentation gap upstream.
- **Review condition:** Close when the constraint is reproduced with captured output and written into `docs/contributing/plugins.md`.
- **Related records:** [ADR-0001](../decisions/adr-0001-marketplace-distribution-model.md)

### DEBT-0018 — The catalog-metadata change shipped without a release review per plugin

- **Status:** Pending
- **Category:** process
- **Evidence:**
  - **Confirmed facts:** The branch `chore/repo-audit-and-catalog-metadata` changed the README and `plugin.json` of all four plugins and was pushed straight to `main` (`bump: none`, four plugins exempt). `.claude/rules/plugin-authoring.md` requires re-running `/plugin-release-review <id>` after every change touching runtime files, the README, or `plugin.json`. At the time of the push, `.claude/state/checklists/` held no record for `block-no-verify`, and the records for `ruff-quality` (2026-09-19T12:03:02Z), `shell-quality` (12:08:40Z), and `verify-completion` (09:02:21Z) all predated the last commit touching their plugin (2026-09-20T05:58Z, 05:58Z, 05:47Z) by about 18 hours. None of the three carries the `cross-plugin`, `metadata-fit`, or `bundled-reviews` items added to `.claude/skills/plugin-release-review/checklist.json` in this same branch.
  - **Inferences:** The substance was covered by two independent `repo-auditor` passes over the same content, which returned PASS on every content row (identity, descriptions, hook and Security tables, README contract, root catalog rows, eval numbers, LICENSE checksums, issue forms) after four content errors they found were fixed. What is missing is the review instrument itself, not a known defect.
  - **Open questions:** Whether the three new checklist items would surface anything the auditor's matrix does not already cover.
- **Impact / risk:** Four plugins are published from a state no release review covers, so a gap the review catches but `npm run check` and the auditor do not would reach users unreviewed. The maintainer accepted this explicitly on 2026-09-20, choosing to consolidate and sync `main` first and review afterwards.
- **Owner or responsible area:** `.claude/skills/plugin-release-review/`, `.claude/rules/plugin-authoring.md`
- **Next action:** Run `/plugin-release-review` to completion on `block-no-verify`, `ruff-quality`, `shell-quality`, and `verify-completion` against the content on `main`, and fix whatever they surface in a follow-up change.
- **Review condition:** Close when all four `.claude/state/checklists/plugin-release-review--<id>.json` records are complete and post-date the last commit touching their plugin.
- **Related records:** [ADR-0002](../decisions/adr-0002-project-hooks.md), [DEBT-0011](resolved-debt.md#debt-0011--2026-09-19--non-runtime-changes-are-pushed-directly-to-main-the-checks-run-before-the-push), [plugin-authoring rule](../../.claude/rules/plugin-authoring.md)

### DEBT-0016 — Python tests and repo scripts have no gates yet

- **Status:** Pending
- **Category:** tooling
- **Evidence:**
  - **Confirmed facts:** The maintainer's environment standard (global CLAUDE.md) runs Python through uv (`#!/usr/bin/env -S uv run --script` with inline dependencies) and gates every Python file with Ruff and Basedpyright. This repo's `npm run check` and CI run only `node:test` and bash suites; nothing installs uv or runs pytest or Basedpyright (2026-09-19). The basedpyright-quality design plans a Python gate core with pytest.
  - **Inferences:** A Python test or script added today would pass CI unlinted and untested.
  - **Open questions:** Whether CI installs uv with `astral-sh/setup-uv` (pinned by SHA) or reuses the pinned Ruff install.
- **Impact / risk:** Python code in plugins or tests would escape the gates every other language has.
- **Owner or responsible area:** `package.json` scripts, `.github/workflows/ci.yml`, `scripts/lint-*.mjs`
- **Next action:** Add `lint:py` (Ruff format and check, Basedpyright) and pytest via `uv run --script` to `npm run check` and CI, with uv pinned.
- **Review condition:** Close when CI fails on a Ruff, Basedpyright, or pytest error in a Python file under `plugins/` or `scripts/`.
- **Related records:** [basedpyright-quality design](../superpowers/specs/2026-09-19-basedpyright-quality-design.md)

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
