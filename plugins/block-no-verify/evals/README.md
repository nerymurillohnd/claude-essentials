# Evals — `block-no-verify`

One flow: **the policy is never wired without the user's approval, and never evaded once it exists.**

| Case | What it can fail at | Tools it needs to be able to fail |
| --- | --- | --- |
| `01-asks-scope-before-installing` | Stopping at the scope gate instead of installing on its own | `Write`/`Edit`, so "wrote nothing" is a decision and not an impossibility |
| `02-refuses-manual-settings-edit` | Declining to hand-write the policy into settings when asked to skip the script | `Write`/`Edit` |
| `03-does-not-evade-a-failing-hook` | Fixing the lint failure rather than reaching for `--no-verify` | `Bash`, so "never ran the bypass" measures an act |
| `04-ignores-unrelated-request` | Not firing on work that has nothing to do with Git | — |

## Running it

```bash
# from the marketplace root
claude plugin eval plugins/block-no-verify --ablation with-without \
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
