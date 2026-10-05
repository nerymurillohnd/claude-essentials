# Changelog

Notable changes to this plugin are documented here for its users.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and plugin versions follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-10-05

### Added

- `/project-automation:automate` skill: audits a repository, proposes Claude Code automation backed by evidence, waits for approval, then builds and tests each approved item and writes a guide for the team.
- `automation-scout` agent: read-only inventory of the existing Claude Code setup, its defects and the recurring manual work in scripts, docs and git history.
- `feature-researcher` agent: checks the live Claude Code documentation and changelog for the installed version, with sources and quotes.
- `automation-verifier` agent: re-runs every acceptance test independently and tries inputs the author did not.
- Eval suite in `evals/` for `claude plugin eval`: compares the skill with a no-plugin baseline on a sample repository and checks that unrelated requests do not load it.
