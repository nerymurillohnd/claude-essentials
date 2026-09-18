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
