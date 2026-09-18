# Repository protocols: issues, plugin versioning, labels — design

- **Date:** 2026-09-18
- **Status:** approved (decisions confirmed by the maintainer in session)
- **Plan:** [2026-09-18-repo-protocols.md](../plans/2026-09-18-repo-protocols.md)
- **Resolves:** DEBT-0001 (official validator in CI), DEBT-0002 (versioning strategy)

## Problem

Before the first plugin lands, the marketplace needs three protocols that
every public, multi-plugin marketplace depends on:

1. **Issues** — how the community reports bugs, requests features, proposes
   plugins, and asks questions; how the maintainer triages them.
2. **Plugin version bumps** — how a change to `plugins/<name>/` reaches
   installed users, and how each version is tagged.
3. **Labels** — one taxonomy for issues and PRs, including a PR's version-bump
   impact, kept as code.

**What a "release" means here.** Plugins aren't packages or downloadable
software. A plugin version reaches users when three things happen:

- the maintainer merges a bumped `version` in `plugin.json` to `main`;
- Claude Code sees the new version string in the marketplace, through
  `/plugin update` or auto-update;
- the version gets its git tag `{name}--v{version}`, which Claude Code uses to
  resolve other plugins' dependency constraints.

There are no GitHub Releases, archives, or "latest" badges. Release notes live
in each plugin's `CHANGELOG.md`.

## Verified constraints (live docs and CLI, 2026-09-18; Claude Code 2.1.276)

