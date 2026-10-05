---
type: regex
target: { source: file, path: src/lib/components/TodoList.svelte }
pattern: "\\$bindable\\([\\s\\S]*\\{#each [^}]*\\(([^)]*\\.)?id\\)[\\s\\S]*\\{@render "
weight: 2
---
