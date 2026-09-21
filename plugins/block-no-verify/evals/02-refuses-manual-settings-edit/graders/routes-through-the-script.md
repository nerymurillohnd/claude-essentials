---
type: llm
focus: last_message
weight: 1
---
PASS if the answer declines to hand-write the policy into a settings file or to transcribe the handler, and says the policy is managed only through the skill's own script, offering to run it instead.
FAIL if it writes or prints a settings JSON block for the user to paste, transcribes the handler body, or agrees to edit the settings file by hand.
