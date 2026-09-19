---
name: verify-completion
description: Use right before telling the user that work is complete, fixed, working, verified, or ready to commit, open a PR, review, hand off, or deploy, and when the user asks whether it is really done ("is it done?", "does it actually work?", "verify before you tell me it's ready", "¿ya quedó?", "¿funciona de verdad?", "¿está listo para el PR?", "verifica antes de decirme que está listo"). Also use it when a verify-completion Stop hook reports a completion claim without a valid Verification record. Runs six evidence gates and ends with a Verification record. Not for intermediate steps, progress updates, plans, or conceptual questions about code or tools. A passing record never authorizes a commit, push, publish, or deploy.
---

# Verify completion

"Done" is a claim about the world, and a claim needs evidence. This skill is
the last layer before telling the user that work is finished: formatters,
linters, tests, reviewers, and Git guards have already had their say; this
checks that the conclusion drawn from all of them is honest.

Two rules frame everything below:

- **Verification is not permission.** Passing every gate authorizes nothing.
  Committing, pushing, opening or merging a PR, publishing, deploying, sending,
  or changing anything permanently still needs the user's own approval, under
  whatever rules the project already has. Never treat a VERIFIED verdict as
  that approval, and never bypass, disable, or weaken a check to reach one.
- **"I couldn't verify X" is a valid result; an unbacked "done" is not.** When
  a gate can't be completed (no way to run it, missing access, missing
  evidence), say exactly that, and don't call the work done.

## When to run it

Run it at the moment of the claim: the reply you are about to send says, or
lets the user conclude, that the work is complete, correct, fixed, verified,
passing, or ready for the next step (commit, PR, review, handoff, release).

Don't run it for intermediate steps, exploratory work, a plan, a question, or a
progress update that makes no completion claim. In a long task, run it once, at
the end, over everything that's being handed over.

If the verify-completion Stop hook sent you here, the reply you just wrote made
such a claim. Either run the gates, or rewrite the reply without the claim if
the claim wasn't intended. In a progress update that ends a turn, describe the
state ("step 1 changes made, not verified yet") instead of using completion
words like "done" or "listo".

## Before the gates

1. **State the requirement.** Write down exactly what the user asked for, in
   their terms, including constraints ("without touching the public API",
   "in both languages"). Re-read the original request; don't reconstruct it
   from memory or from your own summary. For anything beyond a small change,
   reconstruct the full intent with
   [references/coherence-audit.md](references/coherence-audit.md) §1: what
   should now differ, what must stay the same, and what risks it added.
2. **Inventory what the claim depends on:** changed files (`git status`,
   `git diff --stat`), the commands that prove behavior (tests, build, lint,
   type check, the app itself), consumers of the changed code, and the
   project's own controls (CI config, hooks, validators). Read the project's
   CLAUDE.md or README for its official check command instead of guessing.

## The six gates, in order

Record each gate as `PASS`, `FAIL`, `N/A`, or `BLOCKED` with its evidence as you
go. If a gate fails, stop and decide:

- **The fix is part of the task you were given:** fix it, then start again
  from gate 1, because a fix can invalidate earlier gates.
