---
type: regex
target: { source: file, path: src/lib/Disclosure.svelte }
pattern: "export let|<slot|\\son:[a-z]|createEventDispatcher"
match: not_contains
---
