---
type: llm
focus: last_message
---
PASS if the reply explains that rebase replays commits on top of another base (rewriting their hashes) and advises against rebasing commits that others already have (shared or published history).
FAIL if either point is missing or the reply is about something else.
