---
paths:
  - "plugins/**/hooks/**"
  - "plugins/**/skills/**"
  - "plugins/**/agents/**"
  - "plugins/**/commands/**"
---

# Hooks and permissions (recent changes)

- Since 2.1.288, a failing PreToolUse or PermissionRequest hook blocks the call.
- Synchronous hooks that launched background processes hung until the 2.1.285 fix.
- Auto mode is the default permission mode for interactive sessions without configuration (2.1.284).
- With `allowManagedPermissionRulesOnly`, skills from third-party marketplaces lose their `allowed-tools` (2.1.284).
- Since 2.1.282 the `anthropic-skills` and `claude-ai` namespaces do not load; the `claude-ai` reservation was reverted in 2.1.283.
- Plugins must never depend on `allowed-tools` pre-approval.
- Review plugin instructions assuming they run under auto mode.
- Plugin hooks must be robust and fast, and must never spawn daemons.
- Avoid both `anthropic-skills` and `claude-ai` as names.
