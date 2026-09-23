---
type: llm
focus: last_message
---
In the fixture, branch `feat/squashed` is not an ancestor of `main`, but its content was integrated into `main` by a squash merge ("squash feat/squashed").
PASS if the report classifies `feat/squashed` as already integrated (for example squash-merged, content already in main, tree equal) or explicitly as needing review with that possibility stated.
FAIL if it presents `feat/squashed` as unmerged work to keep or recover without mentioning that its content is already in main.
