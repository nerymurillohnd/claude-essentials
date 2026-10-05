---
description: A Node.js service with a broken hook, unenforced CLAUDE.md rules and repeated manual commits; the plugin must propose evidence-backed, docs-verified automation and change nothing.
expected_outcome: A proposal that reports the broken hook, protects .env with rules that can work, prefers a project verify skill over a commit hook, cites evidence and asks for approval.
runs: 2
max_turns: 80
timeout_seconds: 1200
allowed_tools: [Read, Glob, Grep, Skill, Agent, TodoWrite]
---

Audit this repository and set up Claude Code automation (skills, hooks, subagents, whatever fits) that would make working on it faster and safer. Show me your proposal first; don't change anything yet.
