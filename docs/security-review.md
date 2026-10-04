# Security review

Plugins run with the permissions of the person who installs them ([plugin security and trust](https://code.claude.com/docs/en/plugins/security)). This review applies to every pull request that adds or changes code that runs on a user's machine: hooks, MCP and LSP servers, executables in `bin/`, monitors and mods, and to every change to `.github/workflows/`. Pull requests that touch `plugins/*/hooks/`, `.mcp.json`, `.lsp.json`, `bin/`, `monitors/` or `.github/workflows/` receive the `security-review` label automatically; for declarations inside `plugin.json` or mod sources elsewhere, the reviewer applies it by hand. They need a code owner's approval. Policy: [ADR security-posture](adr/decisions/ADR_2026-10-03_security-posture.md).

## Reviewer checklist

### Visibility

- [ ] The README **Permissions** section explains, in plain words, why each item in the generated table is needed.
- [ ] Requirements list every interpreter, tool, service and account the plugin needs.
- [ ] `userConfig` declares every value the user must provide; secrets use `"sensitive": true`.

### Execution

- [ ] Every command is built on `${CLAUDE_PLUGIN_ROOT}` or `${CLAUDE_PLUGIN_DATA}`, quoted in shell form, or uses exec form with `args`.
- [ ] No `curl | sh`, package installation, download or network access at install time or session start.
- [ ] Hooks finish quickly, start no background processes, and fail open for the user's work unless blocking is the documented purpose.
- [ ] `PreToolUse` and `PermissionRequest` hooks block only what the README says they block.
- [ ] No hook or mod approves tool calls the user would otherwise be asked about, unless that is the plugin's documented purpose.
- [ ] `${user_config.*}` is never used in shell-form commands (Claude Code rejects it; values reach hooks as `CLAUDE_PLUGIN_OPTION_<KEY>`).

### Data and network

- [ ] Every remote host or MCP URL is listed under Permissions; remote MCP servers use `https://`.
- [ ] No secrets, tokens or credentials in the repository, including examples.
- [ ] Data leaves the user's machine only where the README says so, and only to the listed hosts.
- [ ] Files are written only under `${CLAUDE_PLUGIN_DATA}` or where the user asked.

### Mods

- [ ] A skill, settings hook or MCP server cannot do what the mod does (compare the table in the [mods overview](https://code.claude.com/docs/en/plugins/mods/overview#compare-mods-settings-hooks-skills-and-mcp-servers)).
- [ ] The pull request includes the `hooks:` and `calls:` lines from `claude plugin validate`, and each event and call is justified.
- [ ] `claude plugin test` passes; `metadata.minClaudeCodeVersion` is at least 2.1.287.

### Instructions

- [ ] Skills and agents do not instruct Claude to bypass permission prompts, disable safeguards or exfiltrate data.
- [ ] Destructive or irreversible actions require explicit user confirmation, assuming auto mode is on.

## After a vulnerability

Fix it in a new release with a `### Security` changelog entry, publish a GitHub security advisory, and tell users to run `claude plugin update <plugin>@claude-essentials`: background auto-update is off by default for community marketplaces. See [SECURITY.md](../SECURITY.md).
