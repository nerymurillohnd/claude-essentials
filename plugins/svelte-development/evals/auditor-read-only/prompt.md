---
description: An audit request goes to the read-only auditor, which reports findings and changes nothing.
runs: 2
max_turns: 40
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

Audit the src/routes/profile folder of this SvelteKit project before we ship it.
