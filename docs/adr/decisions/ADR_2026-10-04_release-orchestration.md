---
status: accepted
date: 2026-10-04
decision-makers:
  - "Nery Samuel Murillo (maintainer)"
---

# Release orchestration with a project skill, merge left to the PR lifecycle

## Purpose

Decide how much of a plugin release is orchestrated now that the repository is maintained by one person and Claude Code, replacing the "no single release command" rule.

## Scope

`.claude/skills/release-plugin/`, `docs/releasing.md`, `.claude/skills/plugin-versioning/`. The scripts stay as they are: `scripts/bump_version.py`, `scripts/release_notes.py`, `scripts/check_pr.py`, `claude plugin tag` and `.github/workflows/release.yml`.

## Context and problem statement

[ADR release-automation](ADR_2026-10-03_release-automation.md) kept each release step manual until real releases showed which belong together. The maintainer then decided that, with only the maintainer and Claude Code working on the repository, the release should be orchestrated, while every action that leaves the machine still needs the maintainer's approval at that moment, and pull request reviews and the merge stay with the maintainer's `/github-ops:automatic-pr-lifecycle`.

## Decision drivers

- One entry point for a release, so no step (notes, bump, behaviour check, test-install, label) is forgotten.
- Every push, pull request and tag push is approved by the maintainer at that exact moment.
- No new script that bundles steps: the reviewed scripts keep their single responsibilities.
- Reviews and the merge are handled by the maintainer's pull request lifecycle, not by the release.

## Considered options

- A user-invoked project skill that runs the existing steps and stops for approval and for the merge
- One script that bumps, commits, pushes and tags
- Keep every step manual

## Decision outcome

Chosen option: **a user-invoked project skill that runs the existing steps and stops for approval and for the merge**, because it removes forgotten steps without bundling the scripts and keeps every publication behind the permission prompts.

`/release-plugin <plugin> <level> <topic>` creates the `<plugin>/<topic>` branch, checks the notes, runs the bump, drives the plugin, runs the gates, commits signed, pushes the branch and opens the pull request with its `semver:` label, then hands off to `/github-ops:automatic-pr-lifecycle`. `/release-plugin <plugin> tag` tags the merged commit, verifies the signature, pushes the tag and checks the GitHub Release. The skill sets `disable-model-invocation`, so only the maintainer starts it.

### Consequences

- Good, because a release follows the same sequence every time.
- Good, because the permission `ask` rules and hooks make each publication a prompt the maintainer answers.
- Bad, because the skill is a prompt: its order is guidance, while the gates, `check_pr.py` and the prompts are the enforcement.

### Confirmation

`check_pr.py` and the release workflow keep enforcing the result. Revisit after the first real releases, or when a collaborator joins and releases need a second reviewer.

## More information

Supersedes [ADR release-automation](ADR_2026-10-03_release-automation.md). See [ADR claude-code-automation](ADR_2026-10-04_claude-code-automation.md).
