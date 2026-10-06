---
description: In a SvelteKit 2 project, a param matcher is written the SvelteKit 2 way, not with SvelteKit 3 APIs.
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
