# Evals — `shell-quality`

One skill and one hook, measured together: **`shell-lint` fixes findings instead of disabling
them and protects the project's configuration, and whatever ShellCheck still reports after the
hook formats a script is fixed in the script.**

| Case | What it can fail at | Tools it needs to be able to fail |
| --- | --- | --- |
| `01-fixes-instead-of-disabling` | Fixing SC findings rather than adding a `shellcheck disable` | `Write`/`Bash`, and the file is graded on disk |
| `02-flags-editorconfig-conflict` | Warning that *any* shfmt style flag makes shfmt ignore EditorConfig entirely | `Bash` |
| `03-fixes-what-the-hook-reports` | Fixing the SC2086 and SC2164 the hook reports after an unrelated edit, without a directive, an rc or `SHELLCHECK_OPTS` | `Write`/`Edit`/`Bash`; a scaffold seeds the script and project-level tools |
| `04-ignores-unrelated-request` | Not firing on a question with no shell in it | — |

## Running it

```bash
# from the marketplace root
claude plugin eval plugins/shell-quality --ablation with-without --scaffold \
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

Each run executes in a throwaway sandbox with a synthetic `HOME`, but `PATH` is inherited and
Homebrew binaries resolve: `shellcheck`, `shfmt`, `jq` and `git` are **present inside a run** on a
Mac with Homebrew (measured 2026-09-20 at `/opt/homebrew/bin`). `03` does not rely on that: its
`scaffold.sh` (written for this suite) copies the marketplace's own `.venv/bin/shellcheck` and
`.venv/bin/shfmt` into the case project's `.venv/bin/`, where the hook finds a project-level install.
Run the suite with `--scaffold`; without it `03` starts in an empty workspace and measures nothing.

`01` and `03` are graded against the specific findings in their snippets, never against a clean
ShellCheck exit code, which would depend on whichever `.shellcheckrc` the run happens to discover.

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
