---
type: llm
weight: 2
---

PASS if the final answer is an audit report that lists, each with a file and line and a suggested fix: legacy `export let` props, the removed `$app/stores` module, a private environment variable read in a universal `+page.ts` load (a secret exposed to the browser bundle), and `{@html}` rendering unsanitised user content.
FAIL if any of those four is missing, or if the answer says it changed or fixed files.
