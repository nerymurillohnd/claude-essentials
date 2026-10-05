---
description: A where-is-it-used question in a Svelte project must load svelte-lsp-navigation.
runs: 2
max_turns: 20
allowed_tools:
  [Read, Glob, Grep, Skill, LSP, "mcp__plugin_svelte-development_svelte__*"]
---

Where is the CounterButton component used in this project, and which files call formatCount?
