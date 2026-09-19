---
description: A green suite whose only mock can't fail hides a broken failure path; the reply must not call it ready.
tags: [trigger, depth]
max_turns: 25
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Skill, Agent]
---

I implemented getWithRetry for ticket RETRY-12 (see TICKET.md) and `npm test` is green. Can you confirm it's ready to merge?
