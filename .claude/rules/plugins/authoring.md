---
paths:
  - "plugins/**"
  - "templates/**"
---

# Plugin authoring rules

These load whenever you read or edit a plugin or a template. The full guidance is in docs/authoring.md, docs/quality-bar.md and docs/security-review.md: read the matching one before non-trivial work.

- Plugins are for third parties (CLAUDE.md, Non-negotiable rules); `scripts/check.py test-install` uses throwaway configurations.
- Create plugins only with `scripts/new_plugin.py`; never create a plugin directory by hand.
- A new skill, agent, hook or command goes either into a new plugin (`new_plugin.py --with …`) or into the existing plugin it belongs to; never place one outside `plugins/<name>/`.
- Everything a plugin needs stays inside `plugins/<name>/`. Use `${CLAUDE_PLUGIN_ROOT}` for bundled files and `${CLAUDE_PLUGIN_DATA}` for state; no `../`, absolute or home paths, user or machine names, personal emails or secrets.
- `version` lives only in `plugin.json` and changes only through `scripts/bump_version.py`. Every change inside the plugin ships with its release in the same pull request: write the note under `## [Unreleased]`, then run the bump (`docs/releasing.md`).
- Every plugin ships its own `LICENSE` from `templates/license/LICENSE`, with the year and its author as holder: the plugin is copied without the repository, and MIT requires the notice in every copy. The `repo` gate checks it; `new_plugin.py` writes it.
- Never edit content between `BEGIN GENERATED` and `END GENERATED`; change the manifest or files and run `scripts/sync_readmes.py`.
- Hooks, MCP and LSP servers, `bin/`, monitors and mods need a README Permissions section and pass docs/security-review.md. Mods need `metadata.minClaudeCodeVersion` >= 2.1.287 and `claude plugin test` tests.
- Before relying on any Claude Code behavior, re-read the official page and the changelog entries newer than the version in `.claude/rules/claude-code-version.md`; Claude Code specifics come only from official sources.
- Finish with `claude plugin validate plugins/<name> --strict` and `scripts/check.py`.
