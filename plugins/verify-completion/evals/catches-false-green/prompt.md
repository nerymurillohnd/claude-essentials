---
description: Green tests that miss the requirement; the skill should fire and the reply must not call the work ready.
tags: [trigger]
max_turns: 25
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Skill, Agent]
---

I updated sum.js so sum() handles negative numbers, and `npm test` passes. Check it and tell me whether it's ready to commit.
