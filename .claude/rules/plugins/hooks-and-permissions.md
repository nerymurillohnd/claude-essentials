---
paths:
  - "plugins/**/hooks/**"
  - "plugins/**/skills/**"
  - "plugins/**/agents/**"
  - "plugins/**/commands/**"
  - "plugins/**/.claude-plugin/plugin.json"
  - "scripts/repo.py"
  - "scripts/new_plugin.py"
---

# Hooks and permissions (recent changes)

- Since 2.1.288, a PreToolUse or PermissionRequest hook that Claude Code cannot match, or whose tool input cannot be serialized to JSON, blocks the call instead of being skipped. A hook that runs and fails (any exit code other than 2, invalid JSON) is a non-blocking error and the call proceeds; only exit 2 or a blocking decision blocks.
- Synchronous hooks that launched background processes hung until the 2.1.285 fix.
- Auto mode is the default permission mode for interactive sessions without configuration (2.1.284).
- With `allowManagedPermissionRulesOnly`, skills from third-party marketplaces lose their `allowed-tools` (2.1.284).
- Since 2.1.282, skill folders, command files and workflow commands in the `anthropic-skills` namespace do not load (a plugin so named still loads but yields name ties to synced skills); the same restriction on `claude-ai` was reverted in 2.1.283.
- Plugins must never depend on `allowed-tools` pre-approval.
- Review plugin instructions assuming they run under auto mode.
- Plugin hooks must be robust and fast, and must never spawn daemons.
- Avoid both `anthropic-skills` and `claude-ai` as names.
- The `init --with hooks` scaffold runs `bun "${CLAUDE_PLUGIN_ROOT}/hooks-handlers/on-session-start.ts"`; never ship it unchanged, because hooks may only use interpreters the plugin declares as requirements, and a plugin script is never run with an interpreter in front.
- A plugin script starts with `#!/usr/bin/env <interpreter>` (no version such as `python3.12`, no absolute interpreter path, no options), is mode 755 in git, and hooks, monitors, MCP and LSP servers run it by path: `"${CLAUDE_PLUGIN_ROOT}/scripts/x.sh"`. The docs run plugin scripts by path and require them to be executable (plugins/components#hooks, hooks-guide); installs keep the bit since 2.1.86. A sourced or imported file has neither shebang nor mode 755. The `repo` gate checks all of it (ADR unpinned-tooling-and-shebang-interpreters).
