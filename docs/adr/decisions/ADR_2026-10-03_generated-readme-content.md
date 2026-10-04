---
status: accepted
date: 2026-10-03
decision-makers:
  - "Nery Samuel Murillo (maintainer)"
---

# Generated README content that cannot drift from the plugins

## Purpose

Keep the root README catalog and the factual parts of every plugin README in sync with manifests and plugin files.

## Scope

`README.md`, `plugins/*/README.md`, `templates/readme/`, `scripts/sync_readmes.py`.

## Context and problem statement

READMEs repeat facts that live elsewhere: versions, categories, component lists, install commands, configuration options and what a plugin runs. Hand-maintained copies drift, and a stale Permissions section is a security problem.

## Decision drivers

- Facts have one source of truth.
- Authors still write the explanations only they can write.
- The check runs in `uv run scripts/check.py` and agrees with the formatter.

## Considered options

- Root README fully rendered from a template; plugin READMEs with generated blocks between markers
- Hand-written READMEs reviewed manually

## Decision outcome

Chosen option: **rendered root README and generated blocks in plugin READMEs**. Generated blocks: header (badges, description, navigation), requirements, installation, components, configuration (when `userConfig` exists), runtime (under Permissions, when the plugin runs code), uninstall, documentation and license. Badges are static shields.io images built from manifest data plus GitHub's native workflow badge. Output passes through Prettier. Links out of a plugin directory are absolute GitHub URLs, because plugins are copied alone into the user's cache.

### Consequences

- Good, because a version bump, a new skill or a new MCP server updates the READMEs automatically.
- Bad, because generated blocks must not be edited by hand; changes go to the templates or the source files.

### Confirmation

`scripts/sync_readmes.py --check` fails on stale content or missing or inapplicable blocks; `scripts/check_repo.py` requires the section headings.

## Pros and cons of the options

### Generated content

- Good, because documentation and configuration agree by construction.
- Bad, because the generator is code to maintain.

### Hand-written READMEs

- Good, because they are fully flexible.
- Bad, because facts drift silently.

## More information

Authoring rules for READMEs: [docs/readme-guide.md](../../readme-guide.md).
