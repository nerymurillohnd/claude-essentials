---
status: accepted
date: 2026-10-03
decision-makers:
  - "Nery Samuel Murillo (maintainer)"
---

# Validation stack with zero repository dependencies

## Purpose

Choose the tools behind `uv run scripts/check.py` and how they are installed.

## Scope

`scripts/check.py`, `scripts/`, `tests/`, `pyrightconfig.json`, `ruff.toml`, `.github/workflows/validate.yml`.

## Context and problem statement

The repository distributes plugins; it is not an application with a runtime. It should not need `npm install`, a virtual environment or a lockfile to run its checks.

## Decision drivers

- No dependency manifest or install step for contributors.
- The official validator is the authority for Claude Code formats.
- Local runs and CI run identical commands.

## Considered options

- Official validator, stdlib Python gates via `uv run`, tools resolved on PATH locally and pinned on CI
- A Node project with npm dev dependencies (markdownlint, commitlint)
- A Python project with a lockfile

## Decision outcome

Chosen option: **official validator, stdlib Python gates, tools on PATH, pinned in CI**. The single entry point is `uv run scripts/check.py`, a standard-library Python script like every other script in the repository; CI runs exactly the same command. An initial Makefile was replaced by it on 2026-10-03 because the maintainer had agreed on Python scripts run with uv, not on make; the Python entry point also works for contributors without make, such as on Windows.

| Gate                     | Tool                                                                                                                            |
| ------------------------ | ------------------------------------------------------------------------------------------------------------------------------- |
| Claude Code formats      | `claude plugin validate --strict` on the marketplace and each plugin                                                            |
| Repository rules         | `scripts/check_repo.py` (catalog, names, SemVer, changelogs, READMEs, portability, self-containment, mods, labels, tag pattern) |
| Generated README content | `scripts/sync_readmes.py --check`                                                                                               |
| Gate behavior            | `tests/` with injected defects                                                                                                  |
| Formatting               | Prettier                                                                                                                        |
| Python                   | ruff, basedpyright with warnings as errors                                                                                      |
| Workflows                | actionlint, zizmor (`uvx zizmor@1.30.1 --offline --collect=workflows`)                                                          |
| GitHub file schemas      | check-jsonschema built-in schemas for workflows and issue forms                                                                 |
| Commits                  | `scripts/check_commit_msg.py` (Conventional Commits)                                                                            |

`uv run scripts/check.py ci-tools` installs the pinned versions on CI runners; locally each tool is resolved by name on PATH.

### Consequences

- Good, because there is nothing to install in the repository and CI mirrors `uv run scripts/check.py` exactly.
- Bad, because a contributor needs the tools on PATH (documented in CONTRIBUTING.md), and local versions can differ from the CI pins.

### Confirmation

CI runs `uv run scripts/check.py` and `uv run scripts/check.py test-install`. Markdown linting, link checking and Dependabot were considered and deferred; revisit when the catalog has several plugins.

## Pros and cons of the options

### Zero repository dependencies

- Good, because checks run immediately on a fresh clone with the documented tools.
- Bad, because own gate code needs its own tests (provided in `tests/`).

### npm dev dependencies

- Good, because markdownlint and commitlint are ready-made.
- Bad, because it adds a package manifest, a lockfile and an install step to a repository that has no runtime.

## More information

No hand-written JSON Schema for Claude Code files is used: the published schema URL returns 404, and the official validator is the authority (see [ADR editor-json-schemas-not-adopted](ADR_2026-10-03_editor-json-schemas-not-adopted.md)).
