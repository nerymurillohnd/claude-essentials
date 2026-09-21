---

status: accepted
date: 2026-09-18
decision-makers: Nery Samuel Murillo Tejada
consulted: Claude Code (Opus 5) — live docs, changelog, and CLI verification
informed: Contributors to this repository
supersedes: none
superseded-by: none

---

# Plugins use explicit semver; CI enforces bumps and tags `{name}--v{version}` with `claude plugin tag`

## Context and Problem Statement

Plugins in this marketplace aren't packages. Nothing is downloaded from a
release page. Users install a plugin with `/plugin install`, and they receive
new versions through `/plugin update` or auto-update from the catalog on
`main`.

Claude Code uses a plugin's resolved version as its update cache key. That
version comes from `plugin.json` `version`, then the marketplace entry, then
the git commit SHA of the source. For relative-path plugins in a git-hosted
marketplace, that SHA is the whole repository's commit
([version management](https://code.claude.com/docs/en/plugins-reference#version-management)).
With an explicit version, pushing commits without a bump never reaches
installed users. Other plugins' version constraints resolve only against tags
named `{plugin-name}--v{version}`
([plugin dependencies](https://code.claude.com/docs/en/plugin-dependencies#tag-plugin-releases-for-version-resolution)).

The templates already set `"version": "0.1.0"` without a stated strategy
(DEBT-0002). How should this multi-plugin public marketplace version its
plugins and publish those versions?

## Decision Drivers

- Installed users must reliably receive fixes, and only intended changes.
- Other plugins must be able to declare version constraints on ours.
- A forgotten bump or tag must be impossible, not merely discouraged.
- Use Claude Code's own tooling (`claude plugin tag`, `claude plugin validate`)
  wherever it exists, rather than reimplementing its checks.
- Don't present plugins as downloadable software.

## Considered Options

- Explicit semver, with bumps enforced in CI and tags created by CI with
  `claude plugin tag` on merge
- Explicit semver, tagged manually with `claude plugin tag --push`
- Explicit semver, plus GitHub Releases per version
- Commit-SHA versioning (omit `version`)

## Decision Outcome

Chosen option: "Explicit semver, enforced in CI, tagged by CI with
`claude plugin tag`".

- `version` is required and canonical (`schemas/plugin.schema.json`).
  Marketplace entries never carry one.
- `scripts/check-versions.mjs`, run by the `version-check` CI job, fails a PR
  in any of these cases:
  - a plugin whose **runtime** files changed keeps its version (unless a
    maintainer applied `bump: deferred`). README, `docs/`, LICENSE, CHANGELOG,
    and `plugin.json` metadata are a closed exempt list; any other path counts
    as runtime;
  - the version decreases or isn't canonical;
  - the tag already exists;
  - the CHANGELOG lacks `## [X.Y.Z] - YYYY-MM-DD`;
  - a removed plugin has no `renames` entry;
  - the official `claude plugin tag --dry-run` fails.
- `scripts/tag-versions.mjs`, run by the `Tag plugin versions` workflow on
  push to `main`, runs `claude plugin tag plugins/<name> --push` for each
  untagged version. That command validates the plugin, checks agreement
  between `plugin.json` and the marketplace entry, refuses dirty trees and
  existing tags, and creates annotated tags.
- There are no GitHub Releases: version notes are the plugin's `CHANGELOG.md`
  section.
- A tag ruleset makes `*--v*` tags immutable.
- CI installs a pinned Claude Code CLI on the runner only
  (`CLAUDE_CODE_VERSION` in `ci.yml` and `tag-versions.yml`). It is not a
  repo dependency: locally, the scripts use the maintainer's own `claude` on
  `PATH`.
- The bump rules are documented in
  [versioning.md](../contributing/versioning.md#which-number-to-bump).

### Consequences

- Good, because every merged plugin change reaches users as a new version,
  and constraints (`~1.2.0`) work.
- Good, because the rules live in one pure module
  (`scripts/lib/version-plan.mjs`) that CI, the triage bot, and the tagging
  script all use. Tag creation and its validation are Claude Code's own.
- Good, because nothing suggests a download: the marketplace is the only
  distribution channel.
- Bad, because every plugin change needs a bump and a CHANGELOG entry, even
  small ones. `bump: deferred` is the maintainer's escape hatch.
- Bad, because the CI-pinned CLI must be bumped deliberately to pick up
  upstream validator changes, and a newer local `claude` can disagree with CI
  until it is (DEBT-0004).
- Neutral: pre-1.0 plugins treat MINOR as breaking, per semver.

### Risks and mitigations

| Risk | Likelihood or condition | Impact | Mitigation or response | Owner |
| --- | --- | --- | --- | --- |
| The tagging workflow fails after merge (push rejected, runner outage) | Transient | Version reaches users but is untagged, so dependency ranges can't see it | Idempotent re-run via `workflow_dispatch`; SessionStart snapshot reports untagged versions | Maintainer |
| `bump: deferred` overused | Maintainer habit | Changes wait for the next bump | Label is visible on PRs; SessionStart reports "CHANGED since tag without a version bump" | Maintainer |
| Claude Code changes version resolution, the tag convention, or `plugin tag` behavior | Upstream release | Enforcement drifts from runtime | Changelog cross-check rule in CLAUDE.md; bumps of `CLAUDE_CODE_VERSION` are reviewed; revisit this ADR | Maintainer |

### Confirmation

| Criterion or claim | Verification method | Evidence or result | Responsible party | Review condition |
| --- | --- | --- | --- | --- |
| Rules classify new, bumped, deferred, backwards, retagged, removed, prerelease, and non-canonical cases | `npm test` (`version-plan.test.mjs`, `changelog.test.mjs`) | Pass, 2026-09-18 | Maintainer | Any change to `scripts/lib/version-plan.mjs` |
| `check-versions` enforces the rule on real git history, including `claude plugin tag --dry-run` | Scratch-clone scenario (plan Task 4 Step 3) | Pass, 2026-09-18 | Maintainer | Any change to `scripts/check-versions.mjs` |
| `tag-versions` tags exactly the untagged versions through `claude plugin tag` | `--dry-run` scenario (plan Task 5 Step 2) | Pass, 2026-09-18 | Maintainer | Any change to `scripts/tag-versions.mjs` |
| The tagging workflow tags on merge | First plugin merge to `main` | pending — first plugin version | Maintainer | First plugin version |
| Tags are immutable | Tag ruleset active (`gh api repos/{owner}/{repo}/rulesets`) | Active since 2026-09-18: ruleset "Immutable plugin version tags" (id 23654577), `update` + `deletion` on `refs/tags/*--v*`, `current_user_can_bypass: never` | Maintainer | Any ruleset change |

## More Information

- Resolves [DEBT-0002](../maintenance/resolved-debt.md). Official validation
  in CI (DEBT-0001) is resolved alongside, with the
  [ADR-0001 amendment](adr-0001-marketplace-distribution-model.md).
- Protocol: [versioning.md](../contributing/versioning.md). Design:
  [spec](../superpowers/specs/2026-09-18-repo-protocols-design.md).
- CLI behavior verified on a fixture with 2.1.276 and no credentials:
  - `plugin tag` refuses dirty trees, version mismatches, and existing tags,
    and creates annotated tags;
  - `plugin validate` of the marketplace root doesn't check plugin contents.
- Changelog corroboration (2.1.150 → 2.1.276): `claude plugin tag` was added
  and constrained dependencies auto-update to the highest satisfying tag
  (2.1.150); local-folder marketplaces honor tag pins (2.1.196). Nothing in
  the last six months changes the resolution order above.
- Revisit if Claude Code adds per-directory SHA versioning for relative-path
  plugins, or changes the tag convention.

### Amendment — 2026-09-19: direct pushes for non-runtime changes

- The maintainer's rule: only a change that alters a plugin's behavior needs a
  version bump, and only those changes go through a pull request. Everything
  else (documentation, READMEs, root files, tooling, metadata) is pushed
  directly to `main`. The earlier "every change through a PR" came from the
  repo-protocols plan's ruleset recommendation, not from the maintainer, and it
  contradicted his direct-commit workflow.
- The "Require green checks to merge into main" ruleset gets the repository
  admin role as a bypass actor (mode *Always*), which reverses DEBT-0005. The
  deletion and force-push ruleset and the immutable tag ruleset are unchanged.
- The checks move before the push instead of disappearing.
  `.claude/hooks/guard-push.sh` denies a direct push to `main` unless the tree
  is clean, `npm run check:versions` reports `bump: none`, and `npm run check`
  passes. A runtime change is sent to a PR.
- `version-check` now also runs on pushes to `main`, comparing against the
  commit before the push, so a runtime change that slipped through (a push made
  outside Claude) still turns `main` red. The tag dry-run stays on pull
  requests only, because after a push the tag workflow may already have created
  the tag.
- Accepted risk: a push made outside Claude Code skips the local gate. CI then
  catches it after the fact, not before. Recorded as DEBT-0011.

### Amendment — 2026-09-21: eval cases and plugin test suites are not runtime

- `evals/**` at the plugin root, and `test-*.sh` files and `tests/**` directories
  at any depth, join the exempt list. Claude never loads them: eval cases are
  consumed only by `claude plugin eval`, and a plugin's own suites run only under
  the maintainer gate. Editing them therefore needs no version bump and never
  changes the plugin the user installs. The exempt list stays closed; anything
  else under a plugin is still runtime.
- The rule has one home in the maintainer tooling (`EXEMPT_FILE`) and one
  mirror in `.claude/hooks/lib/plugin-paths.sh`; a parity test runs both over
  the same table so they cannot drift.
- Evals in CI select a plugin only when this runtime classification reports a
  change for it; an `evals/**`-only diff never runs a suite and never blocks a
  merge.
