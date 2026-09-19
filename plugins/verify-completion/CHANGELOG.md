# Changelog

All notable changes to verify-completion are documented in this file.

This changelog follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and [Semantic Versioning](https://semver.org/spec/v2.0.0.html). Use ISO 8601
dates (`YYYY-MM-DD`) and keep entries concise, user-facing, and actionable.

## [Unreleased]

<!--
Every change to runtime files (skills, agents, commands, hooks, MCP/LSP config,
plugin.json components) bumps "version" in .claude-plugin/plugin.json
and adds a "## [X.Y.Z] - YYYY-MM-DD" section below; CI enforces both and tags
{plugin-name}--v{version} on merge. See docs/contributing/versioning.md.
-->

## [0.1.0] - 2026-09-19

### Added

- `verify-completion` skill: a six-gate protocol (adversarial review, outcome,
  counterpart, distrust the green, both directions, evidence) that ends with a
  checkable Verification record, and never counts as permission to commit,
  push, or deploy.
- Coherence audit reference: reconstructing the change's intent, auditing the
  diff for noise, half-applied patterns, silent contract changes, and drift,
  and checking that every layer depending on what moved (tests, types,
  validators, docs, config, CI, generated files) moved too.
- Depth audit reference: reading the tests (assertions that restate the
  implementation, missing negative and failure cases), deconstructing mocks
  that can't fail or accept impossible states, validating validators, and an
  edge-case matrix whose rows are chosen by what the change touches, each
  skipped row with a reason.
- `completion-verifier` agent: an independent, read-only second opinion that
  gets the requirement and where to look, never the author's conclusions, and
  preloads the skill so the gates live in one place. The
  skill scales it to the change: none for a small change, one verifier for
  substantial work, and three in parallel (`coherence`, `depth`, `edges`) for
  a change that spans layers.
- `deep-verify` workflow, opt-in for large changes: three read-only verifiers in
  parallel, then independent agents try to refute each problem and overturn
  each `PASS`, returning only what survives.
- Stop hook: when a reply presents work as finished (English or Spanish) after
  real work, it asks for a valid Verification record, keeps asking while
  Claude keeps working, and otherwise warns you that the claim is unverified.
  A reply that calls the work done while its own verdict is `NOT VERIFIED` is
  rejected as a contradiction.
- `enforcement` option (`enforce`, `warn`, `off`) in `/config`.
- 122-case hook test suite, run on bash 3.2 and 5.x with jq 1.6, 1.7.1, and 1.8.2; a typical reply is checked
  in about 100 ms, and 250 KB replies built to be slow in under 2 seconds.

[Unreleased]: https://github.com/nerymurillohnd/claude-essentials/compare/verify-completion--v0.1.0...HEAD
[0.1.0]: https://github.com/nerymurillohnd/claude-essentials/tree/verify-completion--v0.1.0
