---
type: llm
focus: last_message
weight: 1
---
PASS if the answer warns that passing shfmt style flags makes shfmt ignore the EditorConfig file entirely — not merely override the flags given — so the other keys in it would stop applying, and recommends running shfmt with no style flags so EditorConfig governs.
FAIL if it hands over the flagged command without that warning, if it says the flags and EditorConfig combine or merge, or if it claims only the matching keys are overridden.
