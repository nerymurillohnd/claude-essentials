---
status: accepted
date: 2026-10-03
decision-makers:
  - "Nery Samuel Murillo (maintainer)"
---

# Security posture for code that runs on users' machines

## Purpose

Decide which plugin components are accepted and how they are reviewed, given that every plugin runs with the permissions of the person who installs it.

## Scope

Hooks, MCP and LSP servers, executables in `bin/`, monitors and mods in any plugin; `SECURITY.md`, `CODEOWNERS` and the review process.

## Context and problem statement

Skills and agents are instructions. Hooks, MCP and LSP servers, executables and monitors run processes on the user's machine. Mods (Claude Code 2.1.287 and later) run JavaScript or TypeScript inside Claude Code, unsandboxed: they can read and rewrite prompts and tool calls, approve tool calls, make network requests and spend the user's usage. Background auto-update is off by default for community marketplaces, so a fix does not reach users until they update.

## Decision drivers

- Protect the people who install plugins.
- Keep useful capabilities available for plugins that need them.
- Make every capability visible before installation.

## Considered options

- Allow everything under strict review, with mods only when nothing else can do the job
- Allow only instruction components (skills, agents, output styles, commands)
- Standard review for everything

## Decision outcome

Chosen option: **strict review**:

- Every pull request touching hooks, `.mcp.json`, `.lsp.json`, `bin/`, `monitors/` or workflows gets the `security-review` label automatically and needs a code owner's approval.
- The plugin README documents every such component under **Permissions**; a generated table lists what runs, so documentation cannot drift from configuration.
- No downloads or network access at install time, no undeclared remote servers, no secrets, no machine-specific paths.
- Mods are accepted only when the in-process capability delivers something a skill, settings hook or MCP server cannot; they require `metadata.minClaudeCodeVersion` of at least 2.1.287, tests run by `claude plugin test`, and the `hooks:`/`calls:` lines from `claude plugin validate` attached to the pull request.
- Vulnerabilities are reported through GitHub private vulnerability reporting; advisories tell users to update explicitly because auto-update is off by default.

### Consequences

- Good, because users see what a plugin runs before installing it.
- Bad, because privileged plugins take longer to review.

### Confirmation

`scripts/check_repo.py` requires the Permissions section for privileged plugins and the mod requirements; the labeler applies `security-review`; CODEOWNERS covers `plugins/` and `.github/`. See [docs/security-review.md](../security-review.md).

## Pros and cons of the options

### Strict review

- Good, because it keeps capabilities available with visibility and accountability.
- Bad, because reviewer capacity limits throughput.

### Instruction components only

- Good, because nothing runs code.
- Bad, because guardrail and integration plugins become impossible.

## More information

Docs: [Plugin security and trust](https://code.claude.com/docs/en/plugins/security), [Mods overview](https://code.claude.com/docs/en/plugins/mods/overview).
