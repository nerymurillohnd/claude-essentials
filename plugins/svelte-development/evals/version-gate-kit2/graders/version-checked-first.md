---
type: llm
focus: trace
arm: both
---

PASS if, before writing or proposing any code, the agent found the installed SvelteKit version: it read package.json, ran npm ls, or printed package.json with a shell command.
FAIL if it wrote or proposed code before looking at the installed version, or never looked.
