# Topic routing — where each Claude Code topic lives

Every slug and quoted section name below was validated against the live index and docs map on 2026-09-20
by `ccdocs.py selfcheck` (map stamp 2026-09-19). Re-run `ccdocs.py selfcheck` to re-validate this file in
two HTTP requests rather than trusting the date. Slugs are relative to `https://code.claude.com/docs/en/`
(append `.md` for raw markdown). Page slugs change rarely; section names change more often. If a slug 404s
or a section is missing, run `ccdocs.py find <keyword>`; if the term isn't a heading at all (env var,
settings key, error string), run `ccdocs.py grep <term>`. Both read live sources, so they are right even
when this file is stale.

"Volatile" lists the details that churn release-to-release. Never answer those from memory or from
this file — fetch the section and cross-check the changelog.

## Contents
1. Hooks
2. MCP
3. LSP / code intelligence
4. Agents overview, subagents, forks
5. Agent teams, agent view, cross-session messaging, worktrees
6. Dynamic workflows
7. Skills
8. Plugins
9. Marketplaces & plugin distribution
10. GitHub Actions, GitLab CI/CD, Code Review, headless/CI
11. Models, effort, context window
12. Memory: CLAUDE.md, AGENTS.md, auto memory
13. Rules files (`.claude/rules/`) and the `.claude` directory
14. Settings, permissions, tools (cross-cutting)
15. Agent SDK counterparts

---

## 1. Hooks
- Guide (task-oriented, examples): `hooks-guide` — sections: "What you can automate", "How hooks work",
  "Filter hooks with matchers", "Prompt-based hooks", "Agent-based hooks", "HTTP hooks", "Limitations and troubleshooting".
- Reference (authoritative schema): `hooks` — "Hook lifecycle", "Configuration" (locations, matcher
  patterns, handler fields: command / HTTP / MCP tool / prompt / agent), "Hook input and output"
  (exit codes, "Exit code 2 behavior per event", JSON output, "Decision control"), "Hook events"
  (one section per event, each with `<Event> input` and `<Event> decision control`), "Run hooks in the
  background", "Security considerations", "Debug hooks".
- Related: `sub-agents` → "Define hooks for subagents"; `skills` (hooks in skill frontmatter);
  `plugins-reference` → "Hooks"; `agent-teams` → "Enforce quality gates with hooks"; `settings-reference`
  (hook-related settings); `agent-sdk/hooks` (SDK callbacks — different API).
- Volatile: the event list (events are added often), per-event input fields, which events can block,
  decision-control JSON keys, handler types, matcher syntax, timeouts. Always fetch the specific event section.
- Fetch pattern: `ccdocs.py outline hooks` → `ccdocs.py page hooks --section "PreToolUse decision control"`.

## 2. MCP
- Quickstart: `mcp-quickstart`. Main: `mcp` — "Installing MCP servers" (HTTP/SSE/stdio/WebSocket),
  "MCP installation scopes" (local/project/user, precedence, env-var expansion in `.mcp.json`),
  "Authenticate with remote MCP servers" (OAuth, headersHelper), "Use MCP servers from claude.ai",
  "Use Claude Code as an MCP server", "MCP output limits and warnings", "Scale with MCP tool search",
  "Use MCP prompts as commands", "Respond to MCP elicitation requests", "Push messages with channels".
- Org control: `managed-mcp` (managed-mcp.json, `managedMcpServers`, allow/deny lists).
- Related: `channels`, `channels-reference`; `plugins-reference` → "MCP servers"; `sub-agents` →
  "Scope MCP servers to a subagent"; `hooks` → "Match MCP tools", "MCP tool hook fields";
  `agent-sdk/mcp`, `agent-sdk/tool-search`; `cli-reference` (`claude mcp …` subcommands).
- Protocol spec (outside Claude Code): https://modelcontextprotocol.io
- Volatile: transports supported, CLI flags, scope file locations, output-token limits and their env
  vars, tool-search defaults, OAuth options.

## 3. LSP / code intelligence
There is no standalone LSP page. LSP is delivered through plugins:
- `plugins` → "Add LSP servers to your plugin" (how-to).
- `plugins-reference` → "LSP servers" (config schema for `.lsp.json` / manifest field).
- `tools-reference` → "LSP tool behavior" (what the LSP tool does at runtime).
- `discover-plugins` → "Code intelligence" (official marketplace LSP plugins) and troubleshooting
  "Code intelligence issues".
- Official marketplace contents (which language servers ship as plugins):
  https://raw.githubusercontent.com/anthropics/claude-plugins-official/main/.claude-plugin/marketplace.json
- Volatile: supported languages/plugins, required binaries, config fields. Search the changelog: `ccdocs.py changelog --grep LSP --last 20`.

## 4. Agents overview, subagents, forks
- Chooser page: `agents` — "Choose an approach" across subagents, forks, agent teams, agent view, workflows, worktrees.
- Subagents: `sub-agents` — "Built-in subagents", "Supported frontmatter fields", "Choose a model",
  "Available tools", "Restrict which subagents can be spawned", "Permission modes", "Preload skills into
  subagents", "Enable persistent memory", "Run subagents in foreground or background",
  "Let subagents spawn their own subagents", "Concurrent subagent limit", "Fork the current conversation".
