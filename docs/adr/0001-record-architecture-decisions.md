---
status: accepted
date: 2026-10-03
decision-makers:
  - "Nery Samuel Murillo (maintainer)"
---

# Record architecture decisions as MADR-based ADRs

## Purpose

Establish how this repository records decisions so future maintainers and Claude Code sessions understand why it works the way it does.

## Scope

Every decision that changes the catalog format, release process, validation, security posture, tooling or contribution model. Routine plugin changes are recorded in changelogs instead.

## Context and problem statement

A public marketplace accumulates rules whose reasons are easy to lose: why versions live only in `plugin.json`, why a tool was rejected, why a gate exists. Without a record, later contributors weaken rules they do not understand.

## Decision drivers

- Decisions must be findable and reviewable in pull requests.
- The format must be a widely adopted open standard, not a house invention.
- Records must be cheap to write, so they actually get written.

## Considered options

- MADR 4 template adapted with Purpose and Scope sections
- Free-form notes in `CLAUDE.md`
- No records

## Decision outcome

Chosen option: **MADR 4 template adapted with Purpose and Scope sections**, stored in `templates/adr/adr-template.md` and used for every record in `docs/adr/NNNN-title.md`.

### Consequences

- Good, because MADR is a maintained open standard (license `MIT OR CC0-1.0`), familiar to many contributors.
- Good, because `make check` fails when an ADR is missing from the [index](README.md).
- Bad, because writing an ADR adds a step to significant changes.

### Confirmation

`scripts/check_repo.py` verifies every `docs/adr/NNNN-*.md` is listed in `docs/adr/README.md`. Reviewers ask for an ADR when a pull request changes a rule listed in Scope.

## Pros and cons of the options

### MADR 4 adapted

- Good, because it captures drivers, options and consequences in a predictable shape.
- Bad, because the Purpose and Scope additions diverge slightly from upstream; attribution is kept in the template.

### Notes in CLAUDE.md

- Good, because they load into every Claude Code session.
- Bad, because they mix current rules with history and grow without structure.

## More information

Source: [MADR template](https://github.com/adr/madr/blob/develop/template/adr-template.md); attribution in [THIRD_PARTY_NOTICES.md](../../THIRD_PARTY_NOTICES.md).
