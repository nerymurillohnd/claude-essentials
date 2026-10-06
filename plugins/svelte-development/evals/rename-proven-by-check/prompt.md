---
description: A prop rename is proven with the project check (baseline, declaration-only change, comparison with the references) and leaves no old name behind.
runs: 2
max_turns: 60
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

Rename the `label` prop of CounterButton to `caption` everywhere it is used, and make sure the rename left nothing broken that was not broken before.
