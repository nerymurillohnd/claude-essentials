---
description: Questions about dynamically used components are answered with documentSymbol and findReferences, not dismissed as invisible to the language server.
runs: 2
max_turns: 30
allowed_tools:
  [
    Read,
    Glob,
    Grep,
    Skill,
    LSP,
    Bash,
    "mcp__plugin_svelte-development_svelte__*",
  ]
---

Is the CounterButton component used anywhere other than the home page, including dynamically? I need every usage before I change its props.
