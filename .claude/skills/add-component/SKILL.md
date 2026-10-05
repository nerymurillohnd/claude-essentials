---
name: add-component
description: Adds a skill or an agent to an existing claude-essentials plugin with the official generator, then completes, validates and drives it and prepares the minor release. Use when asked to add a skill, agent or subagent to a plugin that already exists.
argument-hint: "<plugin> skill|agent <name> <one-line description>"
arguments: [plugin, kind, name]
---

# Add a component to a plugin

```
- [ ] 1 Scaffold   add_component.py on a $plugin/<topic> branch
- [ ] 2 Write      replace the TODOs in the component and the CHANGELOG note
- [ ] 3 Validate   validate --strict and check.py
- [ ] 4 Drive      drive_plugin.py with the new component
- [ ] 5 Release    /release-plugin $plugin minor <topic>
```

1. **Scaffold.** `git switch -c $plugin/add-$name`, then `scripts/add_component.py $plugin $kind $name --description "<one-line description>"`. It runs `claude plugin init` in a throwaway config, copies the generated example under the new name, adds a TODO note under `## [Unreleased]` and regenerates the README.
2. **Write.** Fill the component from the installing user's point of view (`docs/authoring.md`, `docs/quality-bar.md`); write skills with the `skills-best-practices` skill when it is available. Replace the CHANGELOG TODO with a user-facing note.
3. **Validate.** `claude plugin validate plugins/$plugin --strict`, then `scripts/check.py`.
4. **Drive.** `scripts/drive_plugin.py $plugin --prompt "/$plugin:$name …" --expect '<what it does>'` for a skill; for an agent, a prompt that should delegate to it.
5. **Release.** A new compatible component is a MINOR release: ask the maintainer to run `/release-plugin $plugin minor add-$name` (only the maintainer can start it), which bumps, commits and opens the pull request.

## Gotchas

- Hooks, MCP and LSP servers, monitors and output styles are not scaffolded here: they merge into shared files and need `docs/security-review.md`. Use `claude plugin init --with <kind>` in a throwaway config (as `new_plugin.run_init` does) and merge by hand.
- A plugin agent cannot use `hooks`, `mcpServers`, `permissionMode` or `initialPrompt` frontmatter; Claude Code ignores them for plugin subagents.
- Removing or renaming a component is a MAJOR release after a deprecation period (`docs/releasing.md`).
