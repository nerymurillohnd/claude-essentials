---
status: superseded
date: 2026-10-03
decision-makers:
  - "Nery Samuel Murillo (maintainer)"
---

# Release process: editorial changelogs, a bump script, manual signed tags, CI publication

## Purpose

Decide how a plugin release is prepared, tagged and published, and how much of it is automated now.

## Scope

`scripts/bump_version.py`, `scripts/release_notes.py`, `.github/workflows/release.yml`, plugin changelogs.

## Context and problem statement

Releases need user-facing notes, a version bump, a dated changelog section, a signed commit, a signed tag and a GitHub Release. Every commit and tag must be signed with the maintainer's key, and the repository has no dependency manifest. Which release steps deserve to be combined is only known after real releases.

## Decision drivers

- Changelogs describe changes that matter to users, not commit subjects.
- Signed commits and tags with the maintainer's key, in the official `<name>--v<version>` format.
- Automate only what is understood; no single "release" command before real releases show which steps belong together.

## Considered options

- Editorial changelogs, a stdlib bump script, manual commit and `claude plugin tag`, CI publication
- One script that bumps, commits and tags
- release-please (bot release pull requests, per-component tags)
- git-cliff generating the changelogs from commits

## Decision outcome

Chosen option: **editorial changelogs, a stdlib bump script, manual commit and `claude plugin tag`, CI publication**.

- Each plugin keeps a hand-written `CHANGELOG.md`; notes are written under `## [Unreleased]` in the pull request that changes the plugin.
- `python3 scripts/bump_version.py plugin <name> <level>` checks the notes (a MAJOR needs `### Migration`), moves them into a dated section, bumps `plugin.json` (the only place the version lives, so the catalog needs nothing else), regenerates the README content that shows the version and validates. It never commits, tags or pushes.
- The bump is committed in that same pull request ([ADR per-plugin-versioning](ADR_2026-10-03_per-plugin-versioning.md)). After the merge, the maintainer runs `claude plugin tag` on the merged commit, which creates the signed annotated tag after checking manifest and catalog agree.
- Pushing the tag runs the release workflow: `scripts/release_notes.py verify` checks tag and manifest, the plugin is validated, and `scripts/release_notes.py notes` publishes that version's changelog section as the GitHub Release.
- `uvx git-cliff@2.14.2 --include-path "plugins/<name>/**"` may be used occasionally to draft notes from history without adding a dependency; the draft is reviewed and rewritten, and never decides the bump or writes the changelog.

### Consequences

- Good, because notes are written for users and every commit and tag carries the maintainer's signature.
- Good, because nothing is automated before its value is known.
- Bad, because a release takes a few manual commands, documented in [docs/releasing.md](../../releasing.md).

### Confirmation

Unit tests cover changelog rewriting and the Migration requirement; `scripts/check_pr.py` rejects a plugin change without its single-step bump, matching changelog section and `semver:` label; the release workflow refuses tags that do not match the manifest. Revisit after the first real releases: combining the steps into one command, or adopting git-cliff or release-please, needs a new ADR.

## Pros and cons of the options

### Bump script plus manual commit and tag

- Good, because each step is visible and reviewable, with zero dependencies.
- Bad, because the maintainer runs several commands per release.

### One script that bumps, commits and tags

- Good, because a release is one command.
- Bad, because it fixes a workflow before any real release has tested it.

### release-please

- Good, because it is fully automated and supports `tag-separator` for the official format.
- Bad, because its commits and tags are made by a bot through the API, not signed with the maintainer's key.

### git-cliff as the changelog source

- Good, because it generates changelogs from Conventional Commits and filters by path for per-plugin versions.
- Bad, because it adds configuration and a second source of notes, and commit subjects are not user-facing notes.

## More information

Superseded on 2026-10-04 by [ADR release-orchestration](ADR_2026-10-04_release-orchestration.md): the release is now orchestrated by the `release-plugin` project skill; the scripts and tag flow decided here are unchanged.

Procedure: [docs/releasing.md](../../releasing.md). git-cliff: [monorepo usage](https://git-cliff.org/docs/usage/monorepos/); pinned execution with uv: [uv tools](https://docs.astral.sh/uv/concepts/tools/).
