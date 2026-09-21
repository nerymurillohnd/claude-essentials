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

## [0.1.2] - 2026-09-20

### Changed

- Skill description: rewritten from the skill's own files rather than from the
  previous description. It now opens with the instruction instead of a
  self-introduction, and states what the files actually guarantee: the
  script-only lifecycle (`assess`, `status`, `preflight`, `install`, `verify`,
  `uninstall`), coverage of Bash and PowerShell, the passive path that checks
  status once per session and offers the policy at most once, the backup that
  restores itself on failure, the Claude Cowork guard, and the rule that a
  denied command is fixed at its cause instead of reshaped to evade the check.
  No quoted trigger phrases, matching how Anthropic's own skills are written.

- Skill frontmatter now declares `when_to_use` beside `description`. Claude Code
  appends it to `description` in the skill listing, so the two are one
  1,536-character budget; splitting them keeps the instruction and the
  triggering conditions apart. Neither field contains a colon followed by a
  space, which a YAML parser reads as a nested mapping and rejects —
  `scripts/lib/skill-frontmatter.test.mjs` now parses every skill's frontmatter
  and enforces both rules, because `claude plugin validate --strict` does not.

- Eval table: the published scores are withdrawn until the suite is re-measured
  against the descriptions this version ships. The numbers dated 2026-09-19 were
  measured against the previous text, and a re-run performed while preparing this
  version pinned a different agent model, so neither set isolates the change.
  The cases themselves are unchanged.

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

[Unreleased]: https://github.com/nerymurillohnd/claude-essentials/compare/block-no-verify--v0.1.2...HEAD
[0.1.2]: https://github.com/nerymurillohnd/claude-essentials/compare/block-no-verify--v0.1.1...block-no-verify--v0.1.2
[0.1.1]: https://github.com/nerymurillohnd/claude-essentials/compare/block-no-verify--v0.1.0...block-no-verify--v0.1.1
[0.1.0]: https://github.com/nerymurillohnd/claude-essentials/tree/block-no-verify--v0.1.0
