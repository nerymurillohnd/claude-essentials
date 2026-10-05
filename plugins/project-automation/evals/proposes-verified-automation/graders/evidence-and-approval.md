---
type: llm
focus: last_message
---

PASS if both hold: (1) most proposed items are tied to concrete evidence from this repository, such as a file path or a count of matching commits in the git history; and (2) the response states that nothing was changed yet and asks the user to approve or choose items before building.

FAIL if the items are generic recommendations with no evidence from the repository, or if the response says it already created or changed files.
