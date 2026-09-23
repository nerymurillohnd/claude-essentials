# Report template

Every audit report uses this layout, in this order. Fill every section. When a section has
nothing to say, write "None", with the reason. The rules for findings and recommendations
are in `audit-contract.md`.

```markdown
> **Verification amendment — <date>:** <only when the audit corrected itself; what changed and why>

# Repository hygiene audit — <routine | deep>

**Status:** proposed
**Current authority:** live Git and provider observations pinned below; this report authorizes nothing
**Verification:** <what was read: local topology, provider enumerations, integrity checks>
**Open risks:** <what is unknown or blocked, one line each>

## Executive finding

<Three to eight plain-language sentences for a reader who does not know Git: what state the
repository is in, the most serious risks, what work exists only here, and what stays
untouched without approval.>

## Evidence and time boundary

- Repository: <top level>, Git dir: <path>, common dir: <path>
- Git <version>; bare/shallow/partial/sparse: <values>; object format: <sha1|sha256>
- Baseline: HEAD <full SHA>, tree <full SHA>, branch <name or detached>
- Collected: <local time and UTC>; observations are sequential, not one atomic snapshot
- Remotes: <names>; URLs redacted; <refreshed? which command, or "not fetched">
- Provider: <name and repository, or "none">; source per surface: <MCP tool | gh api | glab>, with the reason
- Evidence package: <path>

## Coverage

| Area | Status | Measure | Note |
| --- | --- | --- | --- |
| G1 Repository identity and format | inspected | — | |
| G5 Local branches | inspected | 6/6 branches | |
| P3 Pull requests and reviews | blocked | 0/? | gh not authenticated |
| … one row per area of the skill's matrix … | | | |

<Coverage is stated as a fraction for each authority. Do not state one global percentage
when any denominator is unknown; say why.>

## Findings

### <Area group — e.g. Branches and remotes>

**F3 — <title>.** <What it is; why it matters here; evidence (command and trimmed output);
confidence; consequence of doing nothing; root cause, if any.>

<…every finding, grouped by area; findings that share a root cause sit under it…>

## Recommendations awaiting approval

### R1 — <title> (closes F3, F7)

- **What was found:** …
- **What this does:** …, step by step
- **What changes / what stays:** …
- **Risk and who it affects:** …
- **Preconditions (re-checked before running):** …
- **Command:** `…` (literal, one per line)
- **Undo:** `…` or **irreversible**
- **If you do nothing:** …
- **Approval scope:** approving R1 authorizes only …; it does not authorize …
- **Alternatives:** … (recommended first)

<…every recommendation, in priority order: protect work → remove risk → fix root cause →
fix drift → reduce noise…>

## Retain / no action

| Item | Why it stays | Exit condition (what would make removal safe) |
| --- | --- | --- |

## Questions that would refine the recommendations

1. <Only questions whose answer changes a recommendation.>

## Verification and preservation statement

- Cross-checks: <e.g. tracking refs vs `ls-remote`; tree equality vs endpoint diffs>
- False-positive review: <catalogue entries that applied, and how each was ruled out>
- Controls: <a positive and a negative control, e.g. `git cat-file -t HEAD` → commit;
  `git cat-file -t 0000000000000000000000000000000000000000` → exit 128>
- Not performed: <every class of action that did not happen: fetch, prune, gc, deletion,
  checkout, push, provider mutation, …>
- Final evidence check: <the counts in the appendices equal the counts in this report>

## Approval request

<One line, for example: "Approve R1, R2 and R4; keep R3 until you answer question 1.">
```

## Appendices

Write the full enumerations to the evidence package (`audit-contract.md`, section 10), not
into the chat:

- `local-evidence.md`: each command, its exit code and its output. Redaction happens in the
  same command.
- `provider-evidence.md`: every PR, thread, alert and branch, with the totals read.

The report names each appendix and its path.

## Size

- A `routine` report fits in one reply.
- A `deep` report can be long; its appendices are always files. When the reply would exceed
  what the user can read, put the full report in the evidence package. Then give the
  Executive finding, the Coverage table, the Recommendations and the Approval request in the
  reply, with the report's path.
