---
status: accepted
date: 2026-10-03
decision-makers:
  - "Nery Samuel Murillo (maintainer)"
---

# Testing approach: isolated install tests and gates proven by injected defects

## Purpose

Decide how plugin installation and the gates themselves are tested without touching anyone's real Claude Code configuration.

## Scope

`scripts/test_install.py`, `tests/`, `python3 scripts/check.py test-install`, `python3 scripts/check.py tests`, CI.

## Context and problem statement

Static validation does not prove that a plugin installs and loads the way users receive it. Installing into a maintainer's real configuration would break the rule that plugins are for third parties and never installed locally by default. A gate that never fails proves nothing.

## Decision drivers

- Never modify the real Claude Code configuration.
- Exercise what users actually get: a copy of the plugin in the plugin cache.
- Prove every gate fails for the intended reason.

## Considered options

- Isolated `HOME` and `CLAUDE_CONFIG_DIR` locally and in CI, plus injected-defect unit tests
- Static validation only
- End-to-end tests only in CI after publication

## Decision outcome

Chosen option: **isolated configuration tests plus injected-defect unit tests**. `scripts/test_install.py` runs three scenarios in throwaway configurations: the repository added as a directory marketplace (in place), a temporary marketplace using `git-subdir` sources over `file://` against a bare clone of HEAD (cache copy, as users receive it), and `--plugin-dir` session loading. Outside CI it fingerprints the real configuration before and after and fails if anything changed. `tests/` copies the repository, injects one defect per test, and asserts the gate fails for that defect only.

### Consequences

- Good, because install behavior is tested on every pull request with no risk to real configurations.
- Bad, because the cache-copy scenario tests committed HEAD only.

### Confirmation

CI runs `python3 scripts/check.py` (which includes the `tests` gate) and `python3 scripts/check.py test-install`. Verified approaches that do not work, and must not be retried, are recorded in `.claude/rules/testing/isolated-install.md`.

## Pros and cons of the options

### Isolated configuration

- Good, because it uses the real CLI against real install paths.
- Bad, because it depends on the CLI honoring `CLAUDE_CONFIG_DIR` (verified on 2.1.289).

### Static validation only

- Good, because it is fast.
- Bad, because loading and cache-copy failures go unnoticed.

## More information

Docs: [CLAUDE_CONFIG_DIR](https://code.claude.com/docs/en/env-vars), [Plugin sources](https://code.claude.com/docs/en/plugins/marketplace-reference#git-subdir-plugin-source). Procedure in [docs/testing.md](../../testing.md).
