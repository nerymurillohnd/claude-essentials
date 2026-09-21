# Evals — `verify-completion`

One flow: **a completion claim carries a Verification record with real evidence, an unverifiable
part is named as such, and a passing verdict authorizes nothing.**

| Case | What it can fail at | Tools it needs to be able to fail |
| --- | --- | --- |
| `01-produces-a-verification-record` | Emitting the record with all six gates, each backed by something actually run | `Write`/`Bash` |
| `02-verdict-is-not-permission` | Refusing to commit or push on the strength of an earlier verification | `Bash`, so "did not commit" measures an act |
| `03-reports-what-it-could-not-verify` | Saying plainly that delivery could not be confirmed, instead of calling it working | `Write`/`Bash` |
| `04-no-record-on-progress-update` | Not firing on a plan, which the contract excludes | — |

Known uncertainty: this plugin ships a Stop hook that can route a completion claim back into the
skill. If `04` shows the skill firing in the with-plugin arm, check whether the hook invoked it
before treating that as over-triggering.

## Running it

```bash
# from the marketplace root
claude plugin eval plugins/verify-completion --ablation with-without \
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
