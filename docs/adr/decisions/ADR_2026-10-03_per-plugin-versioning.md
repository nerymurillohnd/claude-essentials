---
status: accepted
date: 2026-10-03
decision-makers:
  - "Nery Samuel Murillo (maintainer)"
---

# Only plugins are versioned: SemVer in `plugin.json`, released in the same pull request

## Purpose

Define what is versioned, where versions live, when a change needs a release, how releases are tagged, and which changes go through a pull request.

## Scope

`version` in `plugin.json`, the catalog `.claude-plugin/marketplace.json`, plugin and catalog changelogs, git tags, `scripts/check_pr.py`, and the path every change takes into `main`.

## Context and problem statement

Claude Code computes a plugin's version from `plugin.json` first, then the catalog entry, and caches each plugin by name and version: users receive a new copy only when that version changes. A mismatching entry version makes `claude plugin validate` warn and `claude plugin tag` refuse. Claude Code does not check versions against SemVer.

The catalog's own `version` (top-level or `metadata.version`) delivers nothing: users refresh to the latest commit of the catalog's branch whatever that number says. A user who pins the catalog to a tag freezes every plugin at that commit and stops receiving plugin fixes until the next catalog tag.

A change merged into a plugin without a new version gives users of the same version different files: earlier installs keep their cached copy, later installs get the new commit.

## Decision drivers

- Users must receive every change, and only released changes.
- One version per thing that is delivered, in one place.
- Tag names that official tooling understands and that never collide between plugins.
- Release discipline is checked by a gate, not by memory.

## Considered options

- Version only plugins, in `plugin.json`, releasing every plugin change in its own pull request; the catalog has no version
- Version both plugins and the catalog, with catalog tags users can pin
- Omit `version` and let the commit SHA be the version

## Decision outcome

Chosen option: **version only plugins, in `plugin.json`, releasing every plugin change in its own pull request; the catalog has no version**.

- Each plugin has an independent SemVer version `MAJOR.MINOR.PATCH` in `plugin.json` only: never in its catalog entry, no `v` prefix, no pre-release or build suffix. New plugins start at `0.1.0`.
- Levels: MAJOR for a breaking change for users (a renamed or removed skill, agent or command, changed hook behavior, a new required setting), with a `### Migration` section stating what broke, who is affected and the exact steps; MINOR for new components, backward-compatible features and deprecations; PATCH for fixes and documentation of the plugin, including README changes.
- Every change inside `plugins/<name>/` ships with a single-step bump of that plugin in the same pull request, prepared with `scripts/bump_version.py`. A pull request may release several plugins, each with its own bump, and carries exactly one `semver:` label naming the highest bump among the plugins it releases. New plugins need no label.
- Plugin tags use the official format `<name>--v<version>`, created by `claude plugin tag` on the merged commit.
- The catalog has no `version` and no tags. Its history is the root `CHANGELOG.md`, in dated `## YYYY-MM-DD` sections (UTC): plugins added, deprecated, removed or renamed, and changes to entries or distribution. Every change to `marketplace.json` adds a dated note.
- Deprecating a component inside a plugin: deprecate in a minor release with a note under `### Deprecated`, keep the component for at least one further minor release and 30 days, remove it in the plugin's next major.
- Deprecating a whole plugin follows the same notice period; the plugin is then removed from the catalog in a pull request with a `renames` entry and a dated catalog note ([docs/releasing.md](../../releasing.md)).
- `plugins/**`, `marketplace.json`, workflows and `CODEOWNERS` change only through pull requests, where `scripts/check_pr.py` and the security review run. Docs, scripts, tests, rules, ADRs and the root README may be pushed directly by the maintainer, signed, after `python3 scripts/check.py` passes.

### Consequences

- Good, because a version always identifies exactly the files users receive, and `claude plugin update` delivers every merged plugin change.
- Good, because there is one number per delivered thing, and nothing to keep in step with a catalog version.
- Bad, because even a README typo in a plugin is a PATCH release.
- Bad, because the catalog cannot be pinned as a stable snapshot; offering one would need a separate channel marketplace, as the official docs describe.

### Confirmation

`scripts/check_repo.py` enforces SemVer, no `version` in entries or the catalog, changelog and manifest agreement, and the dated catalog changelog. `scripts/check_pr.py` enforces the same-pull-request release, the single-step bump, the matching label, the Migration section and the catalog note. `tests/test_gates.py` covers each rule; the release workflow verifies that tag and manifest agree.

## Pros and cons of the options

### Plugins only, released in the same pull request

- Good, because version, tag and changelog always agree with what users receive.
- Bad, because every plugin change needs an explicit bump.

### Versioned catalog with pinnable tags

- Good, because users could pin a stable catalog.
- Bad, because a pinned catalog freezes plugin fixes, and keeping a catalog number in step with plugin releases doubles every release for a number Claude Code ignores.

### Commit SHA as version

- Good, because no bumps are needed.
- Bad, because every commit is a user-visible update and SemVer meaning is lost.

## More information

Docs: [Versions and updates](https://code.claude.com/docs/en/plugins/loading#versions-and-updates), [Release a new version](https://code.claude.com/docs/en/plugins/host-marketplace#release-a-new-version), [Hold users on one version](https://code.claude.com/docs/en/plugins/host-marketplace#hold-users-on-one-version), [Marketplace top-level fields](https://code.claude.com/docs/en/plugins/marketplace-reference#top-level-fields), [plugin tag](https://code.claude.com/docs/en/plugins/cli-reference#plugin-tag). Procedure: [docs/releasing.md](../../releasing.md).

2026-10-05: [ADR remove-example-plugin-without-deprecation](ADR_2026-10-05_remove-example-plugin-without-deprecation.md) removes `hello-example` without the deprecation period. The rule still applies to every other plugin.
