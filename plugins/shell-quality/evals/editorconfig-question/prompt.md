---
description: A formatting-configuration question triggers shell-lint and gets the EditorConfig rule right.
tags: [trigger]
max_turns: 8
allowed_tools: [Read, Glob, Grep, Skill]
---

Our .editorconfig sets indent_size = 2 for shell scripts, but in CI we run `shfmt -s -d .` and it complains about tabs. Why, and what should the CI command and pre-commit hook look like?