- Related: `tools-reference` → "Agent tool behavior"; `hooks` → SubagentStart/SubagentStop;
  `agent-sdk/subagents`; `cli-reference` (`--agents` flag), `settings-reference`.
- Volatile: frontmatter fields, built-in agent roster and their models, nesting/concurrency limits, fork behavior.

## 5. Agent teams, agent view, cross-session messaging, worktrees
- `agent-teams` — "Enable agent teams" (check whether it is still experimental/flag-gated), "Compare with
  subagents", "Choose a display mode", "Use subagent definitions for teammates", "Permissions",
  "Token usage", "Limitations".
- `agent-view` — background sessions dashboard (`claude agents`), dispatch, supervisor process.
- `cross-session-messaging` — messaging other sessions, restrictions.
- `worktrees` — isolation, "Isolate subagents with worktrees", WorktreeCreate/WorktreeRemove hooks.
- Hooks: `hooks` → TeammateIdle, TaskCreated, TaskCompleted.
- Volatile: enablement flags, display modes, limits, availability by plan/platform.

## 6. Dynamic workflows
- `workflows` — "When to use a workflow", "Run a bundled workflow", "Have Claude write a workflow"
  (keyword, `ultracode`, plan approval, save for reuse, distribute in a plugin, pass input),
  "How a workflow runs" ("Behavior and limits"), "Manage runs" (resume, usage limits, cost, size guideline, turn off).
- Related: `plugins-reference` (workflows as a plugin component), `claude-directory` (where saved workflows live), `agents`.
- Volatile: trigger keyword, bundled workflow list, size guideline/limits, cost behavior, availability.

## 7. Skills
- `skills` — "Bundled skills", "Choose where skills load" (personal/project/plugin/managed, monorepos,
  name collisions, claude.ai-synced skills), "Frontmatter reference", "Available string substitutions",
  "Add supporting files", "Control who invokes a skill", "Skill content lifecycle", "Pre-approve tools for a
  skill", "Pass arguments to skills", "Inject dynamic context", "Run skills in a subagent",
  "Restrict Claude's skill access", "Override skill visibility from settings", "Troubleshooting"
  (not triggering / triggers too often / descriptions cut short).
- Related: `commands` (built-in slash commands; custom commands merged into skills), `features-overview`
  (skills vs CLAUDE.md vs subagents), `costs` → "Move instructions from CLAUDE.md to skills",
  `plugins-reference` → "Skills", `agent-sdk/skills`.
