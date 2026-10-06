---
type: llm
---

PASS if the answer says that `doubled` should be computed with `$derived` (for example `let doubled = $derived(count * 2)`) instead of an `$effect` that writes to `$state`, and that the button mutates the `count` prop (`count++`) although the component does not own it, suggesting a local state, a callback prop or `$bindable`.
FAIL if either problem is missing, or if the answer recommends Svelte 4 syntax such as `export let`, `$:` or `on:click`.
