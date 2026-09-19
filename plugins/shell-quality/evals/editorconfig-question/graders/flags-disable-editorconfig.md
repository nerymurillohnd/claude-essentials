---
type: llm
---

PASS if the reply explains that passing a parser or printer flag such as `-s` makes shfmt ignore EditorConfig entirely, recommends running `shfmt -d` without style flags (moving `simplify = true` into .editorconfig if simplification is wanted), and shows a pre-commit hook for shfmt without style arguments.
FAIL if it says flags merely override individual EditorConfig keys, or recommends keeping `-s` or `-i` flags alongside EditorConfig.
