# Changelog

All notable changes to repo-hygiene are documented in this file.

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

## [0.1.0] - 2026-09-22

### Added

- `routine` skill: audits a Git repository and its hosting provider across 31 areas at routine
  depth. Claude reads without asking, reports once with detailed recommendations, and runs only
  the item IDs the user approves.
- `deep` skill, invoked only by the user (`/repo-hygiene:deep`), with five phases:
  - `audit`: full-depth forensics and adjudication;
  - `plan`: a plan package with an acceptance contract and operation IDs;
  - `execute`: approved operations with a restore-tested backup, review-thread closure and
    defect fixes;
  - `resume`: picks up an open program where it stopped;
  - `certify`: checks the acceptance contract.
- Read-only agents `thread-adjudicator`, `candidate-classifier` and `certificate-verifier` for
  large volumes of review threads, candidates and final checks.
- A bundled Git reference: the audit contract, report template, provider recipes, adjudication
  methods, program references, area checklists, per-command pages with a safety class per
  option, and a routing map of every git-scm reference page and Pro Git section with its
  official URL.
- Evals with a fixture that plants findings in every Git area.
