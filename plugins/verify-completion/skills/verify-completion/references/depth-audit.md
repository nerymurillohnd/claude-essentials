# Depth audit: tests, mocks, validators, edge cases

A green suite is suspicious until you've inspected what it asserts and what it
leaves out. [false-green.md](false-green.md) finds checks that were switched off,
silenced, or pointed at the wrong target. This file asks the harder question:
do the checks that *did* run prove the behavior the user asked for?

It applies to any language or stack. Don't tick every row on every change:
pick the rows that apply to what changed, check them, and give the rest a
one-line reason ("no network code in this change"). A row you skip with no
reason counts as a gap, not as `N/A`.

## 1. Audit the tests (gate 4)

Read the tests that cover the change; don't just run them.

| Look for | Why it's a false green |
| --- | --- |
| Assertions that restate the implementation (snapshot of current output, expected value computed the same way as the code) | They prove the code does what it does, not what was asked |
| Only the happy path: no negative, malformed, or boundary case | Half the contract is untested |
| Failure paths left out: timeout, retry, concurrency, cancellation, partial failure, permission errors | These are where production breaks |
| Would it still pass if the change were reverted or the function emptied? | Then it doesn't test the change |
| Weak assertions: `toBeTruthy`, "no exception thrown", checking type but not value, counting calls without checking arguments | Almost any output passes |
| Test names that promise more than the body checks | A reviewer trusts the name |

## 2. Deconstruct mocks and simulations (gate 4)

Treat every mock, stub, fixture, fake client, and simulated environment as a
suspect until it's shown to be realistic.

| Ask | A bad answer means |
| --- | --- |
| Does it behave like the real dependency, including its errors? | The real integration is untested |
| Can it fail: errors, latency, timeouts, malformed or partial responses? | Failure handling is never exercised |
| Does it keep state the way the real thing does (ordering, persistence, idempotency)? | State bugs are invisible |
| Does it accept inputs the real dependency would reject? | The mock approves impossible states |
| Does it skip authentication, validation, serialization, filesystem, or network behavior? | The layer most likely to break is simulated away |
| Is the thing under test itself mocked? | Nothing real ran |

When a mock can't be trusted, say what a real run would add, and prefer one
check against the real dependency (a local instance, a sandbox, a dry run)
over another mocked test.

## 3. Validate the validators (gate 3)

When the change adds or relies on a schema, guard, parser, serializer, or
validation utility, show that it rejects what it should. Run it or its tests
with each input that applies:

| Input | Expected |
| --- | --- |
| A required field missing | Rejected, with an error naming the field |
| An unexpected or dangerous extra field (`__proto__`, `constructor`, admin flags) | Rejected or stripped, where the contract says so |
| The wrong type (string for number, object for array) | Rejected |
| A malformed nested structure | Rejected at the right level |
| Empty string, empty array, `null`, `undefined`, zero where they're invalid | Rejected |
| Duplicate keys, broken references, an invalid URL or date | Rejected |
| Types and runtime validation that disagree (a TypeScript type the schema doesn't enforce, a DB column the model allows) | Named as schema drift |

## 4. Edge-case matrix (gate 5)

For each meaningful change, run or reason through the rows that apply. Record
the ones you exercised and how.

| Area | Cases | Applies when the change… |
| --- | --- | --- |
| Input shape | empty, null/undefined, malformed, wrong primitive type, missing or extra fields, wrong nesting | takes input from users, files, APIs, or other modules |
| Size and bounds | minimum, maximum, off-by-one, very large input, duplicates, unexpected order | loops, paginates, slices, sorts, or limits |
| Text | Unicode, emoji, combining marks, encoding, line endings, whitespace-only | handles strings users or files provide |
| Failure | network failure, timeout, retry exhaustion, partial response, permission denied, missing file or directory | calls anything outside the process |
| Concurrency and repetition | concurrent execution, races, repeated or interrupted runs, non-idempotent operations | writes state, runs in parallel, or can be retried |
| Environment | missing environment variables, a different working directory, platform differences, environment-specific values committed as constants | reads config, paths, or the environment |
| Boundaries | server/client or trust boundaries crossed, serialization round-trips, secrets reaching logs or errors | sends data between processes, to the browser, or to logs |
| Modules and builds | import/export mismatches, module resolution, tree-shaking removing side effects, generated code out of date | changes exports, packaging, or build config |
| Shell scripts | missing `set -euo pipefail` where it's safe, pipelines that mask failures, unquoted variables, unsafe globs, `cd` without a check | adds or changes shell code |

## What the record should show

- **Gate 3:** each validator input you tried and what it returned.
- **Gate 4:** the tests and mocks you inspected, and what you found (including
  "the mock for X can't fail, so the retry path is untested").
- **Gate 5:** the matrix rows you exercised, with commands or test names, and
  the rows you skipped with their reason.

A gap you found and couldn't close within the task is a `FAIL` or `BLOCKED`
with that exact gap, and the verdict is `NOT VERIFIED`.
