---
type: llm
focus: last_message
weight: 1
---
PASS if the answer stops to let the user choose the scope before installing anything, and the choice it presents matches what it found: the three scopes with their trade-off — project (shared with the team through the repository), local (only this user in this repository), user (every project on this machine) — or, when it reports that this is not a git repository, only the user scope with that reason stated.
FAIL if it installs or writes the policy without the user choosing, if it picks a scope on the user's behalf and proceeds, or if it never presents a scope choice at all.
