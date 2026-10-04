---
status: accepted
date: 2026-10-03
decision-makers:
  - "Nery Samuel Murillo (maintainer)"
---

# Marketplace name `claude-essentials` with a non-affiliation disclaimer

## Purpose

Fix the marketplace identifier users type after `@`, and make sure nobody mistakes the project for an Anthropic product.

## Scope

`.claude-plugin/marketplace.json` `name` and `description`, the root README, every plugin README, and plugin naming rules.

## Context and problem statement

Users install plugins as `<plugin>@<marketplace>`, so the marketplace name is permanent. Claude Code reserves official marketplace names and refuses names that imitate them. The name begins with "claude", which could suggest an official origin.

## Decision drivers

- The name must pass `claude plugin validate --strict` and the `claude plugin marketplace add` name check.
- Users must not be misled about affiliation.
- Plugin names must not pass as Anthropic's own plugins.

## Considered options

- `claude-essentials` with an explicit disclaimer
- A name without "claude"

## Decision outcome

Chosen option: **`claude-essentials` with an explicit disclaimer**, because it was verified at runtime on Claude Code 2.1.289: `validate --strict` passes and `marketplace add` accepts it in an isolated configuration. The disclaimer "Independent community project, not affiliated with or endorsed by Anthropic" appears in the marketplace description, the root README and every plugin README. Plugin names may not start with `claude-`, `anthropic-`, `anthropics-` or `cc-plugin-`, nor contain `claude` or `anthropic` as a word.

### Consequences

- Good, because the name describes the catalog and works with every Claude Code surface tested.
- Bad, because the "claude" prefix must stay paired with the disclaimer forever.

### Confirmation

`scripts/check_repo.py` fails when the disclaimer is missing from `marketplace.json` and enforces the plugin naming rules; `scripts/test_install.py` adds the marketplace in an isolated config on every CI run, so a future reservation of the name would fail CI. Revisit if Claude Code's reserved-name rules change (check the changelog routine in CLAUDE.md).

## Pros and cons of the options

### `claude-essentials` with a disclaimer

- Good, because it is clear and searchable.
- Bad, because it depends on Claude Code continuing to accept it.

### A name without "claude"

- Good, because it avoids any confusion.
- Bad, because it is less discoverable and was not required by the documented rules.

## More information

Docs: [Marketplace reference, reserved names](https://code.claude.com/docs/en/plugins/marketplace-reference#reserved-names) and [Plugin manifest reference, name](https://code.claude.com/docs/en/plugins/manifest-reference#name).
