---
type: regex
target: {source: file, path: app.py}
match: not_contains
flags: i
---
noqa|fmt:\s*(off|skip)|isort:\s*(skip|off)|ruff:\s*(ignore|disable|file-ignore)
