# Eval record — Shell Quality (`shell-quality`)

**Date:** 2026-09-20 · **Status:** archived record, not a current measurement

This file holds the eval table that used to sit in
[`plugins/shell-quality/README.md`](../../plugins/shell-quality/README.md). R9 moved it here:
a score in a README goes stale the moment a model, a prompt or a grader changes, and
a stale score is worse than none. Results now live in the pull request that measured
them, and the suite itself is [`plugins/shell-quality/evals/`](../../plugins/shell-quality/evals/).

**Superseded case names:** ``fix-shell-snippet``, ``editorconfig-question``, ``hook-request-gated``, ``ignores-concept-question``.
The suite was rewritten on 2026-09-20; the cases it ships today are numbered
(`01-…`, `02-…`) and none of the names below resolves to a directory any more.

## The table as the README carried it

**Behavioral evals** — [`evals/`](evals/) runs with `claude plugin eval`, which compares a
run with the plugin against a baseline without it:

| Case | Checks | With | Without | Δ | Last run |
| --- | --- | ---: | ---: | ---: | --- |
| `fix-shell-snippet` | `shell-lint` fires when cleaning up a script and fixes findings instead of silencing them | — | — | — | Pending re-measurement — the skill descriptions changed in this version |
| `editorconfig-question` | `shell-lint` fires and explains that style flags disable EditorConfig | — | — | — | Pending re-measurement — the skill descriptions changed in this version |
| `hook-request-gated` | `shell-hooks` fires, asks for scope and mode, writes no settings (the case grants no shell, so it tests the gate's wording, not an install) | — | — | — | Pending re-measurement — the skill descriptions changed in this version |
| `ignores-concept-question` | Neither skill fires on a conceptual shell question | — | — | — | Pending re-measurement — the skill descriptions changed in this version |
