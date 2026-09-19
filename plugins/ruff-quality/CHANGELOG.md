# Changelog

All notable changes to ruff-quality are documented in this file.

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

- `ruff` skill: the Ruff 0.16 workflow for every Python change (safe fixes,
  format, check), configuration discovery, rule selection after the 413-rule
  default, formatter-conflicting rules, suppressions Claude must not add,
  migration from Black, isort, Flake8, Pylint, pyupgrade, and a Ruff 0.15
  setup, and pre-commit, CI, and language-server setup.
- `ruff-hooks` skill: assesses the project, shows the exact configuration of
  each mode (recommended, own, defaults) with baseline finding counts, and,
  only after the user chooses a scope and a mode, installs the ruff-quality
  gate through a backup-first, idempotent `manage.sh`.
- The gate: `UserPromptSubmit` baseline, `PreToolUse` guard (denies
  suppression comments and changes to the Ruff configuration or the gate),
  `PostToolUse` fix/format/lint of every edited `.py`, `.pyi`, and `.ipynb`
  (including files written through Bash when Claude Code reports them), and a
  `Stop` gate with a configurable block limit. Fails closed with exit 2.
- Recommended profile: Ruff's defaults plus 36 rule families (701 rules), no
  formatter conflicts.
- Behavioral suites: 99 gate cases and 41 installer cases, on bash 3.2 and 5.x.

<!--
COMPARE LINKS (ADR-0003 tags are "{plugin-name}--v{version}"). Keep one link per
heading: [Unreleased] compares the latest tag to HEAD; each version compares the
previous tag to its own; the first version links to its tag.
-->

[Unreleased]: https://github.com/nerymurillohnd/claude-essentials/compare/ruff-quality--v0.1.0...HEAD
[0.1.0]: https://github.com/nerymurillohnd/claude-essentials/tree/ruff-quality--v0.1.0
