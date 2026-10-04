---
status: accepted
date: 2026-10-03
decision-makers:
  - "Nery Samuel Murillo (maintainer)"
---

# Labels and pull request automation as code

## Purpose

Define the label taxonomy and how labels are created, applied and enforced.

## Scope

`.github/labels.yml`, `.github/labeler.yml`, `.github/release.yml`, the issue forms, and the Labels, Label pull requests and Pull request workflows.

## Context and problem statement

Triage, release categories and release discipline all depend on labels. Labels created by hand drift between what documentation promises and what the repository has.

## Decision drivers

- One definition file as the source of truth.
- Automatic labels where a rule can decide; human labels only where judgment is needed.
- Use maintained actions and native GitHub features.

## Considered options

- Labels as code with crazy-max/ghaction-github-labeler, actions/labeler for paths, issue-form labels for triage
- `gh label` scripts run by hand
- Labels created in the web interface

## Decision outcome

Chosen option: **labels as code**. Prefixes: `type:`, `semver:`, `status:`, `priority:`, `category:`, `plugin:<name>`, plus `security-review`, `good first issue` and `help wanted`. The scaffold appends `plugin:<name>` and its labeler rules. Issue forms apply `status:needs-triage` natively. The labeler applies `plugin:`, `category:`, `type:docs`, `type:chore` and `security-review` by path. The `semver:` label is a human decision and is enforced by `scripts/check_pr.py`.

### Consequences

- Good, because labels, release-note categories and gates stay consistent.
- Bad, because the label sync deletes labels not in the file; adding one means editing the file.

### Confirmation

`scripts/check_repo.py` fails when a plugin or category label or labeler rule is missing. The Labels workflow dry-runs on pull requests.

## Pros and cons of the options

### Labels as code

- Good, because changes are reviewed and reproducible.
- Bad, because it adds two workflows.

### Manual labels

- Good, because there is nothing to maintain.
- Bad, because they drift and cannot be checked.

## More information

The labeler runs on `pull_request_target` so it can label pull requests from forks; it never checks out or runs pull request code.
