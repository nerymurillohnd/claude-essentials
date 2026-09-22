---
type: regex
pattern: 'tool\.ruff'
target: {source: file, path: pyproject.toml}
match: not_contains
flags: i
---
