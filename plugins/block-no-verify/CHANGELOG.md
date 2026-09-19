# Changelog

All notable changes to block-no-verify are documented in this file.

This changelog follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and [Semantic Versioning](https://semver.org/spec/v2.0.0.html). Use ISO 8601
dates (`YYYY-MM-DD`).

## [Unreleased]

<!--
Every change to runtime files (skills, agents, commands, hooks, MCP/LSP config,
plugin.json components) bumps "version" in .claude-plugin/plugin.json
and adds a "## [X.Y.Z] - YYYY-MM-DD" section below; CI enforces both and tags
{plugin-name}--v{version} on merge. See docs/contributing/versioning.md.
-->

## [0.1.0] - 2026-09-18

### Added

- `block-no-verify` skill: assess a repository, recommend a scope, and install
  (only after explicit approval), verify, report, and uninstall a `PreToolUse`
  policy that denies Git verification and signing bypasses.
- Bash 3.2-compatible handler with a quote-aware POSIX and PowerShell
  tokenizer, nested-command inspection, and fail-closed deny (JSON plus exit 2).
- `manage.sh`: deterministic, idempotent, backup-first installer with
  automatic rollback on failed verification.
- 326-case behavioral test suite, run against the installed copy on bash 3.2
  and 5.x; typical commands are checked in about 30 ms, 50 KB inputs in about
  200 ms, with a metered parser so no input can outlast the hook timeout.
