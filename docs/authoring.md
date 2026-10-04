# Authoring guide

How to build a plugin for Claude Essentials. Every Claude Code fact here links to the official documentation; when this guide and the documentation disagree, the documentation wins and this guide needs a fix.

**Contents:** [Layout](#layout) · [Components](#components) · [Paths and portability](#paths-and-portability) · [Manifest](#manifest) · [Skills](#skills) · [Code that runs](#code-that-runs) · [Documentation](#documentation) · [Check your work](#check-your-work)

## Layout

Create plugins with `python3 scripts/new_plugin.py`; it runs the official `claude plugin init` in a throwaway configuration and adapts the result. Each plugin lives in `plugins/<name>/`:

```text
plugins/<name>/
├── .claude-plugin/plugin.json   manifest (only this file goes in .claude-plugin/)
├── skills/<skill>/SKILL.md      one directory per skill
├── agents/<agent>.md            subagents
├── commands/<command>.md        legacy command files; prefer skills
├── output-styles/<style>.md     output styles
├── hooks/hooks.json             hooks, with a top-level "hooks" key
├── .mcp.json                    MCP servers
├── .lsp.json                    LSP servers
├── bin/                         executables on the Bash tool's PATH
├── README.md                    generated blocks plus your explanations
└── CHANGELOG.md                 Keep a Changelog, newest release first
```

Source: [Plugin manifest reference, standard layout](https://code.claude.com/docs/en/plugins/manifest-reference#standard-layout).

- A `CLAUDE.md` at the plugin root is never loaded; put instructions in a skill.
- A root `SKILL.md` is the skills-directory layout; marketplace plugins use `skills/<name>/SKILL.md`.

## Components

| Need                                             | Use                                    | Docs                                                                           |
| ------------------------------------------------ | -------------------------------------- | ------------------------------------------------------------------------------ |
| Instructions Claude follows for a task           | Skill                                  | [Skills](https://code.claude.com/docs/en/skills)                               |
| A specialist Claude delegates to                 | Agent                                  | [Subagents](https://code.claude.com/docs/en/sub-agents)                        |
| A response format or persona                     | Output style                           | [Output styles](https://code.claude.com/docs/en/output-styles)                 |
| A deterministic action on an event               | Hook                                   | [Hooks](https://code.claude.com/docs/en/hooks)                                 |
| Tools that reach an external system              | MCP server                             | [MCP](https://code.claude.com/docs/en/mcp)                                     |
| Code intelligence for a language                 | LSP server                             | [Code intelligence](https://code.claude.com/docs/en/plugins/code-intelligence) |
| Changing Claude Code's own behavior or interface | Mod, only when nothing above can do it | [Mods](https://code.claude.com/docs/en/plugins/mods/overview)                  |

Plugin skills and agents are namespaced: a skill `review` in plugin `code-checks` runs as `/code-checks:review`.

## Paths and portability

Claude Code copies each installed plugin, alone, to `~/.claude/plugins/cache/<marketplace>/<plugin>/<version>/` ([loading reference](https://code.claude.com/docs/en/plugins/loading#find-plugins-on-disk)). Everything a plugin needs must be inside its directory.

- Reference bundled files as `${CLAUDE_PLUGIN_ROOT}/...` and persistent state as `${CLAUDE_PLUGIN_DATA}/...` ([environment variables](https://code.claude.com/docs/en/plugins/manifest-reference#environment-variables)). `${CLAUDE_PLUGIN_ROOT}` changes on every update, so never write state there.
- In shell-form hook commands, quote the variable: `"${CLAUDE_PLUGIN_ROOT}"/scripts/check.sh`, or use exec form with `args`.
- The variables are not set in the Bash tool's environment; in skills and agents, write the `${...}` reference in the Markdown body so Claude Code substitutes it.
- Never use `../`, absolute or home paths, user or machine names, personal emails or secrets. `python3 scripts/check.py` rejects them.
- Links from a plugin README to other repository files are absolute GitHub URLs; `scripts/sync_readmes.py` generates them.

## Manifest

`scripts/new_plugin.py` writes the manifest. Rules:

- `name` is permanent: users install, enable and configure the plugin by `<name>@claude-essentials`. Use `displayName` for the label. See [naming](naming.md).
- `version` lives only in `plugin.json`, never in the marketplace entry. Do not change it in feature pull requests; releases change it ([releasing](releasing.md)).
- `metadata.minClaudeCodeVersion` states the oldest Claude Code version you tested; it appears in the README badge and requirements.
- `keywords` include the category. `license` is `MIT`; `repository` is this repository.
- Declare `userConfig` for values users must provide instead of asking them to edit settings; sensitive values go to secure storage ([user configuration](https://code.claude.com/docs/en/plugins/manifest-reference#user-configuration)).

## Skills

- `description` says what the skill does and when to use it, in the third person, using the words a user's request would contain. Claude uses it to decide when to load the skill.
- Use `disable-model-invocation: true` for skills with side effects that should only run when the user asks.
- Do not depend on `allowed-tools` pre-approval: organizations can disable it for third-party marketplaces.
- Assume auto mode is on: instructions must not ask Claude to run destructive or irreversible commands without the user's confirmation.
- Run `/doctor prompt-audit plugins/<name>` in a Claude Code session to catch prompting patterns written for older models and stale paths.
- Frontmatter fields: [skills reference](https://code.claude.com/docs/en/skills#frontmatter-reference).

## Code that runs

Hooks, MCP and LSP servers, executables, monitors and mods run with the permissions of the person who installs the plugin. They need:

- a **Permissions** section in the README explaining why each item is needed (the generated table lists what runs);
- interpreters and tools listed under Requirements; never assume a runtime such as `bun` is installed;
- no network access or downloads at install time, no undeclared remote servers, no secrets;
- fast, robust hooks that never start background daemons: a hook that fails to match can block the tool call it guards.

Mods additionally need `metadata.minClaudeCodeVersion` of at least 2.1.287 and tests that `claude plugin test` runs. See the [security review](security-review.md).

## Documentation

The README template has author sections (Overview, Usage, the explanation under Permissions) and generated blocks. Write the author sections; run `python3 scripts/sync_readmes.py` for the rest. Details in the [README guide](readme-guide.md).

## Check your work

```bash
claude plugin validate plugins/<name> --strict   # official validator
python3 scripts/check.py                                        # every gate CI runs
python3 scripts/check.py test-install                                 # install in a throwaway config
```

For plugins that shape Claude's behavior, `claude plugin eval` compares results with and without the plugin ([plugin evals](https://code.claude.com/docs/en/plugin-evals)); include results in your pull request when you have them.
