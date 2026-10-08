---
type: regex
target: { source: "file", path: "src/lib/components/TodoList.svelte" }
pattern: "export let|<slot|\\son:[a-z]|\\$:|createEventDispatcher|\\$\\$props"
match: not_contains
---
