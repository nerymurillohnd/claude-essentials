---
description: In a SvelteKit 2 project, Claude proposes the migration to SvelteKit 3 before writing, and writes no SvelteKit 3 API into the SvelteKit 2 project.
runs: 2
max_turns: 30
allowed_tools:
  [
    Read,
    Glob,
    Grep,
    Skill,
    Bash,
    Edit,
    Write,
    "mcp__plugin_svelte-development_svelte__*",
  ]
---

The route src/routes/items/[id] must only match numeric ids. Add a param matcher for it.
