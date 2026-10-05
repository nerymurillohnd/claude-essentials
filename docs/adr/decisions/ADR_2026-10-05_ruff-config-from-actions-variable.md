---
status: accepted
date: 2026-10-05
decision-makers:
  - "Nery Samuel Murillo (maintainer)"
---

# Ruff configuration from the maintainer's global file and an Actions variable

## Purpose

Remove the repository copy of the maintainer's ruff configuration while CI keeps applying exactly the same rules.

## Scope

`ruff.toml` (removed), `scripts/check.py ci-tools`, `.github/workflows/validate.yml`, the `RUFF_CONFIG` repository variable on GitHub, and the rules and guides that describe the ruff configuration. `shellcheckrc` stays a repository copy.

## Context and problem statement

`ruff.toml` was a byte-for-byte copy of `~/.config/ruff/ruff.toml`, kept in step by hand ([ADR validation-stack](ADR_2026-10-03_validation-stack.md)). Without a project configuration, ruff falls back to the user-level file at `${config_dir}/ruff/` ([ruff configuration docs](https://docs.astral.sh/ruff/configuration/)), so the maintainer's machine needs no copy. A CI runner has no user-level file: with nothing to read, ruff applies its default rule set, 413 rules instead of the 770 the maintainer's configuration enables (ruff 0.16.10, `--show-settings`, 2026-10-05), and the `python` gate would weaken silently.

## Decision drivers

- One source for the ruff configuration: the maintainer's global file.
- CI applies the same rules as the maintainer's machine; a gate never weakens silently.
- No copy to keep in step inside the repository.

## Considered options

- The global file locally and the `RUFF_CONFIG` Actions variable on CI
- Keep the repository copy
- Accept ruff's defaults on CI

## Decision outcome

Chosen option: **the global file locally and the `RUFF_CONFIG` Actions variable on CI**, because repository variables exist to hold configuration for workflows, and the variable is the global file itself.

- The repository has no ruff configuration file; locally ruff reads `~/.config/ruff/ruff.toml`.
- The repository variable `RUFF_CONFIG` holds that file, set with `gh variable set RUFF_CONFIG < ~/.config/ruff/ruff.toml` (first set 2026-10-05).
- `validate.yml` passes `vars.RUFF_CONFIG` to `scripts/check.py ci-tools` through the step's environment. `ci-tools` writes it to `${XDG_CONFIG_HOME:-~/.config}/ruff/ruff.toml` and fails when the variable is empty or when `ruff check --show-settings` does not report that file as the settings path.

### Consequences

- Good, because the configuration has one source and CI applies all of its rules.
- Good, because a missing or unused configuration fails CI instead of falling back to the defaults.
- Bad, because a change to the global file reaches CI only after the maintainer runs `gh variable set` again; until then CI checks the previous rules.
- Bad, because a contributor other than the maintainer has no ruff configuration locally; only the maintainer and Claude change this repository (CLAUDE.md).

### Confirmation

`tests/test_gates.py` covers an empty variable, the written file and its location, and a configuration ruff does not use. The first CI run after this change shows `ruff uses <home>/.config/ruff/ruff.toml` in the `ci-tools` step. Revisit if a second maintainer joins.

## Pros and cons of the options

### Global file and Actions variable

- Good, because nothing is copied into the repository.
- Bad, because the variable must be updated by hand after the global file changes.

### Repository copy

- Good, because the configuration travels with the code.
- Bad, because the copy must be kept in step with the global file by hand, which is the same chore in another place.

### Ruff defaults on CI

- Good, because nothing needs to be set.
- Bad, because CI would check 357 fewer rules than the maintainer's machine, a silent weakening of the `python` gate.

## More information

GitHub documents repository variables for non-sensitive workflow configuration ([variables](https://docs.github.com/en/actions/reference/workflows-and-actions/variables)). Approved by the maintainer in the Claude Code session of 2026-10-05.
