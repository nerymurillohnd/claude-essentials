---
description: A migration question triggers the ruff skill and gets the current pre-commit hook ids and order.
tags: [trigger]
max_turns: 8
allowed_tools: [Read, Glob, Grep, Skill]
---

Our repo formats Python with black and sorts imports with isort, both in .pre-commit-config.yaml. How do I replace them with Ruff? Show the pre-commit config I should end up with.
