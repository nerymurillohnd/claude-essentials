---
type: regex
target: { source: file, path: src/lib/components/TodoList.svelte }
pattern: "export let|<slot|\\son:[a-z]|\\$\\$props"
match: not_contains
---
