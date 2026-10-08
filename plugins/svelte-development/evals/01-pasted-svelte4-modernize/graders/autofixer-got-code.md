---
type: regex
target: "mock_calls"
pattern: "\"code\"\\s*:\\s*\"[^\"<]{0,200}\\.svelte\""
match: not_contains
weight: 0.5
---
