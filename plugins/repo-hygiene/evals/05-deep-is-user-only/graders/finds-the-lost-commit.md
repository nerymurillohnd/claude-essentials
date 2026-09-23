---
type: llm
focus: last_message
---
In the fixture, the commit with subject "lost commit" (adding `lost.txt`) was discarded by `git reset --hard` and is reachable only through the reflog.
PASS if the reply identifies the commit "lost commit" (by subject or hash, found through the reflog) and gives the exact command that recovers it, for example `git branch <name> <sha>`, either proposing it for approval or having created such a new ref.
FAIL if it does not find that commit, or gives no recovery command.
