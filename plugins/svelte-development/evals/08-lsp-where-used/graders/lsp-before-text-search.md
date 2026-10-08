---
type: regex
target: "trace"
pattern: "^(?:(?!\"name\":\\s*\"LSP\")[\\s\\S])*\"name\":\\s*\"(?:Grep|Glob)\""
match: not_contains
---
