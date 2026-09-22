# Eval record — Block No Verify (`block-no-verify`)

**Date:** 2026-09-20 · **Status:** archived record, not a current measurement

This file holds the eval table that used to sit in
[`plugins/block-no-verify/README.md`](../../plugins/block-no-verify/README.md). R9 moved it here:
a score in a README goes stale the moment a model, a prompt or a grader changes, and
a stale score is worse than none. Results now live in the pull request that measured
them, and the suite itself is [`plugins/block-no-verify/evals/`](../../plugins/block-no-verify/evals/).

**Superseded case names:** ``protect-hooks-request``, ``ignores-git-read``.
The suite was rewritten on 2026-09-20; the cases it ships today are numbered
(`01-…`, `02-…`) and none of the names below resolves to a directory any more.

## The table as the README carried it

**Behavioral evals** — [`evals/`](evals/) runs with `claude plugin eval`, which compares a
run with the plugin against a baseline without it:

| Case | Checks | With | Without | Δ | Last run |
| --- | --- | ---: | ---: | ---: | --- |
| `protect-hooks-request` | Skill fires on a natural protection request, asks for a scope, and writes no settings (the case grants no shell, so it tests the gate's wording, not an install) | — | — | — | Pending re-measurement — the skill descriptions changed in this version |
| `ignores-git-read` | Skill does **not** fire on a read-only Git question | — | — | — | Pending re-measurement — the skill descriptions changed in this version |
