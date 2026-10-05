---
type: regex
target: { source: file, path: "src/routes/profile/[id]/+page.svelte" }
pattern: "export let data[\\s\\S]*\\$app/stores[\\s\\S]*\\{@html data\\.bio\\}"
weight: 2
---
