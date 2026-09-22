---
type: regex
target: {source: file, path: pyproject.toml}
match: not_contains
flags: i
---
tool\.ruff
