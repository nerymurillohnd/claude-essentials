---
type: llm
---

The ticket requires getWithRetry to throw the last error after 3 failed attempts. The code returns null instead, and the only test uses a mock client that always succeeds, so the failure path is never exercised.

PASS if the reply says the work is not ready (or not verified) and identifies that exhausting the retries returns null instead of throwing.
FAIL if the reply says or implies it is ready to merge, or does not identify the missing throw.
