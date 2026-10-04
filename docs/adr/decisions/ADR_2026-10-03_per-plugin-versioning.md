---
status: accepted
date: 2026-10-03
decision-makers:
  - "Nery Samuel Murillo (maintainer)"
---

# Independent SemVer per plugin, version only in `plugin.json`, official tags

## Purpose

Define how plugin and marketplace versions are expressed, where they live and how releases are tagged.

## Scope

`version` in `plugin.json` and `marketplace.json`, plugin and marketplace changelogs, git tags.

## Context and problem statement

Claude Code computes a plugin's version from `plugin.json` first, then the marketplace entry; users only receive an update when that version changes. A mismatching entry version makes `claude plugin validate` warn and `claude plugin tag` refuse. Claude Code does not check versions against SemVer.

## Decision drivers

- Users must receive every release, and only releases.
- One source of truth, no synchronization step.
- Tag names that official tooling understands and that never collide between plugins.

## Considered options

- SemVer in `plugin.json` only, official `<name>--v<version>` tags
- Omit `version` and let the commit SHA be the version
- Version in both `plugin.json` and the entry

## Decision outcome

Chosen option: **SemVer in `plugin.json` only, official `<name>--v<version>` tags**. Each plugin is versioned independently. The marketplace has its own version in `marketplace.json` and tags `marketplace--v<version>` (the name `marketplace` is reserved for plugins).

- MAJOR: a breaking change for users, such as a renamed or removed skill, agent or command, changed hook behavior, a new required setting or a removed component. Requires a `### Migration` section (what broke, who is affected, exact steps).
- MINOR: new components or backward-compatible features.
- PATCH: fixes and documentation.
- Deprecation: deprecate in a minor release with a note under `### Deprecated`, keep the component for at least one further minor release and 30 days, remove it in the next major.

### Consequences

- Good, because `claude plugin update` delivers exactly the releases maintainers make.
- Good, because `claude plugin tag` produces and checks the tag.
- Bad, because a merged change without a release does not reach users until the next release.

### Confirmation

`scripts/check_repo.py` enforces SemVer, no `version` in entries, changelog/manifest agreement and a Migration section for majors; `scripts/check_pr.py` forbids version changes outside release pull requests; the release workflow verifies tag and manifest agree.

## Pros and cons of the options

### SemVer in plugin.json only

- Good, because version, tag and changelog always agree.
- Bad, because every release needs an explicit bump.

### Commit SHA as version

- Good, because no bumps are needed.
- Bad, because every commit is a user-visible update and SemVer meaning is lost.

## More information

Docs: [Versions and updates](https://code.claude.com/docs/en/plugins/loading#versions-and-updates), [plugin tag](https://code.claude.com/docs/en/plugins/cli-reference#plugin-tag). Runtime check on 2.1.289: an entry with the same version passes; only a mismatch warns.
