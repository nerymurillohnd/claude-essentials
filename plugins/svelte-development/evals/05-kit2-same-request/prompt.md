---
description: "Kit 2 project: detects the old major and proposes the migration before writing."
runs: 3
max_turns: 15
timeout_seconds: 300
allowed_tools:
  [Read, Glob, Grep, Edit, Write, Bash, LSP, Skill, ToolSearch, TodoWrite]
---

Make the /items/[id] route only match numeric ids.
