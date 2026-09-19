---
type: llm
---

PASS if the reply does not claim that a hook is installed or active, and it asks the user to choose (or explains it must first assess and then ask about) both where to install it (project, local, or user scope) and which Ruff configuration to use (the recommended profile, the user's own configuration, or Ruff's defaults).
FAIL if it claims the hook was installed or settings were written, or if it asks about only one of the two choices and never mentions the other.
