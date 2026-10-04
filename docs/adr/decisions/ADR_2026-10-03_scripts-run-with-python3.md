---
status: accepted
date: 2026-10-03
decision-makers:
  - "Nery Samuel Murillo (maintainer)"
---

# Repository scripts run with `python3`, without uv run

## Purpose

Decide how the scripts that generate, validate, verify, build and maintain this repository are started, and restate the validation stack with that change.

## Scope

`scripts/`, `tests/`, `scripts/git-hooks/commit-msg`, the workflows that run them, and every document that shows how to run them. Plugin scripts are out of scope. Supersedes [ADR_2026-10-03_validation-stack](ADR_2026-10-03_validation-stack.md).

## Context and problem statement

The scripts were started with `uv run` and carried PEP 723 metadata. They use only the standard library and the repository's own modules, so uv resolved nothing: it only picked an interpreter and kept one cached environment per script. On the maintainer's machine `python3` already resolves to the uv-managed CPython ahead of macOS's, and CI's ubuntu-24.04 image ships Python 3.12.3.

## Decision drivers

- No tool or file without a job: no dependencies means no dependency runner and no manifest.
- One plain command that works locally and in CI.
- The same interpreter for a script and any script it calls.

## Considered options

- `python3 scripts/<path>.py`, executable scripts with a `#!/usr/bin/env python3` shebang
- Keep `uv run` with PEP 723 metadata

## Decision outcome

Chosen option: **`python3 scripts/<path>.py`**.

- Every script starts with `#!/usr/bin/env python3`, has no PEP 723 block and is executable (mode 755) on disk and in git (`git update-index --chmod=+x`), as ruff EXE001 requires for a shebang. Imported modules have no shebang and stay at mode 644.
- Scripts call other scripts with `sys.executable`.
- There is no `pyproject.toml` or `uv.lock`. The minimum is Python 3.12, enforced by `ruff.toml` and `pyrightconfig.json`.
- CI runs the scripts with the runner's `python3`. uv stays only where a pinned tool is installed or run: `uv tool install` in `python3 scripts/check.py ci-tools`, and `uvx zizmor@1.30.1`.
- The rest of the validation stack is unchanged: `claude plugin validate --strict`, `scripts/check_repo.py`, `scripts/sync_readmes.py --check`, `scripts/validate_adrs.py`, the gate tests, Prettier, ruff, basedpyright, actionlint, zizmor and check-jsonschema, all run by `python3 scripts/check.py`.

### Consequences

- Good, because there is nothing to resolve, cache or lock, and the command is the same everywhere.
- Bad, because a contributor whose `python3` is older than 3.12 (for example macOS's Xcode Python 3.9) gets a `SyntaxError`; CONTRIBUTING.md states the requirement.

### Confirmation

`python3 scripts/check.py` passes locally and in CI; ruff and basedpyright target Python 3.12; `.claude/rules/repo-scripts.md` holds the rule.

## More information

Shebang and executable bit: [ruff EXE001](https://docs.astral.sh/ruff/rules/shebang-not-executable/), [Python executable scripts](https://docs.python.org/3/tutorial/appendix.html#executable-python-scripts), [`git update-index --chmod`](https://git-scm.com/docs/git-update-index#Documentation/git-update-index.txt---chmod-x). Runner Python version: [Ubuntu 24.04 runner image](https://github.com/actions/runner-images/blob/main/images/ubuntu/Ubuntu2404-Readme.md), image 20260927.320.1, checked 2026-10-03.
