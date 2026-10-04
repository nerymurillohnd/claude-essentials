---
paths:
  - "plugins/**/hooks/**"
  - "plugins/**/*.ts"
  - "plugins/**/*.js"
  - "docs/security-review.md"
---

# Mods (2.1.287+)

- Mods are JS or TS that run inside Claude Code without a sandbox.
- They see and rewrite prompts and tool calls, can approve calls a hook blocked, reach the network and spend the user's usage.
- The feature is young: 2.1.288 and 2.1.289 brought many fixes.
- An administrator can block mods through managed settings.
- A note above the prompt may come from a mod's band, or from the built-in `cc-plugin-you-should-know` mod, which is off by default and needs `/plugin enable cc-plugin-you-should-know@builtin`.
- Project policy: mods are accepted only if nothing else can do the job, with tests and with the `hooks:`/`calls:` lines attached in the PR.
