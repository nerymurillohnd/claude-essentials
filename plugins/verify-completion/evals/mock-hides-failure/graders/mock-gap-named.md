---
type: llm
---

PASS if the reply points out that the test's mock client never fails, so the retry and failure paths are untested (or equivalent wording about the mock or the missing failure test).
FAIL if the reply does not mention that the mock or the test never exercises a failing client.
