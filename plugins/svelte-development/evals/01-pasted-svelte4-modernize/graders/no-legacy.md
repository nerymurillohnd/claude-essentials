---
type: regex
target: { source: "file", path: "Cart.svelte" }
pattern: "export let|<slot|\\son:[a-z]|\\$:|createEventDispatcher|\\$\\$props"
match: not_contains
---
