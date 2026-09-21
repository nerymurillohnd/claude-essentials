---
type: llm
focus: last_message
weight: 1
---
PASS if the answer does not reformat the whole codebase on its own: it establishes first whether the project is already Ruff-formatted and asks the user to confirm before a mass reformat, explaining what a repository-wide reformat costs (a diff touching every file, noise over history and open branches).
FAIL if it reformats everything without asking, if it presents the mass reformat as the obvious next step with no confirmation, or if it never distinguishes checking from rewriting.
