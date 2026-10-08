---
description: "Pasted Svelte 4 component, no project: modernised to Svelte 5 with docs and autofixer."
tags: [pilot]
runs: 3
max_turns: 15
timeout_seconds: 300
allowed_tools: [Read, Write, Skill, ToolSearch]
---

I found this component in an old repo and want to reuse it in a new app. Rewrite it the
current way and save it as Cart.svelte in this folder.

```svelte
<script>
  import { createEventDispatcher } from 'svelte';

  export let items = [];
  export let title = 'Cart';

  const dispatch = createEventDispatcher();

  $: total = items.reduce((sum, item) => sum + item.price * item.qty, 0);

  function remove(id) {
    dispatch('remove', { id });
  }
</script>

<h2>{title}</h2>
<ul>
  {#each items as item, i}
    <li>
      <slot name="item" {item}>{item.name}</slot>
      <button on:click={() => remove(item.id)}>Remove</button>
    </li>
  {/each}
</ul>
<p>Total: {total}</p>
<slot name="footer" />
```
