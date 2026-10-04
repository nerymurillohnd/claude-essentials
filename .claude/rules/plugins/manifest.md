---
paths:
  - "plugins/**"
  - "scripts/new_plugin.py"
  - "scripts/check_repo.py"
---

# Plugin manifest

- Forbidden prefixes: `claude-`, `anthropic-`, `anthropics-` and `cc-plugin-`; also the exact names `claude`, `anthropic`, `anthropics`, `claude-code` and `claude-mods`.
- Having `claude` or `anthropic` as a standalone word in the name gives a warning, which is a failure under `--strict`.
- The `version` in `plugin.json` wins over the one in the catalog entry.
- If the entry has the same version it passes; if it has a different one, `validate` warns and `claude plugin tag` refuses to tag.
- `commands`, `agents`, `outputStyles` and `workflows` replace their default folder, `skills` adds to its own, and `hooks`, `mcpServers` and `lspServers` merge.
- The components `workflows/`, `themes/`, `monitors/monitors.json` and `settings.json` exist; the latter only accepts `agent` and `subagentStatusLine`.
- claude.ai and Cowork reject plugins with a `bin/` at the root.
- A `CLAUDE.md` at the plugin root is not loaded and `validate` warns.
- `${CLAUDE_PLUGIN_ROOT}` changes with every update and `${CLAUDE_PLUGIN_DATA}` persists unless the plugin is uninstalled without `--keep-data`.
- These variables do not reach the Bash tool's environment: they are substituted inline in the Markdown.
- `${user_config.KEY}` is rejected in shell hooks, monitors and `headersHelper`; there you use exec form or `CLAUDE_PLUGIN_OPTION_<KEY>`.
- Symlinks to elsewhere in the marketplace are dereferenced and those pointing outside it are skipped.
