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

## [0.3.0] - 2026-09-24

### Changed

- **Breaking:** the skill is rewritten as a research contract. Every task starts with one
  command, `ccdocs.py research "<phrase>" ...`, instead of the model choosing which pages to
  read. It routes the phrases through `references/areas.md`, reads every page of the areas they
  name, keeps the sections whose headings use each area's vocabulary, follows every hyperlink in
  those sections one hop, checks six months of release notes, and writes a folder (`MAP.md`,
  `changelog.md`, one file per page and per section) under `${CLAUDE_PLUGIN_DATA}/research`.
- **Breaking:** answers end with a four-part structure (Answer, Evidence, Changelog, Not
  verified) and one `Verified <date> against Claude Code v<version>` line. The `TOOLS USED`,
  `ACTIVATION` and `NOT FOUND` block is gone.
- Scope widened from Claude Code to Cowork and the Claude apps (Help Center) and the Claude API
  (Platform docs), each with its own index and release notes.
- Python requirement lowered from 3.14 to **3.12**. An older `python3` stops with one line
  naming the version it found.
- Skill frontmatter rewritten: `description` states what the skill does and that it takes
  precedence over the built-in `claude-code-guide` agent; `when_to_use` carries the triggers.
- An invalid `CCDOCS_CACHE_TTL`, `CCDOCS_CORPUS_TTL` or `CCDOCS_ANCHOR_TTL` now stops the
  command with a one-line error instead of falling back to the default.

### Added

- `ccdocs.py` commands: `research`, `show` (reads a research folder and nothing outside it),
  `url` (turns a docs MCP path, a bare `/en/` link or an old alias into the canonical, verified
  URL), `quote` (verbatim sentence with its section URL; fails when the text is not on the live
  page), `inventory`, `catalog`, `related`, `dossier` and `links`.
- Section anchors come from the rendered page, including the old ids a renamed section keeps
  and ids placed inside a paragraph; an anchor that can't be verified is dropped and reported.
- References: `areas.md` (29 areas with triggers, vocabulary, official navigation groups and
  pinned pages), `area-pages.md` (every page of every area), `docs-catalog.md` (all index pages
  with their link neighbours) and `url-aliases.md` (old URLs and the page each one serves).
- `selfcheck --live` checks section names against the live pages, and fails when an index page
  or a navigation group belongs to no area.
- `CCDOCS_ANCHOR_TTL` sets how long the rendered-page anchors stay cached.

### Removed

- The skill's `allowed-tools` no longer grants `curl` or `WebFetch`. Every page is read through
  `ccdocs.py`, which downloads the raw markdown whole.

### Fixed

- Sections written as HTML headings (`<h2 id="...">`) are found by `page`, `outline` and
  `research`; they were invisible before.
- A Help Center article whose URL slug changed is resolved by its article number.

### Security

- `raw` and every fetch refuse any URL that is not `https://`; `file://` URLs are rejected. Any
  `https` host is still accepted.
- Cache entries are created with the default file permissions of your system instead of being
  readable by their owner only.
- `research` keeps the last 10 run folders in its output directory and deletes older ones.

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
- An empty `XDG_CACHE_HOME` counts as unset, so the cache no longer lands in `./ccdocs` in the
  working directory. New cache entries are readable by their owner only.
- An old `python3` (3.7 or later) prints the version requirement instead of a SyntaxError:
  the script no longer uses syntax those versions cannot parse.
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

[Unreleased]: https://github.com/nerymurillohnd/claude-essentials/compare/agent-self-knowledge--v0.3.0...HEAD
[0.3.0]: https://github.com/nerymurillohnd/claude-essentials/compare/agent-self-knowledge--v0.2.0...agent-self-knowledge--v0.3.0
[0.2.0]: https://github.com/nerymurillohnd/claude-essentials/compare/agent-self-knowledge--v0.1.0...agent-self-knowledge--v0.2.0
[0.1.0]: https://github.com/nerymurillohnd/claude-essentials/tree/agent-self-knowledge--v0.1.0
