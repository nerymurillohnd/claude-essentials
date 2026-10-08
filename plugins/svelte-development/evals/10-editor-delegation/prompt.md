---
description: "Multi-file feature: delegated to the editor agent, Svelte 5 result in the files."
runs: 3
max_turns: 40
timeout_seconds: 1200
allowed_tools:
  [
    Read,
    Glob,
    Grep,
    Edit,
    Write,
    Bash,
    LSP,
    Skill,
    ToolSearch,
    TodoWrite,
    Agent,
  ]
---

Add a /todos page with a TodoList component in src/lib/components/TodoList.svelte: I can add
todos, mark them done, and filter all / active / done.
