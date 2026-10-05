---
status: accepted
date: 2026-10-05
decision-makers:
  - "Nery Samuel Murillo (maintainer)"
consulted:
  - "Claude Code by Anthropic (research, drafting and verification)"
---

# Remove the example plugin without a deprecation period

## Purpose

Let the pull request that adds the first real plugin remove `hello-example` at once, instead of deprecating it for a minor release and 30 days.

## Scope

The catalog entry and directory of `hello-example` only. Every other plugin keeps the deprecation period of [ADR per-plugin-versioning](ADR_2026-10-03_per-plugin-versioning.md).

## Context and problem statement

`hello-example` exists to prove the release pipeline end to end; its README and catalog description say it is safe to remove. The per-plugin-versioning ADR and `docs/releasing.md` require a deprecation release and at least 30 days before a plugin is removed, while the `new-plugin` project skill says the first real plugin's pull request removes the example directly. The two instructions conflict.

## Decision drivers

- The deprecation period protects users who depend on a plugin; nobody depends on an example that does nothing.
- A deprecation release of the example would spend a release on a plugin about to disappear.
- The `renames` entry still migrates any install cleanly.

## Considered options

- Remove the example directly in the first real plugin's pull request
- Deprecate it first and remove it 30 days later

## Decision outcome

Chosen option: **remove it directly**, with `"renames": {"hello-example": null}`, the label and labeler rules removed, a dated `### Removed` note in the root changelog, and the published tag `hello-example--v0.1.1` and its GitHub Release kept.

### Consequences

- Good, because the catalog shows only real plugins from the first release on.
- Bad, because anyone who installed the example sees it removed without notice; the `renames` entry handles the install.

### Confirmation

The pull request that adds `svelte-development` carries the removal; reviewers check the `renames` entry, the root changelog note and that the old tag still exists.

## Pros and cons of the options

### Remove directly

- Good, because it is one pull request.
- Bad, because it is an exception to a general rule.

### Deprecate first

- Good, because it follows the general rule.
- Bad, because it protects no one and costs a release.

## More information

The general rule stays in [ADR per-plugin-versioning](ADR_2026-10-03_per-plugin-versioning.md) and [docs/releasing.md](../../releasing.md#deprecate-or-remove-a-plugin).
