---
paths:
  - "plugins/**/hooks/**"
  - "plugins/**/skills/**"
  - "plugins/**/agents/**"
  - "plugins/**/commands/**"
  - "plugins/**/.claude-plugin/plugin.json"
  - "scripts/repo.py"
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
