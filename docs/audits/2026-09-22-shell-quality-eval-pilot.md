# Eval pilot — shell-quality 0.2.0 (`shell-hooks`)

**Date:** 2026-09-22 · **Status:** pilot (`--runs 1`), authorized by the maintainer as "Solo piloto $5";
the full suite (`--runs 3`) has not been run for 0.2.0.

**Command** (from the marketplace root, one invocation per case):

```bash
claude plugin eval plugins/shell-quality --trust-plugin --scaffold --ablation with-without \
  --runs 1 --case '<case>-*' --allow-tools Bash Write Edit \
  --model claude-sonnet-5 --judge-model claude-opus-5 --no-publish --max-cost-usd <cap>
```

Claude Code 2.1.278; agent `claude-sonnet-5`, judge `claude-opus-5`; `shell-quality` 0.2.0 loaded from
the working tree (confirmed by the runner's "Plugin under test" line).

| Case | With | Without | Δ | Judge votes (with / without) | Cost |
| --- | ---: | ---: | ---: | --- | ---: |
| `05-audits-before-proposing` | 1.00 | 0.50 | +0.50 | PASS PASS PASS / FAIL FAIL FAIL | $0.88 |
| `06-offers-choice-with-existing-config` | 1.00 | 0.50 | +0.50 | PASS PASS PASS / FAIL FAIL FAIL | $1.19 |
| `03-gate-asks-scope-and-mode` (first run) | 0.50 | 0.50 | 0.00 | FAIL FAIL FAIL / FAIL FAIL FAIL | $0.76 |
| `03-gate-asks-scope-and-mode` (rubric aligned to 0.2.0) | 1.00 | 1.00 | 0.00 | PASS PASS PASS / PASS FAIL PASS | $0.75 |

**Total measured cost:** $3.58.

## Reading

- `05` and `06`: the with-plugin arm reported the governing rc (the parent-folder rc in `05`, the
  project rc and its `disable=SC2086` in `06`) and offered the choices before writing anything; the
  baseline did not. The `writes-nothing-yet` grader passed in both arms, so the whole Δ comes from the
  audit-and-choice rubric.
- `03` first run: the with-plugin answer did what the 0.2.0 contract asks (audited every level, found
  nothing, recommended the profile at project level, asked before writing, and said it could not check
  the latest release without network instead of assuming). The rubric still demanded the 0.1.x flow —
  scope and mode asked together and the gate described in the first turn — which is more than the new
  contract requires (`SKILL.md`: one question at a time; the gate is explained before installing). The
  rubric was corrected to the contract, not softened: it still fails any write, any unchosen
  configuration or scope, and any unchecked prerequisite claim.
- `03` after the correction scores 1.00 in both arms: the base model also stops and asks, so the case is
  kept as a guard, not counted as uplift. The baseline's pass was 2–1, and in the first run the baseline
  was stopped by permissions rather than by choice; neither is evidence for the plugin.
- Cases `01`, `02` (`shell-lint`) and `04` (must not fire) were not re-run: this change does not touch
  `shell-lint`, and `04`'s grader is unchanged. The full three-run suite remains to be run.
