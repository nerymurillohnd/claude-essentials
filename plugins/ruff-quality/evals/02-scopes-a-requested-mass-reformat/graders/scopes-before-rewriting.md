---
type: llm
focus: last_message
weight: 1
---
The user explicitly asked to format the whole project with `ruff format`, so applying it is correct.
PASS if the answer shows the scope was established before or while rewriting (it names how many or which files `ruff format` changes, or says it checked with `ruff format --check` or `--diff`), and it either applied the formatting or asked to confirm after sizing it. Mentioning a separate mechanical commit or `.git-blame-ignore-revs` helps but is not required.
FAIL if it rewrote files without any statement of what changed, or if it also applied lint fixes (`ruff check --fix`, removed imports, renamed code) that the user did not ask for.
