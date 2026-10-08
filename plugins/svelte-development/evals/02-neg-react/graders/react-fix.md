---
type: llm
---

PASS if the reply identifies the empty dependency array as the reason the effect never re-runs
for a new query, adds `query` to the dependencies, and handles stale responses (an ignore
flag, an AbortController or equivalent cleanup).
FAIL if it suggests Svelte, or misses the dependency array.
