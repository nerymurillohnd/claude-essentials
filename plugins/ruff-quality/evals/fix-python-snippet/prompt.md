---
description: Cleaning up Python code triggers the ruff skill, which fixes the code instead of silencing findings.
tags: [trigger]
max_turns: 8
allowed_tools: [Read, Glob, Grep, Skill]
---

Clean up this function so it would pass a strict Ruff setup. Reply with the corrected code and a one-line note per change; don't run anything.

```python
import os, sys
def load(path, verbose=False):
    try:
        data = open(path).read()
    except:
        return None
    unused = 1
    if verbose == True:
        print("loaded %s" % path)
    return data
```
