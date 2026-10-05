---
description: A component task goes to the editor, which reads the docs before writing and validates after.
runs: 2
max_turns: 60
allowed_tools:
  [
    Read,
    Glob,
    Grep,
    Skill,
    LSP,
    Agent,
    Bash,
    Write,
    Edit,
    "mcp__plugin_svelte-development_svelte__*",
  ]
---

Add src/lib/components/TodoList.svelte: it takes `items` (an array of `{ id, text, done }`) as a prop the parent can bind to, renders every item with a checkbox bound to its `done` field, and lets the parent customise how each item's text is rendered. Then use it on the home page with three sample items.
