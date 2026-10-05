---
description: A whole-project error check runs the project checker from the command line.
runs: 2
max_turns: 25
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

Check this whole project for type errors and tell me what you find.
