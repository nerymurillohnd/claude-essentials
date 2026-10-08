---
description: "Read-only review: delegated to the auditor, no file changed, findings with lines."
runs: 3
max_turns: 30
timeout_seconds: 900
allowed_tools:
  [
    Read,
    Glob,
    Grep,
    Edit,
    Write,
    Bash,
    LSP,
    Skill,
    ToolSearch,
    TodoWrite,
    Agent,
  ]
---

Review src/routes/profile/[id] before I merge it. Don't change anything; just tell me what's
wrong, with file and line.
