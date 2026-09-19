# Distrust the green: false-positive vectors

A green check means "nothing this check looks at went wrong". Gate 4 asks what
the check doesn't look at. Examine the vectors that fit the work, record each
one you checked and its result, and treat any hit as a gate failure until it's
explained.

## Checks that were switched off or softened

Search the diff first; that's where a weakening hides.

| Vector | How to look |
| --- | --- |
| Skipped or focused tests | `git diff` for `.skip`, `xit`, `xdescribe`, `.only`, `fit`, `@pytest.mark.skip`, `@Disabled`, `t.Skip`, `#[ignore]`, `pending` |
| Deleted or emptied tests | `git diff --stat` for removed test files; tests whose assertions were removed |
| Loosened assertions | exact matches turned into `toContain`, `toBeTruthy`, `assert x` without a value, wider tolerances, updated snapshots nobody reviewed |
| Lint, type, or format rules relaxed | `eslint-disable`, `biome-ignore`, `# noqa`, `# type: ignore`, `@ts-ignore`, `@ts-expect-error`, `// nolint`, `shellcheck disable`, rules removed from config |
| Thresholds lowered | coverage minimums, performance budgets, `--max-warnings`, allowed-failure flags in CI |
| Hooks or gates bypassed | `--no-verify`, `HUSKY=0`, `SKIP=`, `continue-on-error: true`, `if: false`, `when: never`, `allow_failure: true` |
| Checks not run at all | a command that exits 0 because it matched no files, no tests collected ("0 tests", "no tests ran"), a filter that excluded the new code |

## Failures that were silenced

| Vector | How to look |
| --- | --- |
| Swallowed errors | empty `catch`, `except: pass`, `.catch(() => {})`, `\|\| true`, `2>/dev/null` on a command whose failure matters, `set +e` |
| Ignored exit codes | pipelines without `pipefail`, `;` instead of `&&`, a wrapper script that always exits 0 |
| Warnings mistaken for success | deprecation or "falling back to" messages in the output that you didn't read |
| Partial success reported as success | batch jobs, migrations, or deploys that report per-item failures in a log but exit 0 |

## Tests that prove nothing

Whether the tests that ran actually test the requirement (assertions that
restate the implementation, happy-path-only suites, mocks that can't fail) is
the depth audit in [depth-audit.md](depth-audit.md).

## Wrong target

| Vector | How to look |
| --- | --- |
| Stale artifacts | build output, generated code, compiled assets, or caches older than the last edit; rebuild before judging |
| Wrong environment | tests ran against a local stub, a different config, a different database, or a different Node/Python version than the target |
| Wrong path | the command exercised a sibling function, an old endpoint, a feature flag's other branch, or a fixture instead of real data |
| Unsaved or uncommitted state | the check ran on files that aren't what will be committed or deployed (untracked files, a dirty submodule, an unstaged hunk) |

## When there are no tests

"No tests failed" is not evidence when there are no tests. Then gate 4 is about
what you used instead: running the program, reading the output, calling the
endpoint, rendering the page. State which, and why it covers the requirement.
