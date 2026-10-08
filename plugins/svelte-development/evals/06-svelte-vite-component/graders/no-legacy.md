---
type: regex
target: { source: "file", path: "src/lib/Accordion.svelte" }
pattern: "export let|<slot|\\son:[a-z]|\\$:|createEventDispatcher|\\$\\$props"
match: not_contains
---
