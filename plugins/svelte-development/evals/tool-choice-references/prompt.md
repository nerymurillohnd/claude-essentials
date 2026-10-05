---
description: A usage question about project code goes to the LSP, not to the documentation tools.
runs: 2
max_turns: 20
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

Is formatCount used anywhere besides where it is defined?
