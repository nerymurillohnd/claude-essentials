# Evals — `ruff-quality`

Two skills, one flow each: **`ruff` fixes findings instead of silencing them and stays in scope;
`ruff-hooks` installs nothing before the user picks a scope and a mode.**

| Case | Skill | What it can fail at | Tools it needs to be able to fail |
| --- | --- | --- | --- |
| `01-fixes-instead-of-silencing` | `ruff` | Fixing the findings rather than adding `noqa` | `Write`/`Bash`, and the file is graded on disk |
| `02-asks-before-mass-reformat` | `ruff` | Not reformatting a whole codebase unasked | `Bash` |
| `03-gate-asks-scope-and-mode` | `ruff-hooks` | Stopping for both scope *and* mode, and describing the gate first | `Write`/`Edit` |
| `04-ignores-unrelated-request` | — | Not firing on a question with no Python in it | — |

## Running it

```bash
# from the marketplace root
claude plugin eval plugins/ruff-quality --ablation with-without \
  --allow-tools Bash Write Edit \
  --model claude-sonnet-5 --judge-model claude-opus-5 --no-publish --max-cost-usd 12
```

The judge is a different model from the agent on purpose: a model grading its own output prefers it.

Run results are not recorded here. They live in `results/` (git-ignored); a dated result worth
keeping goes to `docs/audits/`.

## Why the cases grant the tools they grant

A gated tool (`Bash`, `Write`, `Edit`, `WebFetch`, `mcp__*`) needs **two** grants, and the runner
refuses it unless it has both: the case must list it in `allowed_tools`, and the operator must pass
it in `--allow-tools` on the command line. A skill's own `allowed-tools` frontmatter counts for
neither — it only pre-approves permission prompts for tools already granted. Leave out the
`--allow-tools` flag and the runner prints `not granted … Bash, Write, Edit` and every file grader
in that case fails at 0 in both arms.
So every grader that asserts something was *not* done (no settings written, no bypass run, no
suppression added) is only meaningful if the run could have done it: those cases grant `Write`,
`Edit` and `Bash` deliberately. Both arms receive them, which makes each delta conservative.

## Sandbox environment

Each run executes in a throwaway sandbox with a synthetic `HOME`. `PATH` is inherited verbatim, but
entries under your real home directory do not resolve — so `ruff`, installed at `~/.local/bin/ruff`,
is **absent inside a run** even though it is on your machine (measured 2026-09-20). `03` therefore usually exercises the fail-closed path (the gate refuses to
install without `ruff`), which its rubric accepts as correct — that is the contract, not a failure.

Ruff's own configuration discovery also differs: outside a project, Ruff picks up
`~/.config/ruff/ruff.toml`, so "passes `ruff check` clean" is not a stable bar across machines.
`01` is graded against the two findings in the snippet itself, never against a clean exit code.

## CI policy

- **Always, required:** `claude plugin validate --strict` (`make validate-cli`).
- **Conditional, never blocking:** `evals.yml` runs `claude plugin eval` for this plugin
  only when the pull request changes one of its runtime files (`.claude-plugin/**`,
  `skills/**`, `agents/**`, `commands/**`, `hooks/**`, `scripts/**`, `.mcp.json`,
  `.lsp.json`, …), the same classification that decides a version bump. A change under
  `evals/**`, `README.md`, `CHANGELOG.md`, `LICENSE` or `docs/**` never selects it.
- **Never in CI:** `claude plugin eval init`.
- The job uploads the aggregate JSON and `report.html` as workflow artifacts, skips when
  `ANTHROPIC_API_KEY` is absent, and is never a required check; `results/` stays git-ignored.
