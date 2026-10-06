---
type: llm
---

PASS if the answer names src/routes/+page.svelte (it calls `counter.reset()`) and src/lib/counter.svelte.ts (the Counter class would no longer satisfy the Resettable interface from src/lib/resettable.ts, which declares `reset`).
FAIL if either file is missing, if an unrelated file is listed, or if the answer says nothing would break.
