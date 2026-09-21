---
max_turns: 15
timeout_seconds: 400
allowed_tools: [Read, Glob, Grep, Skill, Bash, Write, Edit]
runs: 3
---
En mi repo ya tengo este `.editorconfig`:

```ini
[*.sh]
indent_style = space
indent_size = 2
binary_next_line = true
switch_case_indent = true
```

Quiero formatear los scripts con `shfmt -i 2 -ci`. ¿Me armas el comando para correrlo sobre todo `scripts/`?