- Open standard for SKILL.md outside Claude Code: `skills` → "Using skill frontmatter outside Claude Code";
  API-side Agent Skills live in the platform docs (https://platform.claude.com/llms.txt, search "skills").
- Volatile: frontmatter keys, description length limits, substitution variables, load locations, bundled skill list.

## 8. Plugins
- Create: `plugins` — structure, adding skills/LSP/monitors/default settings, "Test your plugins
  locally", "Debug plugin issues", "Convert existing configurations to plugins".
- Reference: `plugins-reference` — "Plugin components reference" (Skills, Agents, Hooks, MCP servers,
  LSP servers, Monitors, Themes), "Plugin manifest schema" (complete schema, required fields, component
  path fields, user configuration, env vars like the plugin-root variable), "Plugin caching and file
  resolution", "Plugin directory structure", "CLI commands reference" (`claude plugin …`), "Debugging".
- Test: `plugin-evals` (`claude plugin eval`, may be early access — check "Troubleshooting").
- Install/use: `discover-plugins`.
- SDK: `agent-sdk/plugins`.
- Volatile: manifest fields, component types, CLI subcommands, env var names, caching paths.

## 9. Marketplaces & plugin distribution
- Consume: `discover-plugins` — official vs community marketplace, add from GitHub/git/local/URL/claude.ai,
  auto-updates, "Configure team marketplaces".
- Author/host: `plugin-marketplaces` — "Marketplace schema", "Plugin entries", "Plugin sources"
  (relative, GitHub, git, git subdir, npm, zip, command), "Strict mode", "Host and distribute",
  "Require marketplaces for your team", "Managed marketplace restrictions", "Version resolution and
  release channels", "Validation and testing", CLI `plugin marketplace …`.
- Versions: `plugin-dependencies`. Org recommendation: `plugin-relevance`, `plugin-hints`.
- Enterprise lockdown: `managed-settings`, `settings-reference` (marketplace-related keys).
- Live marketplace data: official marketplace JSON (URL in §3); README at
  https://github.com/anthropics/claude-plugins-official
- Volatile: source types, schema fields, managed restriction keys.

## 10. GitHub Actions, GitLab CI/CD, Code Review, headless/CI
- `github-actions` — "Setup" (quick `/install-github-app`, manual, org), "GitHub App permissions",
  "Interactive and automation modes", "Who can trigger runs", "Best practices", "Advanced configuration"
  ("Action parameters", "Pass CLI arguments"), "Upgrade from beta".
- `github-actions-cloud-providers` (Bedrock / Vertex / Foundry auth), `github-enterprise-server`.
- `gitlab-ci-cd` — setup, OIDC/WIF examples, parameters.
- `code-review` — managed PR review (REVIEW.md, pricing, local diff review, ultrareview) — distinct from the Action.
- `headless` — `claude -p`, bare mode, structured/streaming output, auto-approve, SIGTERM; plus
  `cli-reference` for flags and `env-vars`.
- Action source of truth (inputs change with releases — prefer these over docs for exact input names):
  - https://raw.githubusercontent.com/anthropics/claude-code-action/main/action.yml
  - https://raw.githubusercontent.com/anthropics/claude-code-action/main/docs/{usage,configuration,setup,security,solutions,faq,custom-automations,migration-guide}.md
  - Releases/tags: `gh release list -R anthropics/claude-code-action`, or without `gh`/API access:
    `git ls-remote --tags https://github.com/anthropics/claude-code-action` (shows what the moving `v1` tag
    points at, so you can pin a full commit SHA for supply-chain safety).
- Volatile: action inputs, auth options (OAuth token vs API key vs OIDC federation), permissions, version tag.

## 11. Models, effort, context window
- `model-config` — "Available models", "Model aliases", "Setting your model", "Restrict model selection",
  "Organization default model", "`opusplan`", "Fallback model chains", "Adjust effort level",
  "Extended thinking", "Extended context", "Context window and auto-compaction", "Environment variables"
  (pinning IDs for Bedrock/Vertex/Foundry).
- Related: `fast-mode`, `advisor`, `costs`, `prompt-caching`, `sub-agents` → "Choose a model",
  `settings-reference` (model, effort keys), `third-party-integrations` + provider pages.
- Model IDs, context sizes, pricing, deprecations (API-side truth): https://platform.claude.com/docs/en/models/overview.md
  and the platform index https://platform.claude.com/llms.txt.
- Volatile: EVERYTHING here. Aliases resolve to different models over time; new models ship often.
  Never state a model ID, alias target, context size or price without fetching today.

## 12. Memory: CLAUDE.md, AGENTS.md, auto memory
- `memory` — "CLAUDE.md vs auto memory", "Choose where to put CLAUDE.md files", "Import additional files"
  (`@path`), "How CLAUDE.md files load", "Organize rules with `.claude/rules/`", "Manage CLAUDE.md for large
  teams" (org-wide, excludes), "AGENTS.md" (when read, precedence vs CLAUDE.md, availability), "Auto memory"
  (enable/disable, storage location, audit), "View and edit with `/memory`", "Troubleshoot memory issues".
- Related: `best-practices` → "Write an effective CLAUDE.md"; `large-codebases` (layering, per-dir vs path rules);
  `prompt-caching` → "Editing CLAUDE.md mid-session"; `sub-agents` → "Enable persistent memory";
  `hooks` → InstructionsLoaded; `agent-sdk/claude-code-features` → "Project instructions (CLAUDE.md and rules)".
- Volatile: AGENTS.md support was added in 2.1.277 (per changelog) — load order, precedence, and provider
  availability are young and likely to change; auto memory paths/toggles.

## 13. Rules files (`.claude/rules/`) and the `.claude` directory
- `memory` → "Organize rules with `.claude/rules/`": "Set up rules", "Path-specific rules" (frontmatter
  path globs), "Share rules across projects with symlinks", "User-level rules".
- `large-codebases` → "Choose between per-directory CLAUDE.md and path-scoped rules".
- `claude-directory` — interactive map of every file under `.claude/` and `~/.claude/` (CLAUDE.md,
  settings, hooks, skills, commands, agents, workflows, rules, auto memory) + "Choose the right file".
- Not to be confused with permission rules (`permissions`) or security-guidance rules (`security-guidance`).

## 14. Settings, permissions, tools (cross-cutting — most answers touch these)
- `settings` (files, scopes, precedence, merge), `settings-reference` (every key), `settings-example`,
  `managed-settings`, `server-managed-settings`.
- `permissions` (rule syntax), `permission-modes`, `auto-mode-config`, `sandboxing`.
- `tools-reference` (every built-in tool), `commands` (slash commands), `cli-reference`, `env-vars`,
  `interactive-mode`, `glossary`, `debug-your-config`, `errors`, `troubleshooting`, `feature-availability`.
- JSON Schema for settings.json (editor validation): https://json.schemastore.org/claude-code-settings.json
  (community-maintained on SchemaStore — may lag; the docs `settings-reference` wins on conflict).

## 15. Agent SDK counterparts
Same concepts, different API surface — do not mix CLI config answers with SDK answers:
`agent-sdk/hooks`, `agent-sdk/mcp`, `agent-sdk/subagents`, `agent-sdk/skills`, `agent-sdk/plugins`,
`agent-sdk/permissions`, `agent-sdk/claude-code-features`, `agent-sdk/typescript`, `agent-sdk/python`.
