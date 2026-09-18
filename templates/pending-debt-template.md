<!--
  Reusable pending technical debt ledger.

  Copy this file to the repository's maintenance documentation area. Replace
  every placeholder, remove unused optional fields, and duplicate the entry
  block for each unresolved item.

  Record observed facts as evidence, separated from inference and open
  questions. Do not move an item to resolved debt until the corrective change
  is complete and its verification has passed.
-->

# Pending Debt

## Purpose

A living record of unresolved technical or maintenance conditions that need
follow-up, reassessment, or verified remediation.

## Entry criteria

Add an item only when **all** of these hold:

- A specific unresolved condition is observable or supported by traceable evidence — not speculation.
- It has a meaningful operational, security, reliability, compatibility, or maintainability impact.
- There's a concrete next action, or a concrete condition that would trigger reassessment.
- It isn't already tracked by another active record (an open issue, another ADR's follow-up, etc.) unless this ledger is the designated place for it.

Don't add general improvement ideas, unverified speculation, or a copy of every backlog task.

## Record maintenance

- **Append:** check for an existing entry on the same condition first.
- **Update:** revise the entry in place when evidence, impact, ownership, or next action changes. Keep confirmed facts distinct from inference.
- **Resolve:** move the entry to `resolved-debt.md` with its ID only after the fix is verified — both that it works and that the original failure no longer reproduces. Don't just delete it.

## Open Items

### {{DEBT-ID}} — {{Short debt title}}

- **Status:** Pending
- **Category:** {{e.g. security, compatibility, cost, quality}}
- **Evidence:**
  - **Confirmed facts:** {{Paths, revisions, commands, dates — what's actually verified.}}
  - **Inferences:** {{Reasoned conclusions that aren't directly verified, or "none".}}
  - **Open questions:** {{Unresolved questions that affect the assessment, or "none".}}
- **Impact / risk:** {{Current or plausible impact.}}
- **Owner or responsible area:** {{Person, team, system, or repository area — or "unassigned" if genuinely unowned.}}
- **Next action:** {{The smallest concrete action that advances or resolves this.}}
- **Review condition:** {{Event, date, or evidence that triggers reassessment or permits closure.}}
- **Related records:** {{Links to issues, ADRs, PRs, or "none".}}

<!-- Duplicate the {{DEBT-ID}} block above for each additional open item. -->