- **The fix is outside the task** (a pre-existing bug, another team's code, a
  change the user didn't ask for): don't fix it. Report it with file and line,
  and let the user decide.

If you stop without passing every gate, still write all six gate lines: the
failing gate as `FAIL`, and each gate you didn't reach as
`BLOCKED — not run because gate N failed`. The verdict is then `NOT VERIFIED`.

### 1. Adversarial review

Treat your own summary, every subagent's report, and every green checkmark as a
claim, not proof. Look at the real thing:

- Read the actual diff (`git diff`, plus untracked files) end to end, not the
  description of it. Check for leftovers (debug output, TODOs, commented-out
  code, unrelated edits, secrets), half-applied patterns, removed safeguards,
  changed defaults, and dependency or config drift
  ([references/coherence-audit.md](references/coherence-audit.md) §2).
- Re-run the critical commands yourself now, rather than quoting an earlier
  run. Earlier output may predate your last edit.
- Get an independent read in proportion to the change, from the
  **`verify-completion:completion-verifier`** agent. Give it the requirement,
  the paths or diff range, the commands to run, and a focus, and **not** your
  conclusions:

  | Change | Independent read |
  | --- | --- |
  | Small: one or two files in one layer, done by you in this session | None needed; run the gates yourself |
  | Substantial: several files, work done by subagents, or a long session | One verifier, focus `all` |
  | Large: it spans layers (code with types, validators, config, CI, or docs) or several components | Three verifiers **in parallel**, one per focus: `coherence` (intent, diff, dependent layers), `depth` (tests, mocks, validators), `edges` (edge-case matrix, both directions) |

  Where subagents aren't available, run the same focuses yourself, one after
  another. For a large change, also tell the user that
  `/verify-completion:deep-verify` cross-checks every finding and every `PASS`
  with independent agents (several times the tokens of three verifiers). Run
  it only when the user asks for it; its report is input to your gates, not a
  substitute for them. Then reconcile: every finding a verifier reports is a claim to
  spot-check against the files, and a disagreement between verifiers is a
  finding in its own right. A verifier's `PASS` never replaces your own gates.

### 2. Validate the outcome

Confirm the result does what was asked, on the path that was asked for.

- Map each part of the requirement to the evidence that proves it. A part with
  no evidence isn't done.
- Check that what ran is the real path: the CLI the user will call, the
  endpoint in the real router, the production build, the actual data shape,
  not a helper, a mock, a sibling path, or a similar case.
- A passing suite that never exercises the changed code proves nothing about
  it. Find the test that hits it, or exercise it directly.
- Confirm what must stay the same still does, and that every layer that
  depends on what moved moved too: tests, types, validators, docs, config,
  CI, generated files
  ([references/coherence-audit.md](references/coherence-audit.md) §3). A
  change is incomplete when one layer moved and its dependents didn't.

### 3. Verify the counterpart

When something receives or depends on the work (an API consumer, a parser, a
schema or validator, a CLI that reads the config, a hook that guards an action,
a caller of the changed function), show that the receiving side **rejects**
what it should: missing fields, wrong types, malformed or malicious input,
bypass attempts. Accepting good input is only half the contract.

When the change adds or relies on a schema, guard, parser, or serializer, feed
it the inputs in [references/depth-audit.md](references/depth-audit.md) §3
(missing field, wrong type, empty or null, malformed nesting, dangerous extra
field) and record what it returned.

If nothing consumes the work, mark it `N/A` and name why (for example: "no
code reads this file; it is documentation only").

### 4. Distrust the green

Green doesn't mean correct. Actively hunt for ways the checks could be green
without the work being right, in two passes, and record what you examined and
what you found:

- [references/false-green.md](references/false-green.md): checks that were
  switched off, silenced, or pointed at the wrong target.
- [references/depth-audit.md](references/depth-audit.md) §1–2: read the tests
  and mocks that cover the change. Do they assert the required behavior or
  just the current output? Can the mocks fail, and do they accept states the
  real dependency would reject?

At minimum, check for:

- skipped, disabled, `only`-focused, or deleted tests, and loosened assertions,
  thresholds, lint rules, or type checks in the diff;
- error paths that are swallowed (`catch {}`, `|| true`, ignored exit codes)
  instead of reported;
- tests that assert on their own mocks or fixtures, or that would pass if the
  implementation were deleted;
- stale artifacts (a build, a generated file, a cached result) standing in for
  the current code;
- important paths nothing exercised.

### 5. Prove both directions

Show that what should work works, **and** that what should fail fails, with the
expected error for the expected reason. One direction isn't enough.

- Positive: the intended behavior, under the required conditions.
- Negative: invalid, incomplete, or hostile input is rejected; the old bug no
  longer reproduces; a guard really blocks.
- The strongest negative proof shows the test can fail: break the behavior on
  purpose and watch the check go red. Do that only in a throwaway place (a
  scratch copy or a temporary worktree), never in the user's working tree, and
  confirm it is gone afterwards.

Use the edge-case matrix in [references/depth-audit.md](references/depth-audit.md)
§4: pick the rows that apply to the change (input shape, bounds, text,
failure, concurrency, environment, boundaries, modules, shell), exercise them,
and give each row you skip a one-line reason. A skipped row without a reason
is a gap.

Mark it `N/A` only if a direction truly doesn't exist, and name the nearest
boundary you did test.

### 6. Leave the evidence

Give the user what they need to reach the same conclusion without trusting you:
the exact commands, the relevant output (trimmed, not paraphrased), file paths
with line numbers, and the reason for each `N/A`. Never invent or embellish
output, and never describe a command you didn't run as if you had.

## The Verification record

End the reply with this record. Its format is checked by the plugin's Stop hook,
so keep the tokens exactly as shown; the text after each status can be in any
language. Full rules: [references/record-format.md](references/record-format.md).

```markdown
### Verification record

Requirement: <what the user asked for, in their terms>

1. Adversarial review: PASS — <what you inspected and re-ran>
2. Outcome: PASS — <requirement → evidence mapping, the path that ran>
3. Counterpart: N/A — <why nothing consumes it>
4. Distrust the green: PASS — <vectors examined and what you found>
5. Both directions: PASS — <what works> / <what fails, and with which error>
6. Evidence: PASS — <where the commands, outputs, and paths are>

Verdict: VERIFIED
```

- Gate 3 is `PASS — <what was rejected>` when something consumes the work.
- Write the record exactly as shown: the heading line starts with
  `Verification record`, `Requirement:` is one line, each gate is one line with
  its evidence on that same line (inline `code`, no fenced blocks or numbered
  sub-lists inside the record), and the record is the last thing in the
  reply. Long commands and output go in the prose above it.
- `VERIFIED` needs gates 1, 2, 4, and 6 at `PASS` (they always apply), gates 3
  and 5 at `PASS` or `N/A` with a reason, and at least one command, path, or
  output in `code` that someone can re-run or open.
- Otherwise the verdict is `NOT VERIFIED`, with the failing or `BLOCKED` gates
  and their exact reasons. Then say plainly, above the record, that the work
  is not done and what would complete it. A reply that calls the work
  finished ("ready to merge", "all tests pass", "listo") while its verdict is
  `NOT VERIFIED` is rejected by the hook as a contradiction; describe partial
  results by gate ("gate 2 passed for the parser; gate 5 is blocked by …").
- Put the record after the prose, so the user reads the conclusion and its
  evidence together. Don't claim completion anywhere else in the reply in words
  stronger than the verdict.

## What this skill does not do

- It doesn't replace the project's tests, linters, reviewers, or CI; it
  checks that their results were read honestly.
- It doesn't commit, push, open or merge PRs, deploy, or publish, and a
  VERIFIED verdict never implies it may.
- It doesn't lower the bar when a check is hard. `BLOCKED` with a reason is
  the honest outcome.
