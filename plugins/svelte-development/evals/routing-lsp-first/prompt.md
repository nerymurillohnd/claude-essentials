---
description: A question about the project's own symbols starts with the language server, not with text search or whole-file reads.
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

Which files would stop compiling if I deleted the `reset` method from the Counter class? Do not change anything.
