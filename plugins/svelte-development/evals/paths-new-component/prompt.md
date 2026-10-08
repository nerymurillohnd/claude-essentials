---
description: With no project files, asking for a new .svelte file must still bring the Svelte rules (docs before writing, autofixer after, Svelte 5 syntax), the case the skills' paths frontmatter targets.
runs: 2
max_turns: 25
allowed_tools:
  [
    Read,
    Glob,
    Grep,
    Skill,
    Write,
    Edit,
    "mcp__plugin_svelte-development_svelte__*",
  ]
---

Create src/lib/Disclosure.svelte: a button with a `title` that shows or hides its content. The parent can bind whether it is open and passes the content to show.
