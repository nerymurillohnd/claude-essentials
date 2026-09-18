# Pending Debt

Use this file for unresolved maintenance work, known limitations, deferred
remediation, and follow-up tasks. Template: [`templates/pending-debt-template.md`](../../templates/pending-debt-template.md).

## Open Items

### DEBT-0001 — Official `claude plugin validate` is not part of the CI gate

- **Status:** Pending
- **Category:** quality, compatibility
- **Evidence:**
  - **Confirmed facts:** Claude Code 2.1.276 ships `claude plugin validate <path>` (with `--strict` and `--json`), which checks marketplace and plugin manifests plus skill, agent, and command frontmatter. `npm run check` and `.github/workflows/ci.yml` run only the repo's Ajv schema validation (`scripts/validate-marketplace.mjs`). On 2026-09-18, `claude plugin validate .` passes with one warning ("Marketplace has no plugins defined").
  - **Inferences:** The repo schemas can drift from Claude Code's own manifest rules, for example unrecognized fields that the runtime tolerates but `--strict` flags. That drift would go unnoticed until a user install fails.
  - **Open questions:** Whether CI can install the `claude` CLI without authentication for `plugin validate`, and whether `--strict` would reject the catalog-only `kind` field (ADR-0001).
- **Impact / risk:** A plugin that passes `npm run check` could still be rejected or partially loaded by Claude Code for users.
- **Owner or responsible area:** `package.json` scripts, `.github/workflows/ci.yml`
- **Next action:** Add the first plugin, run `claude plugin validate . --strict` and `claude plugin validate plugins/<name> --strict` locally, and decide how to handle `kind`. Then add the command to `npm run check` and CI.
- **Review condition:** The first plugin lands under `plugins/`, or the SessionStart snapshot reports a `claude plugin validate` failure.
- **Related records:** [ADR-0001](../decisions/adr-0001-marketplace-distribution-model.md), [ADR-0002](../decisions/adr-0002-project-hooks.md)

### DEBT-0002 — Plugin versioning in templates is misaligned with live Claude Code docs

- **Status:** Pending — needs a versioning-strategy decision (ADR)
- **Category:** compatibility, distribution correctness
- **Evidence:**
  - **Confirmed facts:**
    - `templates/plugin-bundle`, `templates/plugin-skill-only`, and `templates/plugin-agent-only` each set `"version": "0.1.0"` in `.claude-plugin/plugin.json`. Nothing in `README.md`, `docs/contributing/plugins.md`, or `templates/README.md` states a versioning strategy or its consequence.
    - Live docs, checked 2026-09-18 ([version management](https://code.claude.com/docs/en/plugins-reference#version-management), [version resolution](https://code.claude.com/docs/en/plugin-marketplaces#version-resolution-and-release-channels)): Claude Code uses the resolved version as the update cache key. With an explicit `version`, "pushing new commits without bumping it has no effect" for installed users. Omitting `version` in a git-hosted marketplace falls back to the commit SHA. The docs recommend explicit versions for "published plugins with stable release cycles" and commit-SHA versions for plugins "under active development". They warn against setting `version` in both `plugin.json` and the marketplace entry.
    - Live docs ([tag plugin releases](https://code.claude.com/docs/en/plugin-dependencies#tag-plugin-releases-for-version-resolution)): dependency constraints resolve only against tags named `{plugin-name}--v{version}` that match `plugin.json`'s `version`, created with `claude plugin tag`.
    - `templates/CHANGELOG-reusable-template.md` builds compare links from `{{PREVIOUS_TAG}}...{{VERSION}}`. That is a bare version tag, which in this multi-plugin repo would collide across plugins and doesn't match the official convention.
  - **Inferences:** A contributor copying a template gets version pinning by default without knowing it. Content edits merged without a bump never reach installed users, and nothing but the new PostToolUse and SessionStart hooks (ADR-0002) warns about it.
  - **Open questions:** Which strategy this marketplace adopts: explicit semver with `claude plugin tag` releases (needed if other plugins will declare version constraints on ours), or commit-SHA versioning (every merge to `main` ships).
- **Impact / risk:** Silent non-delivery of fixes to installed users, or broken dependency resolution for downstream plugins.
- **Owner or responsible area:** `templates/plugin-*`, `templates/CHANGELOG-reusable-template.md`, `docs/contributing/plugins.md`
- **Next action:** Record the strategy in an ADR. Align the templates' `version` field, the CHANGELOG tag links (`{plugin-name}--v{version}`), and the contributing guide to it. Then have `npm run check` enforce it.
- **Review condition:** Before the first plugin is added under `plugins/`.
- **Related records:** [ADR-0002](../decisions/adr-0002-project-hooks.md), DEBT-0001

### DEBT-0003 — Shell hooks are not linted by `npm run check` or CI

- **Status:** Pending
- **Category:** quality
- **Evidence:**
  - **Confirmed facts:** `.claude/hooks/*.sh` (ADR-0002) pass `shellcheck -x` with every optional check enabled and `shfmt -d`, verified by hand on 2026-09-18. `npm run check` runs only Biome, `generate`, and `validate`. `.github/workflows/ci.yml` installs only Node.
  - **Inferences:** A later edit to a hook can regress without any gate noticing. The PostToolUse Biome hook doesn't lint `.sh` files.
  - **Open questions:** Whether to pin the ShellCheck optional-check policy in a repo-local `.shellcheckrc`, so CI matches the maintainer's user-wide config, and how to install shfmt in CI.
- **Impact / risk:** Silent breakage of the hooks, including ones that deny edits.
- **Owner or responsible area:** `package.json` scripts, `.github/workflows/ci.yml`
- **Next action:** Add a repo-local `.shellcheckrc` that mirrors the enabled optional checks, plus a `lint:sh` step (`shellcheck -x` + `shfmt -d`) to `npm run check` and CI.
- **Review condition:** The next change to `.claude/hooks/`, or any CI workflow change.
- **Related records:** [ADR-0002](../decisions/adr-0002-project-hooks.md)
