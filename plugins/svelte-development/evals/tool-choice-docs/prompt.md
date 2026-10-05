---
description: An API question goes to the Svelte documentation tools, not to the LSP.
runs: 2
max_turns: 15
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

How do I declare a prop that the parent can bind to in Svelte 5, with a default value? Show a short example.
