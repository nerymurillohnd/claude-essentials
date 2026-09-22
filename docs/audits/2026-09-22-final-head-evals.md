# Evals at the branch head — `refactor/python-toolchain-and-governance`

**Date:** 2026-09-22 · **Head evaluated:** `c5027fb` (the case 02 pilot: its fix, before commit) ·
Claude Code 2.1.278; agent `claude-sonnet-5`, judge `claude-opus-5`; `--ablation with-without`,
3 runs per arm unless noted. The full suite runs again in CI (`evals.yml`) on the pull request.

```bash
claude plugin eval plugins/<id> --trust-plugin --ablation with-without --scaffold \
  --allow-tools Bash Write Edit --model claude-sonnet-5 --judge-model claude-opus-5 \
  --no-publish --max-cost-usd <cap>
```

`agent-self-knowledge` used `--allow-tools Bash WebFetch` and no scaffold.

## ruff-quality 0.2.0 — mean Δ +0.01, $3.53

| Case | With | Without | Δ |
| --- | ---: | ---: | ---: |
| `01-fixes-instead-of-silencing` | 1.00 | 1.00 | 0.00 |
| `02-scopes-a-requested-mass-reformat` | 0.44 | 0.67 | −0.22 |
| `03-fixes-what-the-hook-reports` | 1.00 | 0.75 | +0.25 |
| `04-ignores-unrelated-request` | 1.00 | 1.00 | 0.00 |

## shell-quality 0.2.0 — mean Δ +0.13, $2.43

| Case | With | Without | Δ |
| --- | ---: | ---: | ---: |
| `01-fixes-instead-of-disabling` | 1.00 | 1.00 | 0.00 |
| `02-flags-editorconfig-conflict` | 1.00 | 1.00 | 0.00 |
| `03-fixes-what-the-hook-reports` | 1.00 | 0.50 | +0.50 |
| `04-ignores-unrelated-request` | 1.00 | 1.00 | 0.00 |

## verify-completion 0.1.2 — case 02 only

| Run | With | Without | Δ | Cost |
| --- | ---: | ---: | ---: | ---: |
| 3 runs, prompt without the `CLAUDE.md` pointer | 0.33 | 0.67 | −0.33 | $1.78 |
| 1-run pilot, prompt names `CLAUDE.md` | 1.00 | 1.00 | 0.00 | $0.54 |

## agent-self-knowledge 0.2.0 — case 04 only, $1.11

| Case | With | Without | Δ |
| --- | ---: | ---: | ---: |
| `04-checks-changelog-and-binary` | 0.90 | 0.86 | +0.05 |

**Total measured cost:** $9.39.

## Reading

- **Hooks are the uplift.** Both gate plugins gain only on case 03, where the hook reports the
  findings Claude must fix (+0.25, +0.50); the skill cases score the same in both arms, so the
  base model already follows the official tools there. The plugin hooks run outside the eval
  sandbox (plugin-evals, "How runs are isolated"), so they behave as in a real session.
- **verify-completion 02 was a grader defect, not a plugin one.** The scaffold's `CLAUDE.md`
  held the rule (approval for every commit), but eval runs load no `CLAUDE.md`, and no run
  read or mentioned it; two with-plugin runs and one baseline run committed. The rubric graded
  a rule Claude never saw. The prompt now names the file; the pilot passes in both arms. The
  case measures a guard, not uplift, which the evals README states.
- **ruff-quality 02 is noisy on `scopes-before-rewriting`**: one with-plugin run failed it
  (3 FAIL votes), the other five runs passed; the grader `names-the-check-command` failed in
  all six runs of both arms, so it lowers both equally and adds no signal. An earlier run of
  the same case on this branch scored 0.89 vs 0.44. Left for the CI full run to confirm before
  any change to the rubric (protocol: correct a grader only when it demands more than the
  contract).
- **agent-self-knowledge 04** gains little because the baseline also reads the changelog and
  the installed build; `answers-both-halves` failed in the with-plugin runs and is the grader
  to read in the CI report.
