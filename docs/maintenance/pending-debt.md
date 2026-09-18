# Pending Debt

Use this file for unresolved maintenance work, known limitations, deferred
remediation, and follow-up tasks. Template: [`templates/pending-debt-template.md`](../../templates/pending-debt-template.md).

## Open Items

### DEBT-0003 — Shell scripts are not linted by `npm run check` or CI

- **Status:** Pending (partially mitigated 2026-09-18)
- **Category:** quality
- **Evidence:**
  - **Confirmed facts:** `.claude/hooks/*.sh` (ADR-0002) pass `shellcheck -x` with every optional check enabled and `shfmt -d`, verified on 2026-09-18. Since the ADR-0002 amendment, the PostToolUse hook runs `shfmt -w` and `shellcheck -x` on every `.sh` or shell-shebang file Claude edits, and blocks on findings. Since the second amendment, that includes files changed by Claude's Bash commands. `npm run check` runs Biome, unit tests, `generate`, `validate`, and `validate:claude`, but no shell linter. `.github/workflows/ci.yml` installs Node and the Claude Code CLI, not ShellCheck or shfmt.
  - **Inferences:** Edits that don't go through Claude's tools (a human editor, a merge, another program) can still regress a shell script without any gate noticing.
  - **Open questions:** Whether to pin the ShellCheck optional-check policy in a repo-local `.shellcheckrc`, so CI matches the maintainer's user-wide config, and how to install shfmt in CI.
- **Impact / risk:** Silent breakage of the hooks, including ones that deny edits.
- **Owner or responsible area:** `package.json` scripts, `.github/workflows/ci.yml`
- **Next action:** Add a repo-local `.shellcheckrc` that mirrors the enabled optional checks, plus a `lint:sh` step (`shellcheck -x` + `shfmt -d`) to `npm run check` and CI.
- **Review condition:** The next change to `.claude/hooks/`, or any CI workflow change.
- **Related records:** [ADR-0002](../decisions/adr-0002-project-hooks.md)

### DEBT-0004 — GitHub Actions and the pinned Claude Code CLI are not auto-updated; actions use mutable major tags

- **Status:** Pending
- **Category:** security, supply chain, compatibility
- **Evidence:**
  - **Confirmed facts:**
    - On 2026-09-18, every workflow uses `actions/checkout@v7`, `actions/setup-node@v7`, and `actions/stale@v11` (first-party, referenced by major tag).
    - `triage.yml`, `labels.yml`, and `tag-versions.yml` hold write tokens.
    - The Claude Code CLI is installed on CI runners only, pinned by
      `CLAUDE_CODE_VERSION: "2.1.276"` in `ci.yml` and `tag-versions.yml`. Both
      values must be bumped together; nothing checks that they agree or that
      the maintainer's local `claude` matches them.
    - There's no Dependabot config for the `github-actions` or `npm` ecosystems.
  - **Inferences:** A compromised or force-moved action tag would run in jobs that hold write tokens. Validator and tag behavior from newer Claude Code releases, and security fixes in dev dependencies, only arrive through manual bumps.
  - **Open questions:** Whether to pin actions by full commit SHA with Dependabot updates (the common hardening recommendation), and which labels Dependabot PRs get (`type: maintenance`, `area: ci` or `area: tooling`).
- **Impact / risk:** Supply-chain exposure in privileged workflows, and silent drift from upstream validator changes.
- **Owner or responsible area:** `.github/workflows/`, `.github/dependabot.yml`
- **Next action:** Pin actions by SHA with version comments. Add `.github/dependabot.yml` for `github-actions` and `npm`, using taxonomy labels.
- **Review condition:** Any new workflow, the next action major release, or a Claude Code release that changes `plugin validate` or `plugin tag`.
- **Related records:** [ADR-0003](../decisions/adr-0003-plugin-versioning-and-tagging.md), [ADR-0004](../decisions/adr-0004-issue-and-label-protocol.md)
