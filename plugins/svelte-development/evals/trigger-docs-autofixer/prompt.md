---
description: A request to check Svelte code for problems must load svelte-docs-and-autofixer.
runs: 2
max_turns: 15
allowed_tools:
  [Read, Glob, Grep, Skill, "mcp__plugin_svelte-development_svelte__*"]
---

Is anything wrong with this Svelte 5 component? List the problems.

```svelte
<script>
  let { count } = $props();
  let doubled = $state(0);
  $effect(() => {
    doubled = count * 2;
  });
</script>

<button onclick={() => count++}>{doubled}</button>
```
