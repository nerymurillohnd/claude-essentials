---
type: llm
---

PASS if the corrected code removes the unused imports and the unused variable, replaces the bare `except:` with a specific exception, compares `verbose` without `== True`, and reads the file with a context manager or `pathlib`, and the reply adds no `# noqa`, `# ruff: noqa`, `# ruff: ignore`, or configuration change to silence a rule.
FAIL if it silences any finding with a suppression comment or a configuration change, or leaves the bare `except:` in place.
