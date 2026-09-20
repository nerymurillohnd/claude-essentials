# Changelog

All notable changes to block-no-verify are documented in this file.

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

### Changed

- Catalog: the marketplace entry now has category `security` and search
  `tags`, from `plugin.json` `metadata.marketplace`.
- README Requirements: Claude Code minimum is 2.1.222, since `plugin.json` now
  carries `metadata`, a recognized manifest field only from that version.
  Earlier versions load the plugin but treat the key as unrecognized, which
  `claude plugin validate --strict` — the command the README's Verification
  section gives — turns into an error.
- The plugin description now leads with the outcome and states that only
  commands Claude runs are checked, never your own terminal or CI.
- README: the eval table credits the run it reports (Claude Code 2.1.278,
  skill 0.1.1), the hooks section lists the installed `PreToolUse` group in
  the template's event table, and the Security table gives the exact backup
  folders and what the read-only `status` check reads.

## [0.1.1] - 2026-09-18

### Fixed

- Preflight now checks Git 2.18 or later, the minimum the README lists, instead
  of failing later during assessment.
- `assess` lists installed plugin hooks relative to `CLAUDE_CONFIG_DIR` when it
  is set, instead of printing full paths.
- Without `jq`, the handler no longer denies unrelated commands whose working
  directory or transcript path contains "git" (for example `ls` in
  `~/github/app`); it now checks only the command itself.

The handler's policy is unchanged; reinstalling an installed 0.1.0 policy is
optional (`status` reports it as an older version).

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

[Unreleased]: https://github.com/nerymurillohnd/claude-essentials/compare/block-no-verify--v0.1.1...HEAD
[0.1.1]: https://github.com/nerymurillohnd/claude-essentials/compare/block-no-verify--v0.1.0...block-no-verify--v0.1.1
[0.1.0]: https://github.com/nerymurillohnd/claude-essentials/tree/block-no-verify--v0.1.0
