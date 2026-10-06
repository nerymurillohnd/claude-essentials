---
description: After a small inline edit of a component, the autofixer checks the new content.
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
    Edit,
    Write,
    "mcp__plugin_svelte-development_svelte__*",
  ]
---

In CounterButton, show the label in bold.
