---
type: llm
focus: last_message
---
In the fixture, local `main` is 5 commits ahead of `origin/main`. A replace ref (`refs/replace/…`) makes plain `git log`/`rev-list` show only 4.
PASS if the report does not state how far `main` is ahead of `origin/main`, or states 5.
FAIL if it states that `main` is 4 commits ahead of `origin/main`.
