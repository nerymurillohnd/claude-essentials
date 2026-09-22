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

## [0.2.0] - 2026-09-22

### Added

- The plugin now ships its hooks: installing it turns them on, in the scope you install it
  in, and updating the plugin updates them. After each edit Claude makes to a `.py`, `.pyw`
  or `.pyi` file, the hook applies Ruff's safe fixes (never `--unsafe-fixes`, and never
  removing a just-added import), formats the file, re-checks it, and hands any finding that
  is left to Claude. At the end of the turn it re-checks every Python file the session
  touched and keeps Claude working, up to 7 attempts, then tells you which files still fail.
  You see a one-line result after each edit and at the end.
- Before Claude adds a suppression comment (`noqa`, `ruff: noqa`, `fmt: off`/`skip`,
  `yapf: disable`, `isort: skip`, or `ruff check --add-noqa`/`--add-ignore`) or changes Ruff
  configuration (`ruff.toml`, `.ruff.toml`, `[tool.ruff]`), the hook asks you to confirm. It never denies.
- An `enabled` option (`/config`) turns the hooks off without removing the skill.

### Changed

- The hook runs the Ruff already installed in your project or globally, with Ruff's own
  configuration discovery (your nearest `ruff.toml`, `.ruff.toml` or `pyproject.toml`, then
  your user-level file, then Ruff's defaults). It never runs `uv` or `uvx` and never
  downloads anything. Without Ruff, or without `jq`, it tells you once per session how to
  install it and blocks nothing.
- The `ruff` skill was rewritten from the official Ruff and uv documentation: installing,
  command routes (with `--locked` and `--no-python-downloads` for uv), configuration
  discovery, rule selection, migration, editors, pre-commit and CI, and diagnosis.

### Removed

- The `ruff-hooks` skill, its `manage.sh` installer, its three configuration modes and the
  bundled `ruff.toml` profile: the plugin no longer writes any Ruff configuration.

## [0.1.1] - 2026-09-20

### Changed

- Skill descriptions (`ruff`, `ruff-hooks`): rewritten from the skills' own
  files rather than from the previous descriptions, and opening with the
  instruction instead of a self-introduction. `ruff-hooks` now names the four
  hook events and what each one does, the three configuration modes, the
  one-scope-at-a-time rule, that it fails closed and looks only at files Claude
  touched, and that once installed the gate denies Claude removing it.  `ruff`
  now states that it applies to every Python file Claude touches, not only when
  the user asks, and adds the command route (`uv run`, project venv, `PATH`,
  `uvx`), the unsafe-fix preview and the no-mass-reformat rule. No quoted
  trigger phrases.
- Version claims are no longer pinned: `This skill covers Ruff 0.16` becomes
  `Verified against Ruff 0.16.8 on 2026-09-19` plus an instruction to check
  `ruff --version` and the changelog, and the rule-selection heading, the
  manifest description and three README lines no longer name a release. A
  documented Ruff version stays where it is a fact about a specific release
  (the 413-rule default change, the 0.15 `select` trap) or a declared minimum.

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
  section gives — turns into an error. `ruff-hooks` separately needs 2.1.69,
  where it locates its scripts through `${CLAUDE_SKILL_DIR}`.
- README: Requirements gives the order the gate looks for Ruff
  (`RUFF_BIN`, then the nearest `.venv/bin/ruff` or `venv/bin/ruff`, then
  `PATH`); the Security table says what `uninstall` removes and keeps; the
  Limitations table lists every hook timeout, notes that a timed-out guard does
  not deny, and that Bash-edit coverage needs a Git repository and skips
  Git-ignored files; the maintainer checks run both suites by path under
  `/bin/bash` with `RQ_TEST_BASH`; the FAQ dates its comparison with Astral's
  skill.

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

[Unreleased]: https://github.com/nerymurillohnd/claude-essentials/compare/ruff-quality--v0.2.0...HEAD
[0.2.0]: https://github.com/nerymurillohnd/claude-essentials/compare/ruff-quality--v0.1.1...ruff-quality--v0.2.0
[0.1.1]: https://github.com/nerymurillohnd/claude-essentials/compare/ruff-quality--v0.1.0...ruff-quality--v0.1.1
[0.1.0]: https://github.com/nerymurillohnd/claude-essentials/tree/ruff-quality--v0.1.0
