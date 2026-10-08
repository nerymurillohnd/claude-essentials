---
type: regex
target: "trace"
pattern: "^(?:(?!\"name\":\\s*\"LSP\")[\\s\\S])*\"name\":\\s*\"Grep\""
match: not_contains
---
