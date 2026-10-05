---
description: A Svelte 4 to Svelte 5 migration request must load svelte-best-practices.
runs: 2
max_turns: 15
allowed_tools: [Read, Glob, Grep, Skill]
---

Convert this component to Svelte 5 and reply with the converted code:

```svelte
<script>
  export let items = [];
  export let title;
  let filter = '';
  $: visible = items.filter((item) => item.name.includes(filter));
</script>

<h2>{title}</h2>
<input bind:value={filter} on:input={() => console.log(filter)} />
<ul>
  {#each visible as item}
    <li on:click={() => alert(item.name)}>{item.name}</li>
  {/each}
</ul>
<slot name="footer" />
```
