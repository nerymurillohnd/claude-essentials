# Eval record — Agent Self-Knowledge (`agent-self-knowledge`)

**Date:** 2026-09-20 · **Status:** archived record, not a current measurement

This file holds the eval table that used to sit in
[`plugins/agent-self-knowledge/README.md`](../../plugins/agent-self-knowledge/README.md). R9 moved it here:
a score in a README goes stale the moment a model, a prompt or a grader changes, and
a stale score is worse than none. Results now live in the pull request that measured
them, and the suite itself is [`plugins/agent-self-knowledge/evals/`](../../plugins/agent-self-knowledge/evals/).

**Superseded case names:** ``triggers-on-settings-question``, ``ignores-unrelated-request``.
The suite was rewritten on 2026-09-20; the cases it ships today are numbered
(`01-…`, `02-…`) and none of the names below resolves to a directory any more.

## The table as the README carried it

**Behavioral evals** — [`evals/`](evals/) runs with `claude plugin eval`, which compares a
run with the plugin against a baseline without it:

| Case | Checks | With | Without | Δ | Last run |
| --- | --- | ---: | ---: | ---: | --- |
| `triggers-on-settings-question` | Skill fires on natural phrasing, names `worktree.baseRef`, quotes the documentation sentence verbatim and cites it | 1.00 | 0.00 | +1.00 | 2026-09-20, Claude Code 2.1.278, `claude-sonnet-5` agent and judge, 3 runs per arm |
| `ignores-unrelated-request` | Skill does **not** fire on unrelated work | 1.00 | 1.00 | 0.00 | 2026-09-20, Claude Code 2.1.278, `claude-sonnet-5` agent and judge, 3 runs per arm |

The skill invoked itself unprompted in all three `triggers-on-settings-question`
runs. There is **no eval for the bounded-negative protocol**: the case written
for it rested on a premise that turned out to be false (see Limitations), and no
replacement question has been verified absent from both the published
documentation and the settings schema Claude Code ships. DEBT-0023 tracks it.
