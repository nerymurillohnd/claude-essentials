# Surfaces to decide

For each row: **used** (with the exact fields and values) or **rejected** (why).
Verify every field against the live docs listed in CLAUDE.md before relying on it.

## Plugin

- Layout: `.claude-plugin/plugin.json` only; everything else at the plugin root
- `plugin.json`: name, version, description, author, homepage, repository, license, keywords, component paths, `userConfig` (type, title, required, sensitive, options)
- Distribution: copied to the plugin cache, `${CLAUDE_PLUGIN_ROOT}` changes per version, `${CLAUDE_PLUGIN_DATA}` persists
- Kind (ADR-0001): bundle, skill-only, agent-only
- `settings.json` (only `agent`, `subagentStatusLine`)
- `bin/`: forbidden here (`.github/pull_request_template.md`), because claude.ai organization sync rejects any plugin that has one (plugin-marketplaces); ship executables under `scripts/` and call them by path
- `dependencies` on other plugins (semver), `defaultEnabled`, `channels`
- Node dependencies: a `package.json` at the root is installed into the cache; others go to `${CLAUDE_PLUGIN_DATA}` from a `SessionStart` hook
- `outputStyles`, `workflows`, `experimental.themes`, `experimental.monitors`
- `metadata` (free-form, not read by Claude Code): catalog fields such as category and tags
- `CLAUDE.md` and `.claude/rules/` are not documented plugin components (plugins-reference, 2026-09-19): standing instructions go in skills, agents, or output styles; re-check the docs before assuming otherwise

## Marketplace entry (`.claude-plugin/marketplace.json`)

- Generated here; entry fields override `plugin.json` display fields (displayName, description, author, homepage, repository, license, keywords)
- Entry-only: `category`, `tags`, `strict`, `relevance` (admin-allowlisted marketplaces only), `defaultEnabled`
- Relative-path sources let Claude Code read `plugin.json` before install

## Skills

- Count and boundaries; single `SKILL.md` at the root vs `skills/`
- Frontmatter: name, description, when_to_use, argument-hint, arguments, disable-model-invocation, user-invocable, allowed-tools, disallowed-tools, model, effort, context: fork, agent, background, hooks (+ `once`), paths, shell, metadata, license, compatibility
- Substitutions: `$ARGUMENTS`, `$N`, `$name`, `${CLAUDE_SKILL_DIR}`, `${CLAUDE_PROJECT_DIR}`, `${CLAUDE_PLUGIN_ROOT}`, `${CLAUDE_PLUGIN_DATA}`, `${CLAUDE_SESSION_ID}`
- `!` dynamic context injection (non-zero exit aborts; `|| true`)
- Description budget (1,536 chars; listing budget), progressive disclosure, references one level deep, TOC over 100 lines
- Skills preloaded into subagents; skills shared by several agents

## Agents and orchestration

- Subagent frontmatter: name, description, tools, disallowedTools, model, effort, skills, color; ignored in plugins: hooks, mcpServers, permissionMode
- Foreground vs background; subagents lose the LSP tool
- Agent teams, orchestrator, auditor, writer, verifier roles
- Workflows (`plugins/*/workflows/*.js`, dynamic dialect)

## Hooks

- Events: SessionStart, Setup, UserPromptSubmit, UserPromptExpansion, PreToolUse, PermissionRequest, PermissionDenied, PostToolUse, PostToolUseFailure, PostToolBatch, Stop, SubagentStart, SubagentStop, TaskCreated, TaskCompleted, TeammateIdle, Notification, MessageDisplay, InstructionsLoaded, ConfigChange, CwdChanged, DirectoryAdded, FileChanged, WorktreeCreate, WorktreeRemove, PreCompact, PostCompact, PreModelSwitch, PostModelSwitch, Elicitation, ElicitationResult, StopFailure, SessionEnd
- Where: plugin `hooks/hooks.json` (always on) vs skill frontmatter (session) vs settings installed on request (scoped)
- Matchers (exact, list, regex), `if` (one permission rule, tool events only)
- Handler types: command, http, mcp_tool, prompt, agent; exec form (`args`) vs shell form (Windows)
- Fields: timeout (defaults per event), statusMessage, async, asyncRewake, shell, once
- Input: common fields, per-event fields, Windows native paths
- Output: exit 0/2/other per event, JSON (one object), decision/reason, hookSpecificOutput, additionalContext (factual, not imperative), systemMessage, continue/stopReason, updatedInput, updatedToolOutput, 10,000-char cap
- Fail open vs fail closed per event; a missing script (127) disables silently
- Stop loop cap (8), `stop_hook_active`, subagent and worktree behavior

## LSP (`.lsp.json` at the root or `lspServers`)

- command (placeholders, launcher), args, extensionToLanguage, transport, env, initializationOptions, settings (delivered via didChangeConfiguration and workspace/configuration), workspaceFolder, startupTimeout, shutdownTimeout, restartOnCrash, maxRestarts, diagnostics
- One server per extension; conflicts with other plugins
- Client capabilities Claude Code actually sends (capture them), LSP tool operations

## MCP (`.mcp.json`)

- stdio / http / sse / ws; command, args, env, url, headers, headersHelper
- `${user_config.*}` rules, approval, auth, tool naming

## Monitors (`monitors/monitors.json`)

- name, command, description, when (`always`, `on-skill-invoke:<skill>`); interactive CLI only

## Settings and configuration

- Scopes: user, project, local, managed; `enabledPlugins`, `pluginConfigs`
- Permissions (allow/deny/ask), `disableAllHooks`, environment variables

## Environments

- macOS, Linux, WSL, Windows (Git Bash / PowerShell), containers
- CLI, Desktop, IDE, cloud sessions, `-p`/SDK, Cowork: what runs where
- External requirements: binaries, runtimes, package managers, versions, network

## Languages

- Runtime per shipped component: Bash + jq (default), Python stdlib, Node; the user-side requirement each adds
- Test language per component: bash suites (thin hooks), `node:test` with `child_process` (complex handlers, repo `.mjs`); pytest via `uv run --script` once DEBT-0016 is closed
- Lint gates per language: ShellCheck + shfmt, Ruff + Basedpyright, Biome + tsc

## Verification

- Tests under bash and `/bin/bash`, realistic payloads on stdin
- `claude plugin eval`: cases, graders, baseline arm, models
- Live checks with `claude -p --plugin-dir` and `--debug-file`
- `claude plugin validate --strict`, `npm run check`
