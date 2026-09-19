---
type: llm
---

PASS if the proposed pre-commit configuration uses the `astral-sh/ruff-pre-commit` repository with the hook ids `ruff-check` (with `--fix`) and `ruff-format`, lists `ruff-check` before `ruff-format`, removes black and isort, and says the `rev` must match the project's Ruff version or be looked up rather than guessed.
FAIL if it uses the legacy hook id `ruff` without mentioning `ruff-check`, puts the formatter before the linter, or keeps black or isort running alongside Ruff.
