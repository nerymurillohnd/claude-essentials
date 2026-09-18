# Resolved Debt

Dated historical record of maintenance items resolved after this repo's
initial scaffold. Template: [`templates/resolved-debt-template.md`](../../templates/resolved-debt-template.md).

## Resolved Items

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
