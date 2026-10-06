---
status: proposed
date: YYYY-MM-DD
decision-makers:
  - "{Accountable person or role}"
consulted:
  - "{Optional person or role consulted}"
informed:
  - "{Optional person or role informed}"
supersedes: none
superseded-by: none
---

<!--
  status: proposed | accepted | rejected | deprecated | superseded.
  supersedes: the ADR file name this record replaces, or none.
  superseded-by: the ADR file name that replaces this record, required when status is superseded.
  Remove the consulted and informed lines when empty; the validator rejects empty lists.
-->

# {Short title naming the decision}

## Purpose

{State what this decision establishes and why the record exists.}

## Scope

{Name the affected plugins, repository paths, workflows, or processes and relevant exclusions.}

## Context and problem statement

{Describe the circumstances, the problem, and links to evidence. Frame the decision as a
question when that helps readers understand the choice.}

## Decision drivers

- {Constraint, quality, risk, or goal that matters to the choice}
- {Another decision driver}

## Considered options

- {Chosen option}
- {Alternative option}

## Decision outcome

Chosen option: **{Option name}** because {explain why it best meets the decision drivers}.

### Consequences

- Good, because {positive consequence}.
- Bad, because {trade-off or cost}.

<!-- Optional: remove this table when the decision carries no material risk. -->

### Risks and mitigations

| Risk   | Likelihood or condition              | Impact   | Mitigation or response | Owner   |
| ------ | ------------------------------------ | -------- | ---------------------- | ------- |
| {Risk} | {Likelihood or triggering condition} | {Impact} | {Mitigation}           | {Owner} |

### Confirmation

{Explain how implementation or ongoing compliance will be checked, by whom, and when the
decision should be revisited. Link a test, review, PR, or other evidence when available.}

| Criterion or claim  | Verification method         | Evidence or result     | Responsible party | Review condition   |
| ------------------- | --------------------------- | ---------------------- | ----------------- | ------------------ |
| {What must be true} | {Command, review, or check} | {Result, or "pending"} | {Who}             | {When to re-check} |

Mark planned evidence as pending; do not present it as already observed.

## Pros and cons of the options

### {Chosen option}

- Good, because {supporting argument}.
- Bad, because {limitation}.

### {Alternative option}

- Good, because {supporting argument}.
- Bad, because {reason it was not chosen}.

## More information

{Add supporting evidence, related ADRs, implementation timing, or supersession links.
Remove this section when there is nothing to add.}

---

## Source

This template is adapted from the [Markdown Architectural Decision Records
(MADR)](https://github.com/adr/madr/blob/develop/template/adr-template.md) template.
