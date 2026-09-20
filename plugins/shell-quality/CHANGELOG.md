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

## [0.1.1] - 2026-09-20

### Changed

- Skill descriptions (`shell-lint`, `shell-hooks`): rewritten from the skills'
  own files rather than from the previous descriptions, and opening with the
  instruction instead of a self-introduction. `shell-hooks` now names the four
  hook events and what each one does, the three configuration modes, the
  one-scope-at-a-time rule, that it fails closed, skips zsh and looks only at
  scripts Claude touched, and that once installed the gate denies Claude
  removing it. `shell-lint` now states that it applies to every shell script
  Claude touches, not only when the user asks. No quoted trigger phrases.
- Version claims are no longer pinned: `This skill covers ShellCheck 0.11 and
  shfmt 3.14` becomes `Verified against ShellCheck 0.11.0 and shfmt 3.14.1 on
  2026-09-19` plus an instruction to check both `--version` outputs and the
  changelog, and the README no longer names releases in its summary. Declared
  minimums and facts about a specific release stay.

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

- Catalog: the marketplace entry now has category `development` and search
  `tags`, from `plugin.json` `metadata.marketplace`.
- README Requirements: Claude Code minimum is 2.1.222, since `plugin.json` now
  carries `metadata`, a recognized manifest field only from that version.
  Earlier versions load the plugin but treat the key as unrecognized, which
  `claude plugin validate --strict` — the command the README's Verification
  section gives — turns into an error.
- Keywords add `pre-commit` and `guardrails`, matching what the skills cover.
- README: the hooks section gives the `--max-blocks` range (1–7), the
  Limitations table lists every hook timeout (30 s baseline and guard, 60 s
  post, 120 s Stop), the CAUTION alert says the five hook groups cover four
  events, the Security table names the XDG ShellCheck rc path, and the
  maintainer checks run both suites by path under `/bin/bash` with the
  plugin's own `SQ_TEST_BASH`.

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

[Unreleased]: https://github.com/nerymurillohnd/claude-essentials/compare/shell-quality--v0.1.1...HEAD
[0.1.1]: https://github.com/nerymurillohnd/claude-essentials/tree/shell-quality--v0.1.1
[0.1.0]: https://github.com/nerymurillohnd/claude-essentials/tree/shell-quality--v0.1.0
