---
type: regex
pattern: 'noqa|fmt:\s*(off|skip)|isort:\s*(skip|off)|yapf:\s*disable|ruff:\s*(ignore|disable|file-ignore)'
target: {source: file, path: app.py}
match: not_contains
flags: i
---
