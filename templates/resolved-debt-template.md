<!--
  Reusable resolved technical debt ledger.

  Copy this file to the repository's maintenance documentation area. Replace
  every placeholder, remove unused optional fields, and duplicate the entry
  block for each verified resolution.

  Preserve resolved entries as dated historical records. If a later change
  invalidates a resolution, keep the original entry and open a new pending
  item that links back to it — don't rewrite history.
-->

# Resolved Debt

## Purpose

An auditable history of maintenance/technical debt that's been corrected and
verified — what was wrong, what changed, and the evidence supporting closure.
Doesn't replace `pending-debt.md`; entries move here from there.

## Resolved Items

### {{DEBT-ID}} — {{YYYY-MM-DD}} — {{Short resolution title}}

- **Original pending record:** {{Link to the pending-debt.md entry this closes, or "none".}}
- **Resolved debt:** {{The original limitation, risk, or follow-up item.}}
- **Resolution:** {{The corrective change and the resulting state.}}
- **Positive verification:** {{Evidence the fix actually works — commands, tests, review.}}
- **Negative verification:** {{Evidence the original failure/risk no longer reproduces — not just that the new path works.}}
- **Owner or responsible area:** {{Person, team, system, or repository area}}
- **Residual risk / follow-up:** {{Anything left over, or "none".}}
- **Related records:** {{Links to issues, ADRs, PRs, or "none".}}
- **Superseded by:** {{Link to a newer item when this resolution no longer describes the current state, or "none".}}

<!-- Duplicate the {{DEBT-ID}} block above for each additional resolution. -->
