# Changelog

All notable changes to agent-self-knowledge are documented in this file.

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

### Changed

- **Requires Python 3.14 or later** as `python3`. `ccdocs.py` checks the version when it
  starts and stops with a message naming the version it found, instead of failing midway
  on an older interpreter. The Xcode Command Line Tools' Python (3.9) no longer suffices.
- `ccdocs.py` now passes the marketplace's Ruff and basedpyright gates, which cover every
  Python file a plugin ships. Its commands print the same output as before.

### Fixed

- A cache directory that cannot be written no longer stops retrieval: the page is still
  returned and only caching is skipped, as the README already promised.
- `page --nth` refuses 0 and negative numbers with a usage error; they used to pick a heading
  counted from the end.
- An invalid `CCDOCS_CACHE_TTL` or `CCDOCS_CORPUS_TTL` is named and replaced by its default
  instead of stopping every command with a traceback.
- `version` reports a registry answer that is not JSON as an error instead of a traceback.
- `ccdocs.py` is now tracked as executable (`100755`), so its
  `#!/usr/bin/env python3` shebang works when the script is run by path. The
  skill still calls it as `python3 …/ccdocs.py`, so retrieval behaves exactly
  as before.

## [0.1.0] - 2026-09-20

### Added

- `claude-code-docs` skill: retrieves Claude Code facts from the live official
  documentation, the upstream changelog and the npm registry instead of from
  memory, and answers with the exact sentence quoted verbatim, the source URL,
  and the version it verified against.
- Skill frontmatter declares both `description` and `when_to_use` — 1,082 of the
  1,536 characters Claude Code allows for the two together — and leaves model
  invocation enabled, so Claude can load the skill without being asked for it
  by name.
- `ccdocs.py`, a stdlib-only Python retrieval script (Python 3.7+, no packages,
  no `uv`) with ten commands: `find` and `grep` to locate a fact across every
  heading or the full corpus, `index` and `outline` to navigate, `page` to read
  one section instead of a 430 KB file, `changelog` and `whatsnew` for the
  version dimension, `version` to compare the user's build against npm, `raw`
  to fetch an arbitrary URL, and `selfcheck` to validate every slug and quoted
  section name the skill cites.
- Negative-claim protocol: an assertion that a feature does not exist requires
  three misses — `find`, `grep` over the whole corpus, and `changelog --grep` —
  and is then reported as a bounded fact with its date and version, never as a
  flat denial.
- Report block closing every answer: `TOOLS USED`, `ACTIVATION` (whether the
  skill loaded on its own or was invoked by name), and `NOT FOUND`, so the
  retrieval can be audited instead of trusted.
- Conflict handling: when the documentation and the changelog disagree, both
  are quoted and the answer states which one governs and why.
- `references/sources.md` (endpoint catalog, authority order, anchor rules,
  localized docs, legacy redirects) and `references/topic-routing.md` (per-topic
  key sections, adjacent pages, and what is volatile in each area).

- Limitation stated in the README: the skill reads the published documentation,
  the changelog and the npm registry, and Claude Code ships settings keys in
  none of them. Verified on 2026-09-20 with `worktree.location`, which the
  2.1.278 settings schema defines and the documentation corpus does not carry,
  so a not-found result for a settings key means not documented, not absent.
  Tracked as DEBT-0023.

### Security

- The skill's `allowed-tools` grants `python3` on its own script without a
  permission prompt, and `raw` accepts any URL with no scheme or host
  validation. Publishing with this behavior unchanged is a risk the maintainer
  accepted on 2026-09-20; the vector, the evidence, and the closing condition
  are recorded in `docs/maintenance/pending-debt.md` and in the design spec.

[Unreleased]: https://github.com/nerymurillohnd/claude-essentials/compare/agent-self-knowledge--v0.2.0...HEAD
[0.2.0]: https://github.com/nerymurillohnd/claude-essentials/compare/agent-self-knowledge--v0.1.0...agent-self-knowledge--v0.2.0
[0.1.0]: https://github.com/nerymurillohnd/claude-essentials/tree/agent-self-knowledge--v0.1.0
