---
status: accepted
date: 2026-10-03
decision-makers:
  - "Nery Samuel Murillo (maintainer)"
---

# Release automation: hand-written changelogs, local release script, CI publication

## Purpose

Decide how a plugin or marketplace release is prepared, tagged and published.

## Scope

`scripts/release.py`, `.github/workflows/release.yml`, plugin and marketplace changelogs.

## Context and problem statement

Releases need a version bump, a dated changelog section, a signed commit, a tag and a GitHub Release. Every commit and tag in this repository must be signed with the maintainer's key, and the repository has no dependency manifest.

## Decision drivers

- Signed commits and tags with the maintainer's key.
- User-facing notes written for people, including migration steps.
- Use official tooling where it exists; no new dependencies without need.

## Considered options

- Hand-written changelogs, a stdlib Python release script, `claude plugin tag`, CI publication
- release-please (bot release pull requests, per-component tags)
- git-cliff generating changelogs from commits

## Decision outcome

Chosen option: **hand-written changelogs, a stdlib Python release script, `claude plugin tag`, CI publication**. Contributors add notes under `## [Unreleased]`. A maintainer runs `uv run scripts/release.py plugin <name> <major|minor|patch>`, which moves the notes into a dated section, bumps `plugin.json`, validates, commits (signed) and calls `claude plugin tag` (signed annotated `<name>--v<version>`). Pushing the tag runs the release workflow, which verifies the tag against the manifest, validates the plugin and publishes the changelog section as the GitHub Release.

### Consequences

- Good, because commits and tags carry the maintainer's signature and the official tag format.
- Good, because notes are written for users, not derived from commit subjects.
- Bad, because releases need a maintainer at a terminal.

### Confirmation

Unit tests cover changelog rewriting and the Migration requirement; the release workflow refuses tags that do not match the manifest. Revisit git-cliff or release-please when there are several plugins with frequent releases.

## Pros and cons of the options

### Local release script

- Good, because it has zero dependencies and honors signing.
- Bad, because it is code this repository maintains.

### release-please

- Good, because it is fully automated and supports `tag-separator` for the official format.
- Bad, because its commits and tags are made by a bot through the API, not signed with the maintainer's key.

### git-cliff

- Good, because it generates changelogs from Conventional Commits.
- Bad, because with no plugins and no history it adds configuration and a second source of notes without solving a current problem.

## More information

See [docs/releasing.md](../releasing.md) for the procedure.
