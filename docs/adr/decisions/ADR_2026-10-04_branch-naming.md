---
status: accepted
date: 2026-10-04
decision-makers:
  - "Nery Samuel Murillo (maintainer)"
---

# Branch names follow the commit scope

## Purpose

Settle one branch naming rule for every pull request, plugin or not, and replace an approval that was recorded without evidence.

## Scope

Branches pushed to `origin` for pull requests: plugin work, repository tooling, CI, docs and the catalog. The names reserved for plugins in `scripts/repo.py`. Excluded: branches GitHub or bots create (Dependabot, the Claude GitHub App), and how users install plugins, which never reads a branch other than `main`.

## Context and problem statement

[ADR claude-code-automation](ADR_2026-10-04_claude-code-automation.md) recorded `<plugin>/<topic>` as "approved by the maintainer on 2026-10-04", and `.claude/rules/releasing.md` copied it, but the session handoff of the same day listed the convention as recommended and not approved, and no record of the approval exists. The rule also covered only plugins: pull request #4 used `ci/claude-action` with no rule behind it, and `docs/naming.md` still said branch names were free-form with a `<type>/<plugin>-<topic>` default.

Branches do not reach users. Claude Code clones the marketplace's default branch and copies a plugin into its cache keyed by version ([plugin loading](https://code.claude.com/docs/en/plugins/loading#how-claude-code-computes-the-version)); a user sees another branch only by adding the marketplace with an explicit `#<ref>`. The merge to `main` with a version bump is the release. So the rule is internal hygiene: it should be simple, match what is already enforced, and need no gate.

## Decision drivers

- One rule for every pull request, so no branch name is improvised.
- Reuse a convention that already exists rather than add a second vocabulary.
- No new tooling or gate for a choice that has no effect on users.
- Every recorded approval has a traceable source.

## Considered options

- Prefix equals the commit scope: `<plugin>/<topic>` or `<area>/<topic>`
- `<plugin>/<topic>` for plugins only, other branches free-form
- The scope rule plus a branch name check in `scripts/check_pr.py`

## Decision outcome

Chosen option: **prefix equals the commit scope**, because the Conventional Commits scope is already fixed in `docs/releasing.md` (the plugin name, or `marketplace`, `scripts`, `ci` or `docs`) and checked by `check_pr.py` for single-plugin pull requests, so one rule names both the branch and its commits.

- Plugin work: `<plugin>/<topic>`, for example `hello-example/add-license`. A pull request that changes several plugins uses the area of the main change.
- Other work: `marketplace/<topic>`, `scripts/<topic>`, `ci/<topic>` or `docs/<topic>`.
- `<topic>` is short kebab-case. Branches are short-lived, start from an up-to-date `main` and are deleted on merge (GitHub `delete_branch_on_merge` is on; `git fetch --prune` removes the remote-tracking reference).
- `marketplace`, `scripts`, `ci` and `docs` are reserved: no plugin may use them as its name, enforced by `repo.plugin_name_problems`.
- Decided by the maintainer in the session of 2026-10-04, after reviewing the options and the distribution model above; the approval has no written record.

### Consequences

- Good, because the branch name, the commit scope and the pull request title scope agree, and reviewers read the area from the branch.
- Good, because non-plugin pull requests now have a rule.
- Bad, because nothing enforces the rule: a wrong branch name is caught only in review. Acceptable while it has no effect on users.
- Bad, because four plugin names are no longer available.

### Confirmation

`tests/test_gates.py` proves a plugin named after a repository area fails `plugin_name_problems`. The project skills `new-plugin`, `add-component` and `release-plugin` create `<plugin>/<topic>` branches. Revisit when a collaborator joins: a branch name check in `check_pr.py` becomes worth its cost then.

## Pros and cons of the options

### Plugins only, other branches free-form

- Good, because it changes nothing.
- Bad, because non-plugin branches stay improvised, as `ci/claude-action` was.

### Scope rule plus a check in `check_pr.py`

- Good, because a wrong name fails CI.
- Bad, because pull requests from GitHub and bots need exceptions, and the check adds code and tests for a choice that never reaches users.

## More information

Replaces the branch convention bullet of [ADR claude-code-automation](ADR_2026-10-04_claude-code-automation.md); the rest of that record stands. See [ADR per-plugin-versioning](ADR_2026-10-03_per-plugin-versioning.md) for why the bump, not the tag, decides what users receive.
