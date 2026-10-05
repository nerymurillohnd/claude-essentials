---
description: A route parameter matcher must use the SvelteKit 3 API, found through the docs and checked against the changelog.
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
    WebFetch,
    "mcp__plugin_svelte-development_svelte__*",
  ]
---

Add a route /items/[id] whose page shows the id, and make the route match only when id is a positive integer, using SvelteKit's parameter matchers.
