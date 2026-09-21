---
type: llm
focus: last_message
weight: 1
---
PASS if the answer provides a TypeScript function that groups an array of objects by the value of a given key, and the grouping logic is correct for the signature it declares.
FAIL if no function is given, if the code is not TypeScript, if it groups by something other than the given key, or if the answer deflects into Claude Code documentation instead of writing the function.