- Claude Code uses the resolved version as the update cache key. Resolution
  order: `plugin.json` `version` → marketplace entry `version` → git commit SHA
  of the source (including relative-path sources in a git-hosted
  marketplace) → … ([version management](https://code.claude.com/docs/en/plugins-reference#version-management)).
- With an explicit version, "pushing new commits without bumping it has no
  effect". The docs recommend explicit versions for "published plugins with
  stable release cycles", and say to follow semver and keep a `CHANGELOG.md`.
- Don't set `version` in both `plugin.json` and the marketplace entry.
- Dependency constraints resolve only against tags `{plugin-name}--v{version}`
  ([plugin dependencies](https://code.claude.com/docs/en/plugin-dependencies#tag-plugin-releases-for-version-resolution)).
  Prereleases are excluded from ranges unless the range opts in.
- `claude plugin tag [path] [--dry-run] [--push] [-m msg]` was verified on a
  fixture:
  - it validates the plugin;
  - it refuses a mismatch between `plugin.json` and the marketplace entry
    ("Version mismatch …");
  - it refuses a dirty tree under the plugin or `marketplace.json`;
  - it refuses an existing tag;
  - it creates an **annotated** tag;
  - it runs without authentication.
- `claude plugin validate <path> [--strict] [--json]` was verified the same
  way:
  - it runs without authentication;
  - **validating the marketplace root doesn't check plugin contents**; a broken
    `SKILL.md` only fails at `plugins/<name>`;
  - `--strict` fails any plugin that has the catalog-only `kind` field
    ("Unknown field 'kind'");
  - an empty marketplace warns "Marketplace has no plugins defined".
- A removed or renamed plugin belongs in `marketplace.json` `renames`
  (append-only; `null` means removed).
- GitHub issue forms: labels that don't exist are silently not applied. Issue
  `type:` needs an organization, and this repo is owned by a user account.
- Repo state: public, no branch protection or rulesets, default labels,
  Discussions disabled, private vulnerability reporting enabled, no tags.

## Decisions (maintainer-confirmed)

| # | Decision | Rejected alternative |
| --- | --- | --- |
| D1 | **Explicit semver** is required in every `plugin.json`. Every PR that changes a plugin's **runtime** files bumps its version and adds a dated CHANGELOG entry, unless a maintainer applies `bump: deferred`. Files Claude never loads need no bump: `README.md`, `CHANGELOG.md`, `LICENSE*`, `docs/**`, and `plugin.json` metadata. That exempt list is closed. A `## [Unreleased]` note is recommended for notable exempt changes, not enforced. | Commit-SHA versioning. With relative-path sources, the SHA is the whole repo's commit, so every merge would re-ship every plugin, and dependency constraints couldn't be used. |
| D2 | **CI tags versions** on push to `main`, using the official `claude plugin tag --push` for every untagged plugin version. No GitHub Releases. | Manual `claude plugin tag --push`, where a forgotten tag breaks dependency resolution silently. GitHub Releases, which imply downloadable artifacts that don't apply to plugins. |
| D3 | **Questions go to GitHub Discussions (Q&A)**. Issues are for actionable work only. Blank issues are disabled. | A `type: question` issue form. |
| D4 | **Stale automation only for `status: needs-info`**: stale after 14 days without activity, closed as *not planned* 7 days later. PRs and all other issues are never touched. | No automation. |
| D5 | **Plugin `kind` is derived from the plugin's structure**, not declared in `plugin.json`, and the plugin README's `**Kind:**` line must match. This lets `claude plugin validate --strict` run in CI for the marketplace and every plugin. | Keep `kind` and run the validator without `--strict`, which leaves warnings permanently unenforced. |

## Protocol summary

### Versioning and tagging (ADR-0003)

- `version` is required by `schemas/plugin.schema.json`. It must be canonical
  semver without build metadata (`1.2.3`, `2.0.0-beta.1`). Marketplace entries
  never carry `version`: the generator doesn't emit it.
- Renames: a renamed skill directory, agent, or command changes an invocation
  name and is MAJOR (MINOR pre-1.0). A folder inside a skill is PATCH. A
  renamed plugin needs `renames` and is MAJOR. CI enforces *that* a bump
  happened; the bump level is reviewed against the table in `versioning.md`.
- Bump rules for a plugin:
  - MAJOR: a removed or renamed skill, agent, command, hook, MCP server, or
    argument; a changed invocation name; an incompatible behavior change; or a
    raised Claude Code minimum version.
  - MINOR: new components, options, or opt-in behavior.
  - PATCH: fixes and wording corrections that change model behavior.
  - Pre-1.0: breaking changes bump MINOR.
  - Prerelease: `X.Y.Z-<id>.N`.
- `scripts/check-versions.mjs` (CI job `version-check` on PRs) fails when any
  of these holds:
  - a plugin whose runtime files changed has the same version (unless the PR
    has `bump: deferred`). Paths are classified relative to `plugins/<name>/`:
    `README.md`, `CHANGELOG.md`, `LICENSE*`, `docs/**`, and `plugin.json`
    metadata (`description`, `displayName`, `keywords`, `author`, `homepage`,
    `repository`, `license`) are exempt, and every other path is runtime;
  - the version decreased or isn't canonical;
  - the tag already exists;
  - `CHANGELOG.md` lacks `## [X.Y.Z] - YYYY-MM-DD`;
  - a removed plugin is missing from `renames`;
  - `claude plugin tag --dry-run` fails (with `--verify-tag`, which CI passes).
- `scripts/tag-versions.mjs` (workflow `tag-versions.yml`) runs on push to
  `main` touching `plugins/**`. For each untagged version, it runs
  `claude plugin tag plugins/<name> --push`. It's idempotent.
- A tag ruleset makes `*--v*` tags immutable (no update or delete).

### Official validation (DEBT-0001)

- `@anthropic-ai/claude-code` is pinned as an exact devDependency, so local
  checks and CI run the same validator.
- `npm run validate:claude` runs `claude plugin validate --strict --json` on
  `.` and on every `plugins/<name>`. It tolerates only the empty-marketplace
  warning while `plugins/` is empty. It's part of `npm run check` and CI.

### Labels (ADR-0004)

Families, in `.github/labels.json` (authored) plus derived plugin labels:

| Family | Labels | Applied by |
| --- | --- | --- |
| `type:` | `bug`, `feature`, `plugin-proposal`, `docs`, `maintenance`, `security` | Issue forms; the maintainer on PRs |
| `status:` | `needs-triage`, `needs-info`, `accepted`, `blocked`, `stale` | Forms (`needs-triage`), maintainer, triage bot (author reply), stale bot |
| `priority:` | `critical`, `high`, `low` (no label = normal) | Maintainer |
| `area:` | `plugins`, `catalog`, `ci`, `tooling`, `templates`, `docs`, `community` | Triage bot on PRs (path rules) |
| `plugin:` | one per `plugins/<name>/` (derived, never authored) | Triage bot (PR paths, issue dropdown) |
| `bump:` | `major`, `minor`, `patch`, `prerelease`, `initial`, `none` (computed); `deferred` (maintainer-only) | Triage bot on PRs, from the same rules as `check-versions` |
| community | `good first issue`, `help wanted` (unprefixed, because GitHub features these names) | Maintainer |

Default labels map through `aliases`, so renames keep existing associations:
`bug` → `type: bug`, `enhancement` → `type: feature`, `documentation` →
`type: docs`. Pruning `duplicate`, `invalid`, `wontfix`, `question`, and
`accessibility` is a separate, manual `--prune` run. GitHub's native close
reasons (*completed*, *not planned*, *duplicate*) replace resolution labels.

`scripts/sync-labels.mjs` is a dry run by default, with `--apply` and
`--prune`. The `labels.yml` workflow runs `--apply` (never `--prune`) on push
to `main` when `.github/labels.json` or any `plugin.json` changes.

### Issues (ADR-0004)

- Issue forms: `bug-report`, `feature-request`, `plugin-proposal`,
  `docs-report`. `config.yml` disables blank issues and links to Discussions
  Q&A, private security advisories, and upstream Claude Code issues.
- Each form's **Affected plugin** dropdown (where present) is generated by
  `npm run generate` from `plugins/` on disk. CI fails if it's stale.
- Triage flow: the form applies `type:*` and `status: needs-triage`. The
  triage bot adds `plugin:*` or `area: catalog` from the dropdown. The
  maintainer then sets `status: accepted`, `needs-info`, or `blocked`, plus a
  priority, or closes the issue with a native reason. An author reply on a
  `needs-info` issue moves it back to `needs-triage` and clears `stale`.
- The triage workflow uses `pull_request_target` to label fork PRs. It checks
  out the **base** branch only, runs `npm ci --ignore-scripts` without a
  cache, and reads PR content through the API as data. It never executes PR
  code.

## Out of scope (tracked, not done here)

- DEBT-0003: shell lint in CI.
- Pinning actions by SHA, and Dependabot. This becomes new DEBT-0004.
- Branch ruleset on `main`, which requires PRs plus the `check` and
  `version-check` checks. It's a governance change that is proposed in the
  rollout task and needs explicit confirmation.
