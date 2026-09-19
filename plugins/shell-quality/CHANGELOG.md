# Changelog

All notable changes to shell-quality are documented in this file.

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

- `shell-lint` skill: the ShellCheck 0.11 and shfmt 3.14 workflow for every
  script change (format, then check), how both tools find their
  configuration, correct fixes for the common SC codes, directive placement,
  macOS Bash 3.2 pitfalls ShellCheck does not catch, migration from
  `bash -n`, beautysh, and checkbashisms, and pre-commit, CI, and editor setup.
- `shell-hooks` skill: assesses the project, shows the exact configuration of
  each mode (recommended, own, defaults) with baseline counts, and, only after
  the user chooses a scope and a mode, installs the shell-quality gate through
  a backup-first, idempotent `manage.sh`.
- The gate: `UserPromptSubmit` baseline, `PreToolUse` guard (denies
  `# shellcheck disable`/`source=/dev/null` and changes to rc files, the shfmt
  keys of `.editorconfig`, or the gate), `PostToolUse` shfmt and ShellCheck on
  every edited `.sh`, `.bash`, `.bats`, or shebang script (including scripts
  written through Bash when Claude Code reports them), and a `Stop` gate with a
  configurable block limit. Fails closed with exit 2.
- Recommended profile: a `.shellcheckrc` with ten named optional checks and a
  `[[shell]]` EditorConfig block in Google style.
- Behavioral suites: 82 gate cases and 44 installer cases, on bash 3.2 and 5.x.

<!--
COMPARE LINKS (ADR-0003 tags are "{plugin-name}--v{version}"). Keep one link per
heading: [Unreleased] compares the latest tag to HEAD; each version compares the
previous tag to its own; the first version links to its tag.
-->

[Unreleased]: https://github.com/nerymurillohnd/claude-essentials/compare/shell-quality--v0.1.0...HEAD
[0.1.0]: https://github.com/nerymurillohnd/claude-essentials/tree/shell-quality--v0.1.0
