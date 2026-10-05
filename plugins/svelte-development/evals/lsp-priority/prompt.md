---
description: Symbol questions are answered with the LSP first; an empty result is retried before any fallback.
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

I want to rename the `label` prop of CounterButton to `caption`. List every place that would have to change, and tell me whether the Counter class's `reset` method is called anywhere. Do not edit anything yet.
