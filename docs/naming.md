# Naming conventions

## Plugins

| Rule                                                                                                                                                                                                  | Why                                                                                                                                                                                                                                                                                                                    |
| ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| kebab-case: lowercase letters, digits and single hyphens, starting with a letter, at most 64 characters                                                                                               | Claude Code accepts letters, digits, `.`, `_` and `-` in plugin ids, so kebab-case, the leading letter and the 64-character limit are this repository's stricter convention; `claude plugin validate` warns on non-kebab names ([manifest reference](https://code.claude.com/docs/en/plugins/manifest-reference#name)) |
| Never starts with `claude-`, `anthropic-`, `anthropics-` or `cc-plugin-`; never `claude`, `anthropic`, `anthropics`, `claude-code` or `claude-mods`; `official` never next to `claude` or `anthropic` | `claude plugin validate` rejects names that pass as Anthropic's own plugins                                                                                                                                                                                                                                            |
| Never contains `claude` or `anthropic` as a word                                                                                                                                                      | The validator warns, which fails `--strict`                                                                                                                                                                                                                                                                            |
| Never `anthropic-skills` or `claude-ai`                                                                                                                                                               | Both start with a reserved prefix, so `claude plugin validate` fails them; since 2.1.282 skills in the `anthropic-skills` namespace do not load (the `claude-ai` restriction was reverted in 2.1.283)                                                                                                                  |
| Describes what it does: `release-notes-writer`, not `helper`                                                                                                                                          | Users choose plugins from a list                                                                                                                                                                                                                                                                                       |
| Permanent once published                                                                                                                                                                              | Users install and enable plugins by `<name>@claude-essentials`; a rename breaks every install unless a `renames` entry migrates it ([host a marketplace](https://code.claude.com/docs/en/plugins/host-marketplace#rename-or-remove-a-plugin))                                                                          |

The directory name, the marketplace entry `name` and the manifest `name` are identical. Use `displayName` for a human-friendly label.

## Components

- Skill directories and `name` fields: kebab-case and specific. Users type `/<plugin>:<skill>`. Unlike plugin names, skill names may contain `claude` or `anthropic`: Claude Code reserves only `synced` and `anthropic-skills` for skills ([skills](https://code.claude.com/docs/en/skills)). A skill that is also uploaded to claude.ai or the Claude API cannot contain either word ([Agent Skills](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview)).
- Agents: kebab-case file names; referred to as `<plugin>:<agent>`.
- MCP servers: short kebab-case keys; tools appear as `mcp__plugin_<plugin>_<server>__<tool>`.

## Tags

| Release | Tag                                                            | Created by                                           |
| ------- | -------------------------------------------------------------- | ---------------------------------------------------- |
| Plugin  | `<name>--v<version>`, for example `svelte-development--v1.2.0` | `claude plugin tag`, after `scripts/bump_version.py` |

## Labels

`type:`, `semver:`, `status:`, `priority:`, `category:<category>` and `plugin:<name>`, plus `security-review`, `good first issue` and `help wanted`. The full list is `.github/labels.yml`.

## Commits and branches

Commits and pull request titles follow Conventional Commits with the plugin name as scope: `feat(release-notes-writer): add changelog skill`. Branch names use the same scope as prefix: `<plugin>/<topic>` for plugin work, `marketplace/`, `scripts/`, `ci/` or `docs/` plus `<topic>` otherwise, short-lived and deleted on merge ([ADR branch-naming](adr/decisions/ADR_2026-10-04_branch-naming.md)). Those four areas are reserved and never plugin names.
