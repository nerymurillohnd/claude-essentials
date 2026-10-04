---
status: accepted
date: 2026-10-03
decision-makers:
  - "Nery Samuel Murillo (maintainer)"
---

# Dated, validated MADR records in docs/adr/decisions/

## Purpose

Establish how this repository records decisions, so maintainers, contributors and Claude Code sessions know why it works the way it does and do not weaken rules they do not understand.

## Scope

Every decision that changes the catalog format, release process, validation, security posture, tooling or contribution model. Routine plugin changes go in changelogs instead. Covers `docs/adr/README.md`, `docs/adr/decisions/`, `templates/adr/ADR_YYYY-MM-DD_decision-slug.md`, `scripts/validate_adrs.py` and the `adrs` gate.

## Context and problem statement

A public marketplace accumulates rules whose reasons are easy to lose: why versions live only in `plugin.json`, why a tool was rejected, why a gate exists. Records must be findable, reviewable in pull requests, cheap to write and structurally sound without manual review.

## Decision drivers

- The format is a widely adopted open standard, not a house invention.
- The file list alone shows what was decided and when.
- Structure is checked automatically, like every other artifact in the repository.

## Considered options

- MADR structure with Purpose and Scope, dated filenames, validated by a script
- Numbered MADR records with an index table
- Free-form notes in `CLAUDE.md`

## Decision outcome

Chosen option: **MADR structure with Purpose and Scope, dated filenames, validated by a script**.

- The template is `templates/adr/ADR_YYYY-MM-DD_decision-slug.md`: MADR 4 plus Purpose and Scope sections.
- Records are saved as `docs/adr/decisions/ADR_YYYY-MM-DD_<slug>.md`; the date is the registration date and the slug is lowercase kebab-case.
- The frontmatter `date` equals the filename date; `status` is one of `proposed`, `accepted`, `rejected`, `deprecated` or `superseded`; `decision-makers` names accountable people; unused `consulted` and `informed` fields are omitted.
- To change a decision, a new record links the old one, and the old one is marked `superseded` with a link to the new one, without rewriting its rationale.
- Records carry no corporate document metadata; the filename and Git history identify them, and no index file is kept.

### Consequences

- Good, because chronology and subject are visible in any file listing.
- Good, because placeholders, dates, statuses, sections and links are checked on every run.
- Bad, because records registered on the same day sort by slug, not by the order they were written.
- Bad, because writing a record adds a step to significant changes.

### Confirmation

`python3 scripts/validate_adrs.py` runs in `python3 scripts/check.py` and in CI; `tests/test_gates.py` proves it fails on a wrong filename, a date mismatch, an unknown status, a leftover placeholder, a missing section and a superseded record without a link to its successor. Reviewers ask for a record when a pull request changes a rule listed in Scope.

## Pros and cons of the options

### Dated MADR records

- Good, because MADR captures drivers, options and consequences in a predictable shape and is familiar to many contributors.
- Bad, because the Purpose and Scope additions diverge slightly from upstream; attribution is kept in the template.

### Numbered records with an index

- Good, because the order of writing is explicit.
- Bad, because a number says nothing about the date, and the index is a second list to keep in sync.

### Notes in CLAUDE.md

- Good, because they load into every Claude Code session.
- Bad, because they mix current rules with history and grow without structure.

## More information

Procedure: [docs/adr/README.md](../README.md). Source: [MADR template](https://github.com/adr/madr/blob/develop/template/adr-template.md) (`MIT OR CC0-1.0`); attribution in [THIRD_PARTY_NOTICES.md](../../../THIRD_PARTY_NOTICES.md).
