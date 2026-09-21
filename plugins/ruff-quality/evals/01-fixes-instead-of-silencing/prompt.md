---
max_turns: 20
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Skill, Bash, Write, Edit]
runs: 3
---
Corrige lo que Ruff reporta en este código y déjalo en un archivo llamado `app.py`:

```python
import os
import sys

def get_name(user):
    if user.get("name") != None:
        return f"{user['name']}"
    return 'anonymous'
```
