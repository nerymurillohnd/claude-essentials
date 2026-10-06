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
- Observed or read on Claude Code 2.1.290 on 2026-10-05/06 while building the `svelte-development` hook:
  - A hook's `if` takes one permission rule. `if: Edit(*.svelte)` did not fire for `Write` calls in a real session, although permission `Edit(...)` rules cover every file-editing tool: give `Write` and `Edit` their own handlers. `Write(*.svelte*)` also matched files under `.svelte-kit/` and names such as `x.svelte-check`; list each extension.
  - On `PostToolUse`, an `mcp_tool` hook's output is read like command stdout at exit 0, which goes to the debug log only; Claude sees `hookSpecificOutput.additionalContext`, so an MCP tool whose output is not hook JSON never reaches Claude through a hook.
  - A command hook's text goes inside `echo '...'`: an apostrophe in it ends the quote, `sh` exits 2 with a syntax error, and on `PostToolUse` Claude receives that stderr instead of the note (caught in the PR #17 review on 2026-10-06). Keep apostrophes out of hook texts and run each command with `sh -c` before shipping.
  - Read on 2026-10-06 (hooks and env-vars docs): hook commands get `CLAUDE_CODE_SESSION_ID`, so per-session state needs no stdin parsing; a `Stop` hook's `hookSpecificOutput.additionalContext` keeps Claude working and is labelled `Stop hook feedback` (for guidance, while `decision: "block"` shows as a hook error), both under `stop_hook_active` and the 8-continuation cap; `PreToolUse` accepts `additionalContext`; `SessionStart` sources are `startup`, `resume`, `clear`, `compact` and `fork` (a matcher copied from the older four-value list misses forked sessions; omit it to cover all); `async` hooks cannot block or gate; `type: "agent"` hooks are experimental and `type: "prompt"` hooks call a model on every firing. A context note that repeats on every tool call costs tokens each time: prefer a silent marker plus one `Stop` note.
  - Plugin agents ignore the `hooks`, `mcpServers` and `permissionMode` frontmatter fields (sub-agents docs); ship hooks in `hooks/hooks.json`.
  - A skill's `!` command that fails, or that outside auto mode has no allow rule, aborts the whole skill invocation (skills docs); since plugins never depend on `allowed-tools`, plugin skills do not use `!` injection.
