# Coherence audit: intent, diff, and layers

Correct files can still make an incorrect system. A local fix can cause a
regression elsewhere, a passing build can hide broken intent, and a finished
checklist can miss the objective. This audit checks coherence, not activity.
Every step ends with explicit findings, or an explicit "clean".

## 1. Reconstruct the intent (gate 2)

Before judging the result, write down, from the user's request and not from
your own summary:

| Question | Answer in one or two lines |
| --- | --- |
| What was the change supposed to accomplish? | |
| What problem does it claim to solve? | |
| What files and systems did it touch? | from `git status` / `git diff --stat`, not memory |
| What behavior should now be different? | |
| What behavior must stay the same? | |
| What risks did it introduce? | |

If the final state doesn't match this objective, the change fails regardless
of code quality.

## 2. Audit the diff (gate 1)

Read the whole change set (`git diff`, plus untracked files) and look for:

| Category | Look for |
| --- | --- |
| Noise | unrelated edits, formatting churn, dead code, debug logs, temporary comments, TODOs that block correctness |
| Half-done changes | inconsistent naming, a pattern applied in some places but not others, old and new logic both still live |
| Silent contract changes | removed safeguards, changed defaults, changed public API behavior, a schema change without a migration |
| Drift | lockfile or dependency changes nobody asked for, new or renamed environment variables, config that now differs between local, CI, staging, and production |
| Docs vs code | docs changed without the implementation, or the implementation changed without the docs |

A change that mixes unrelated objectives fails unless the user asked for both
and it's documented.

## 3. Check every dependent layer moved (gates 2 and 6)

For each pair the change touches, confirm the other side moved with it. Skip
the pairs the change doesn't touch, and say so.

| When this moved | Check |
| --- | --- |
| Implementation | tests, types and schemas, validators and guards, docs, config |
| Types | the runtime validation that should enforce them |
| Fixtures and mocks | the real dependency they stand in for |
| Package scripts | the CI workflows that call them |
| Routes, exports | the imports and callers that use them |
| Environment variables | the docs and example env files that list them |
| Generated files | the source and generator that produce them (regenerate and diff) |
| Public metadata | the product, content, or catalog data it describes |

A change is incomplete when one layer moved and a layer that depends on it
didn't.

## What the record should show

- **Gate 1:** the diff you read, and each noise, half-done, contract, or drift
  finding, or "clean".
- **Gate 2:** the intent in one line, mapped to evidence, and what must stay
  unchanged and how you confirmed it did.
- **Gate 6:** the layer pairs you checked, and the ones you skipped with their
  reason.
