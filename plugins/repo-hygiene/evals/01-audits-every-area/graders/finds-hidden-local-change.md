---
type: llm
focus: last_message
---
In the fixture, `work/app.txt` carries the assume-unchanged index flag and has a local edit that `git status` does not show.
PASS if the report identifies that `app.txt` has a local change hidden from `git status` by the assume-unchanged (or skip-worktree) flag.
FAIL if it does not mention this hidden change. Other findings neither help nor hurt this grader.
