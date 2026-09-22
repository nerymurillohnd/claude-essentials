---
type: regex
target: {source: file, path: calc.py}
match: not_contains
flags: i
---
noqa|fmt:\s*(off|skip)|isort:\s*(skip|off)|yapf:\s*disable|ruff:\s*(ignore|disable|file-ignore)
