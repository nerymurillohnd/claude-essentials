# Changelog

Changes to the Claude Essentials catalog: plugins added, deprecated, removed or renamed, and changes to how the catalog is distributed. Each plugin keeps its own versioned changelog in `plugins/<name>/CHANGELOG.md`.

The catalog has no version: users always receive the latest catalog, and only plugins are versioned ([Semantic Versioning](https://semver.org/spec/v2.0.0.html)). Entries are grouped by date (UTC), newest first, using the change types of [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## 2026-10-05

### Added

- `project-automation`: Audits a repository and builds evidence-backed Claude Code automation for it: skills, subagents, hooks, rules and settings, each verified working before it is handed over.

### Removed

- `hello-example`, the example plugin: `project-automation` now exercises the whole pipeline. The catalog's `renames` entry maps it to `null`, so users who installed it see `Removed from the "claude-essentials" marketplace` instead of a not-found error. Uninstall it with `claude plugin uninstall hello-example@claude-essentials`.

## 2026-10-03

### Added

- Marketplace catalog `claude-essentials` with its category taxonomy and the non-affiliation disclaimer.
- `hello-example`, an example plugin that proves the pipeline end to end and will be removed once real plugins cover it.
- Repository gates, the plugin scaffold, the version bump script, the isolated install test, CI workflows, labels and contribution templates.
