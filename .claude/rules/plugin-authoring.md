---
paths:
  - "plugins/**"
  - "templates/**"
---

# Plugin authoring rules

These load whenever you read or edit a plugin or a template. The full guidance is in docs/authoring.md, docs/quality-bar.md and docs/security-review.md: read the matching one before non-trivial work.

- Plugins are for third parties. Describe every capability from the point of view of the user who installs it. Never install, enable or symlink a plugin into the maintainer's real Claude Code configuration; `uv run scripts/check.py test-install` uses throwaway configurations.
- Create plugins only with `uv run scripts/new_plugin.py`; never create a plugin directory by hand.
- Everything a plugin needs stays inside `plugins/<name>/`. Use `${CLAUDE_PLUGIN_ROOT}` for bundled files and `${CLAUDE_PLUGIN_DATA}` for state; no `../`, absolute or home paths, user or machine names, personal emails or secrets.
- `version` lives only in `plugin.json` and changes only through `scripts/release.py`. Feature and fix changes add a note under `## [Unreleased]` in the plugin's `CHANGELOG.md`.
- Never edit content between `BEGIN GENERATED` and `END GENERATED`; change the manifest or files and run `uv run scripts/sync_readmes.py`.
- Hooks, MCP and LSP servers, `bin/`, monitors and mods need a README Permissions section and pass docs/security-review.md. Mods need `metadata.minClaudeCodeVersion` >= 2.1.287 and `claude plugin test` tests.
- Before relying on any Claude Code behavior, re-read the official page and the changelog entries newer than the version recorded in CLAUDE.md; Claude Code specifics come only from official sources.
- Finish with `claude plugin validate plugins/<name> --strict` and `uv run scripts/check.py`.
