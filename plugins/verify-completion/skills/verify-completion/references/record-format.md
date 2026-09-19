# Verification record format

The plugin's Stop hook (`scripts/gate.sh` + `scripts/analyze.jq`) checks this
format whenever a reply presents work as finished. It checks **form and
consistency**, not truth: it can tell that a gate has evidence, not that the
evidence is real. The truth part is gates 1 and 6, and your honesty.

## Shape

The canonical template is the one in [SKILL.md](../SKILL.md#the-verification-record);
this is the same shape:

```markdown
### Verification record

Requirement: <what was asked, at least a few words>

1. Adversarial review: PASS — <evidence>
2. Outcome: PASS — <evidence>
3. Counterpart: N/A — <reason nothing consumes it>
4. Distrust the green: PASS — <evidence>
5. Both directions: PASS — <evidence>
6. Evidence: PASS — <evidence>

Verdict: VERIFIED
```

A table works too, one row per gate, with the `Requirement:` and `Verdict:`
lines around it:

```markdown
### Verification record

Requirement: <what was asked>

| # | Gate | Status | Evidence |
| --- | --- | --- | --- |
| 1 | Adversarial review | PASS | read the full `git diff`; re-ran `npm test` |
| 2 | Outcome | PASS | <evidence> |
| 3 | Counterpart | N/A | <reason nothing consumes it> |
| 4 | Distrust the green | PASS | <evidence> |
| 5 | Both directions | PASS | <evidence> |
| 6 | Evidence | PASS | <evidence> |

Verdict: VERIFIED
```

## Rules the hook enforces

| Element | Rule |
| --- | --- |
| Heading | A Markdown heading (`#`–`######`) or bold line whose text starts with `Verification record` (or `Registro de verificación`), optionally after an emoji or "Final"; or a plain line that is exactly that text. If several appear, the last one counts. The record runs until the next heading of the same or a higher level (any heading, for a bold or plain one). |
| Requirement | A line starting `Requirement:` (also `Requirements:`, `Requisito:`, `Acceptance criteria:`, `Criterios de aceptación:`) with at least 12 letters or digits, on that line or the next one. |
| Gates | Exactly one line for each gate number 1–6, at the start of the line (`1.`, `1)`, `1:`, `Gate 1`, or a table cell `\| 1 \|`). The line must contain a status token and, after it on the same line, at least 12 letters or digits of evidence or reason. Indented numbered sub-lists are detail, not gates. |
| Code blocks | Fenced blocks inside the record are evidence only: lines in them never end the record or count as gates, labels, or verdicts. |
| Status tokens | Uppercase and exact: `PASS`, `FAIL`, `N/A`, `BLOCKED`. |
| Verdict | A line `Verdict: VERIFIED` or `Verdict: NOT VERIFIED` (label also `Veredicto`; `:`, `\|`, or a dash after it; any letter case; bold allowed). |
| `VERIFIED` | No gate is `FAIL` or `BLOCKED`; gates 1, 2, 4, 6 are not `N/A`; the record contains at least one `` `code` `` span or fenced block. |
| `NOT VERIFIED` | Accepted whenever the structure above is complete, as long as the rest of the reply doesn't present the whole work as finished ("ready to merge", "all tests pass", "everything is done", "listo"). Partial results ("the parser bug is fixed, the e2e run is blocked") are fine. Honesty is never blocked; a contradiction is. |

Gate names, evidence, and reasons may be written in any language. The fixed
parts are the heading text, the `Requirement` and `Verdict` labels (or their
Spanish forms), and the status tokens `PASS`, `FAIL`, `N/A`, `BLOCKED`.

Completion claims are looked for only outside the record (its evidence lines
naturally say things like "tests pass"), in the closing 300 lines of the reply,
and never inside code blocks or quotes.

## What happens when it's missing or invalid

With `enforcement` set to `enforce` (the default), the gate keeps the work going
for as long as it makes progress, like `/goal` does:

1. Claude Code continues the turn and tells Claude what is missing or wrong.
2. If Claude does more work (any tool except the read-only ones such as
   `Read`, `Grep`, `Glob`, `WebFetch`: shell commands, edits, subagents, MCP
   tools) and again ends with a claim and no valid record, it is asked again.
3. If Claude answers without doing any new work and still has no valid record,
   the turn ends and the user sees a warning that the claim is unverified.
   Claude Code also ends the turn after 8 consecutive continuations.

A valid record ends the cycle whatever its verdict: `VERIFIED` when every gate
holds, `NOT VERIFIED` when one doesn't. The gate never demands `VERIFIED`,
because the only way to satisfy that demand when a check truly can't pass is
to fake it.

With `warn`, only the warning in step 3 happens. With `off`, nothing happens.

## Status meanings

| Status | Use it when |
| --- | --- |
| `PASS` | You did the check now, on the current state, and it came out right. |
| `FAIL` | You did the check and it came out wrong. |
| `N/A` | The gate truly doesn't apply (gates 3 and 5 only, for `VERIFIED`); say why. |
| `BLOCKED` | You couldn't do the check: no access, no way to run it, missing input. Say exactly what's missing. |
