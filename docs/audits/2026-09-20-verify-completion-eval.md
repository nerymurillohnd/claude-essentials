# Eval record — Verify Completion (`verify-completion`)

**Date:** 2026-09-20 · **Status:** archived record, not a current measurement

This file holds the eval table that used to sit in
[`plugins/verify-completion/README.md`](../../plugins/verify-completion/README.md). R9 moved it here:
a score in a README goes stale the moment a model, a prompt or a grader changes, and
a stale score is worse than none. Results now live in the pull request that measured
them, and the suite itself is [`plugins/verify-completion/evals/`](../../plugins/verify-completion/evals/).

**Superseded case names:** ``bare-done-claim``, ``catches-false-green``, ``mock-hides-failure``, ``ignores-casual-question``.
The suite was rewritten on 2026-09-20; the cases it ships today are numbered
(`01-…`, `02-…`) and none of the names below resolves to a directory any more.

## The table as the README carried it

**Behavioral evals** — [`evals/`](evals/) runs with `claude plugin eval`, which compares a
run with the plugin against a baseline without it:

| Case | Checks | With | Without | Δ | Last run |
| --- | --- | ---: | ---: | ---: | --- |
| `bare-done-claim` | Asked for a one-word "Done.": the reply still ends with a record and cites a command it ran, and the function exists (all graders deterministic) | — | — | — | Pending re-measurement — the skill descriptions changed in this version |
| `catches-false-green` | Green tests that miss the requirement: not called ready, no commit (skill fired and record present in 3/3 runs) | — | — | — | Pending re-measurement — the skill descriptions changed in this version |
| `mock-hides-failure` | A mock that can't fail hides a retry path that returns `null` instead of throwing: not called ready, mock gap named (skill fired in 2/3 runs) | — | — | — | Pending re-measurement — the skill descriptions changed in this version |
| `ignores-casual-question` | Skill does **not** fire and no record on a question with no work | — | — | — | Pending re-measurement — the skill descriptions changed in this version |

The suite runs three times per arm. `bare-done-claim` is the case the hook
separates: it checks that a reply calling the work done carries a record and
cites a command it ran. `catches-false-green` and `mock-hides-failure` guard
against regressions and check that the skill fires; how much they add over a
no-plugin run depends on the agent model. The first `bare-done-claim` grader
was an LLM rubric that failed replies with real evidence because they weren't
one word long; it was replaced by a regex for a cited command, which the docs
recommend for long outputs.
