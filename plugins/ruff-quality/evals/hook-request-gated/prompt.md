---
description: A request for an after-edit Ruff hook triggers ruff-hooks, which asks for a scope and a configuration mode and installs nothing without them.
tags: [trigger]
max_turns: 12
allowed_tools: [Read, Glob, Grep, Skill]
---

Set things up so that every time you edit a Python file here, Ruff lints and formats it, and you can't finish while Ruff errors remain.
