---
status: accepted
date: 2026-10-03
decision-makers:
  - "Nery Samuel Murillo (maintainer)"
---

# Validation stack: standard-library scripts run with `python3`, tools on PATH

## Purpose

Choose the tools behind `python3 scripts/check.py`, how the repository scripts are started and how the tools are installed.

## Scope

`scripts/`, `tests/`, `scripts/git-hooks/commit-msg`, `ruff.toml`, `shellcheckrc`, `pyrightconfig.json`, the workflows that run the scripts, and every document that shows how to run them. Plugin scripts are out of scope.

## Context and problem statement

The repository distributes plugins; it is not an application with a runtime. Its scripts use only the Python standard library and the repository's own modules, so there is nothing to resolve, install or lock. Contributors and CI must run the same checks with the same command.

## Decision drivers

- No dependency manifest, lockfile or install step.
- The official validator is the authority for Claude Code formats.
- One plain command that works locally and in CI, on any operating system.
- The same interpreter for a script and any script it calls.

## Considered options

- Official validator, standard-library Python gates run with `python3`, tools resolved on PATH locally and pinned in CI
- Scripts run through a dependency runner (`uv run`) with inline script metadata
- A Node or Python project with dev dependencies and a lockfile

## Decision outcome

Chosen option: **official validator, standard-library Python gates run with `python3`, tools on PATH, pinned in CI**.

- The single entry point is `python3 scripts/check.py`; CI runs exactly the same command.
- Every script starts with `#!/usr/bin/env python3` and is executable (mode 755) on disk and in git (`git update-index --chmod=+x`), as ruff EXE001 requires for a shebang. Imported modules have no shebang and stay at mode 644.
- Scripts call other scripts with `sys.executable`.
- There is no `pyproject.toml`, lockfile or inline script metadata. The minimum is Python 3.12, enforced by `ruff.toml` and `pyrightconfig.json`.
- `ruff.toml` (`select = ["ALL"]`) and `shellcheckrc` (`enable=all`) are copies of the maintainer's strict global configurations, so every machine and CI apply the same rules.
- Local pre-commit hooks (`.pre-commit-config.yaml`, run by prek, the runner basedpyright's docs recommend) run ruff and basedpyright on every commit, pinned to the CI versions; the `repo` gate checks the pins. They are a fast local check, not a replacement for the gates.
- `python3 scripts/check.py ci-tools` installs the pinned versions on CI runners (`uv tool install`, `uvx zizmor`); locally each tool is resolved by name on PATH.

| Gate                     | Tool                                                                                                                            |
| ------------------------ | ------------------------------------------------------------------------------------------------------------------------------- |
| Claude Code formats      | `claude plugin validate --strict` on the marketplace and each plugin                                                            |
| Repository rules         | `scripts/check_repo.py` (catalog, names, SemVer, changelogs, READMEs, portability, self-containment, mods, labels, tag pattern) |
| ADR records              | `scripts/validate_adrs.py`                                                                                                      |
| Generated README content | `scripts/sync_readmes.py --check`                                                                                               |
| Gate behavior            | `tests/` with injected defects                                                                                                  |
| Formatting               | Prettier                                                                                                                        |
| Python                   | ruff, basedpyright with warnings as errors                                                                                      |
| Workflows                | actionlint (with shellcheck), zizmor (`--offline --collect=workflows`)                                                          |
| GitHub file schemas      | check-jsonschema built-in schemas for workflows and issue forms                                                                 |
| Commits                  | `scripts/check_commit_msg.py` (Conventional Commits), in pull requests and the optional `commit-msg` hook                       |

### Consequences

- Good, because there is nothing to resolve, cache or lock, and the command is the same everywhere.
- Good, because CI mirrors `python3 scripts/check.py` exactly.
- Bad, because a contributor needs the tools on PATH and Python 3.12 or newer (a `python3` older than 3.12 fails with a `SyntaxError`); CONTRIBUTING.md states both, and local versions can differ from the CI pins.
- Bad, because own gate code needs its own tests, provided in `tests/`.

### Confirmation

CI runs `python3 scripts/check.py` and `python3 scripts/check.py test-install`; ruff and basedpyright target Python 3.12; `.claude/rules/repo-scripts.md` and `.claude/rules/testing/gates.md` hold the rules. Markdown linting, link checking and Dependabot are deferred; revisit when the catalog has several plugins.

## Pros and cons of the options

### Standard-library scripts with `python3`

- Good, because checks run immediately on a fresh clone with the documented tools.
- Bad, because the interpreter version depends on the contributor's PATH.

### A dependency runner with inline metadata

- Good, because the runner picks a suitable interpreter.
- Bad, because with no dependencies it only adds a tool and a cached environment per script.

### Dev dependencies and a lockfile

- Good, because ready-made linters such as markdownlint and commitlint are available.
- Bad, because it adds a package manifest, a lockfile and an install step to a repository that has no runtime.

## More information

No hand-written JSON Schema for Claude Code files is used ([ADR editor-json-schemas-not-adopted](ADR_2026-10-03_editor-json-schemas-not-adopted.md)). Shebang and executable bit: [ruff EXE001](https://docs.astral.sh/ruff/rules/shebang-not-executable/), [Python executable scripts](https://docs.python.org/3/tutorial/appendix.html#executable-python-scripts), [`git update-index --chmod`](https://git-scm.com/docs/git-update-index#Documentation/git-update-index.txt---chmod-x). CI Python: [Ubuntu 24.04 runner image](https://github.com/actions/runner-images/blob/main/images/ubuntu/Ubuntu2404-Readme.md) ships Python 3.12.3 (image 20260927.320.1, checked 2026-10-03).
