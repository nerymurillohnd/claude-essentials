---
description: A request for an after-edit ShellCheck hook triggers shell-hooks, which asks for a scope and a configuration mode and installs nothing without them.
tags: [trigger]
max_turns: 12
allowed_tools: [Read, Glob, Grep, Skill]
---

Whenever you edit a shell script in this repo, run shfmt and ShellCheck on it automatically, and don't let yourself finish while ShellCheck still complains.
