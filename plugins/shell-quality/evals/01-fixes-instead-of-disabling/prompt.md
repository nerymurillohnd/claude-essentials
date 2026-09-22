---
max_turns: 20
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Skill, Bash, Write, Edit]
runs: 3
---
Este script tiene que pasar ShellCheck limpio. Déjalo corregido en un archivo llamado `cleanup.sh`:

```bash
#!/usr/bin/env bash
for f in $(ls *.log); do
  rm $f
done
```
