# Eval record — Ruff Quality (`ruff-quality`)

**Date:** 2026-09-20 · **Status:** archived record, not a current measurement

This file holds the eval table that used to sit in
[`plugins/ruff-quality/README.md`](../../plugins/ruff-quality/README.md). R9 moved it here:
a score in a README goes stale the moment a model, a prompt or a grader changes, and
a stale score is worse than none. Results now live in the pull request that measured
them, and the suite itself is [`plugins/ruff-quality/evals/`](../../plugins/ruff-quality/evals/).

**Superseded case names:** ``fix-python-snippet``, ``migrate-black-isort``, ``hook-request-gated``, ``ignores-concept-question``.
The suite was rewritten on 2026-09-20; the cases it ships today are numbered
(`01-…`, `02-…`) and none of the names below resolves to a directory any more.

## The table as the README carried it

**Behavioral evals** — [`evals/`](evals/) runs with `claude plugin eval`, which compares a
run with the plugin against a baseline without it:

| Case | Checks | With | Without | Δ | Last run |
| --- | --- | ---: | ---: | ---: | --- |
| `fix-python-snippet` | `ruff` fires when cleaning up Python and fixes findings instead of silencing them | — | — | — | Pending re-measurement — the skill descriptions changed in this version |
| `migrate-black-isort` | `ruff` fires on a migration question and gives current hook ids and order | — | — | — | Pending re-measurement — the skill descriptions changed in this version |
| `hook-request-gated` | `ruff-hooks` fires, asks for scope and mode, writes no settings (the case grants no shell, so it tests the gate's wording, not an install) | — | — | — | Pending re-measurement — the skill descriptions changed in this version |
| `ignores-concept-question` | Neither skill fires on a conceptual Python question | — | — | — | Pending re-measurement — the skill descriptions changed in this version |
