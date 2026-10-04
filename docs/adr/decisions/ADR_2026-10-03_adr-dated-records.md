---
status: accepted
date: 2026-10-03
decision-makers:
  - "Nery Samuel Murillo (maintainer)"
---

# Dated, validated ADR records in docs/adr/decisions/

## Purpose

Make every architecture decision findable by what it decided and when, and keep records structurally sound without manual review.

## Scope

`docs/adr/README.md`, `docs/adr/decisions/`, `templates/adr/ADR_YYYY-MM-DD_decision-slug.md`, `scripts/validate_adrs.py` and the `adrs` gate in `scripts/check.py`. Supersedes [ADR_2026-10-03_record-architecture-decisions](ADR_2026-10-03_record-architecture-decisions.md).

## Context and problem statement

The first records were numbered (`0001-…`) and listed in an index table. A number says nothing about when a decision was taken, so a reader had to open each record to learn its date, and the index was a second list to keep in sync with the files.

## Decision drivers

- The file list alone should show what was decided and when.
- Records are historical: they are never rewritten, only superseded.
- Structure is checked automatically, like every other artifact in the repository.

## Considered options

- Dated filenames `ADR_YYYY-MM-DD_<slug>.md` in `docs/adr/decisions/`, validated by a script
- Numbered filenames with an index table

## Decision outcome

Chosen option: **dated filenames in `docs/adr/decisions/`, validated by a script**, because the filename carries the registration date and the decision, and validation replaces the index.

- The template is `templates/adr/ADR_YYYY-MM-DD_decision-slug.md` (MADR structure plus Purpose and Scope).
- The frontmatter `date` equals the filename date; `status` is one of `proposed`, `accepted`, `rejected`, `deprecated` or `superseded`; `decision-makers` names accountable people; unused `consulted` and `informed` fields are omitted.
- To change a decision, a new record links the old one, and the old one is marked `superseded` with a link to the new one, without rewriting its rationale.
- Records carry no corporate document metadata; the filename and Git history identify them.

### Consequences

- Good, because chronology and subject are visible in any file listing.
- Good, because placeholders, dates, statuses, sections and links are checked on every run.
- Bad, because records registered on the same day sort by slug, not by the order they were written.

### Confirmation

`uv run scripts/validate_adrs.py` runs in `uv run scripts/check.py` and in CI; `tests/test_gates.py` proves it fails on a wrong filename, a date mismatch, an unknown status, a leftover placeholder, a missing section and a superseded record without a link to its successor.

## More information

Procedure: [docs/adr/README.md](../README.md).
