---
description: "Kit 3 project: version first, docs before code, src/params.ts, autofixer, project check."
tags: [pilot]
runs: 3
max_turns: 40
timeout_seconds: 900
allowed_tools:
  [Read, Glob, Grep, Edit, Write, Bash, LSP, Skill, ToolSearch, TodoWrite]
---

Add a page at /products/[id] that shows the product id, and make the route only match
numeric ids, so /products/abc is a 404. Make the change yourself in this session rather than handing it off.
