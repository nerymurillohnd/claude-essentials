# Evals — `ruff-quality`

One skill and one hook, measured together: **`ruff` fixes findings instead of silencing them and
stays in scope, and whatever Ruff still reports after the hook's safe fixes is fixed in the code.**

| Case | What it can fail at | Tools it needs to be able to fail |
| --- | --- | --- |
| `01-fixes-instead-of-silencing` | Fixing the findings rather than adding `noqa` | `Write`/`Bash`, and the file is graded on disk |
| `02-asks-before-mass-reformat` | Not reformatting a whole codebase unasked | `Bash` |
| `03-fixes-what-the-hook-reports` | Fixing the E741 and F821 the hook reports after an unrelated edit, without a suppression or a `[tool.ruff]` change | `Write`/`Edit`/`Bash`; a scaffold seeds the project and a project-level Ruff |
| `04-ignores-unrelated-request` | Not firing on a question with no Python in it | — |

## Running it

```bash
# from the marketplace root
claude plugin eval plugins/ruff-quality --ablation with-without --scaffold \
  --allow-tools Bash Write Edit \
  --model claude-sonnet-5 --judge-model claude-opus-5 --no-publish --max-cost-usd 15
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
is **absent inside a run** even though it is on your machine (measured 2026-09-20). The plugin's
hook then says Ruff is not installed and does nothing, which is its contract, not a failure.
`03` needs the hook to run, so its `scaffold.sh` (written for this suite) copies the marketplace's
own `.venv/bin/ruff` into the case project's `.venv/bin/`, where the hook finds a project-level
install. Run the suite with `--scaffold`; without it `03` starts in an empty workspace and
measures nothing.

Ruff's own configuration discovery also differs: outside a project, Ruff picks up the user-level
`ruff.toml`, which the synthetic `HOME` hides. `01` and `03` are graded against the specific
findings in their snippets, never against a clean exit code.

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
