---
type: llm
---

PASS if the reply says the rewrite targets Svelte 5 (runes) and explains how the removed
event, the slots and the reactive total are now expressed (callback prop, snippets, $derived).
FAIL if it introduces SvelteKit APIs ($app/..., +page files, load) for this standalone
component, or does not say which Svelte version the code is for.
