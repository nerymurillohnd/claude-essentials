---
type: llm
focus: last_message
weight: 1
---
PASS if the answer states that a PreToolUse hook blocks a tool call by returning `permissionDecision` set to `"deny"` inside a `hookSpecificOutput` object (naming exiting with code 2 as an equivalent route is fine and does not fail the case).
FAIL if it says to use the top-level `decision` or `reason` fields, which are deprecated for this event; if it invents a field name that is not `hookSpecificOutput`, `permissionDecision`, `permissionDecisionReason`, `updatedInput` or `additionalContext`; or if it never names the field that carries the decision.
