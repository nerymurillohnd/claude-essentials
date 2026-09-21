---
max_turns: 25
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Skill, Agent, Bash, WebFetch]
runs: 3
---
Quiero que un hook `PreToolUse` bloquee una llamada a herramienta. ¿Qué tiene que devolver exactamente el hook para que Claude Code no ejecute esa llamada?
