# Changelog

All notable changes to evidence-reader are documented in this file.

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

- `evidence-standard` skill: the shared reporting contract — a receipt for every
  claim, "unknown" instead of guesses, full sequential coverage, file contents
  treated as data (prompt-injection handling), privacy by default, and a fixed
  report template with a completeness checklist.
- `document-reading` skill with stdlib extractors for Word (paragraphs under their
  heading path, tables, tracked changes, comments, headers and footers) and
  PowerPoint (slides in deck order, hidden and orphan slides, speaker notes,
  charts, SmartArt, comments), and a poppler-based PDF probe with page and line
  locators and scanned-page detection.
- `tabular-data` skill with a stdlib workbook auditor (every sheet including
  hidden ones, formulas beside cached values, missing cached values, error
  cells, formula outliers by column, external links, macros, merged ranges,
  labelled recomputation of simple aggregates), a streaming CSV/TSV profiler
  with exact decimal sums, and a JSON Pointer / XML path locator.
- `image-analysis` skill with an image tool that identifies formats, converts
  HEIC and every TIFF page for viewing, crops regions for fine print, reads
  metadata as a claim while withholding GPS and serial numbers, and finds exact
  and near-duplicate images.
- Three read-only agents — `document-reader`, `tabular-auditor`,
  `image-inspector` — each preloading the contract and its format skill, with
  no file-writing tools and no ability to spawn further agents.
- `SubagentStop` report gate scoped to the three agents, with `block`, `warn`
  and `off` modes and a two-retry cap; fails open. A `PreToolUse` hook on
  `SubagentHandback` keeps a copy of a report handed back that way, so the gate
  checks the report the caller actually receives.
- `check-requirements.sh`, which reports the available tools as a `TIERS` line
  and never installs anything.
- Untrusted input hardening: images reach ImageMagick only with the decoder their
  bytes prove (never an SVG or script coder), converted pages and crops go to a new
  private folder per run, and OOXML and XML parts that declare a DTD or entity are
  refused.
- Every extractor needs Python 3.14 as `python3`; an older interpreter gets a
  one-line message naming the version it found and exit code 5, never a traceback.

[Unreleased]: https://github.com/nerymurillohnd/claude-essentials/compare/evidence-reader--v0.1.0...HEAD
[0.1.0]: https://github.com/nerymurillohnd/claude-essentials/tree/evidence-reader--v0.1.0
