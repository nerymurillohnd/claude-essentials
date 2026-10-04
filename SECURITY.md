# Security policy

Claude Essentials distributes Claude Code plugins. A plugin runs with the permissions of the person who installs it, so security reports are taken seriously and handled privately.

## Report a vulnerability

Report vulnerabilities through [GitHub private vulnerability reporting](https://github.com/nerymurillohnd/claude-essentials/security/advisories/new). Do not open a public issue, pull request or discussion.

Include:

- the plugin name and version (`claude plugin list`), and your Claude Code version (`claude --version`);
- what an attacker can do, and under which conditions;
- steps or a minimal proof of concept that reproduces it;
- any suggested fix.

## What is in scope

- Code that plugins run on users' machines: hooks, MCP and LSP servers, executables in `bin/`, monitors and mods.
- Instructions in skills, agents or output styles that cause unsafe actions, exfiltrate data or bypass a user's permission choices.
- Secrets, personal data or machine-specific paths shipped in a plugin.
- The repository's CI workflows and release process, including tag and release integrity.

Vulnerabilities in Claude Code itself belong to its vendor; see the [Claude Code documentation](https://code.claude.com/docs/en/plugins/security) for plugin trust guidance.

## Response

| Step                                | Target                                              |
| ----------------------------------- | --------------------------------------------------- |
| Acknowledge the report              | 5 business days                                     |
| Assess and agree on severity        | 10 business days                                    |
| Release a fix for a confirmed issue | As fast as severity requires; critical issues first |

A fix ships as a new plugin release with a `### Security` changelog entry and a GitHub security advisory that credits the reporter unless they ask otherwise. A plugin that cannot be fixed quickly is removed from the catalog.

## Keep your plugins updated

Claude Code does not update plugins from community marketplaces in the background unless you turn that on, so a fix does not reach you automatically. Turn on **Enable auto-update** for `claude-essentials` under `/plugin` → **Marketplaces**, or run `claude plugin update <plugin>@claude-essentials` when an advisory is published.

## Supported versions

Only the latest release of each plugin receives security fixes.

## How plugins are reviewed

Every plugin is reviewed against the [quality bar](docs/quality-bar.md). Plugins that run code also pass the [security review](docs/security-review.md), and each plugin README lists what it runs under **Permissions**.
