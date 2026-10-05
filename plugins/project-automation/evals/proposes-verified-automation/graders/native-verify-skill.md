---
type: llm
focus: last_message
---

The repository's history has six "fix lint errors after review" commits, and CLAUDE.md asks for lint and tests before every commit.

PASS if the response proposes a project skill named `verify` that runs the project's checks, or explicitly says Claude Code runs a project skill named `verify` before commits, as its answer to that problem.

FAIL if it addresses the problem only with a commit-blocking hook, a reminder in CLAUDE.md or a generic reviewer, without the `verify` skill.
