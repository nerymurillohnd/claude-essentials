# Diagnosing Ruff

Verified on 2026-09-22 by running Ruff 0.16.8 in a scratch directory, and
against [configuration](https://docs.astral.sh/ruff/configuration/),
[linter](https://docs.astral.sh/ruff/linter/), and
[formatter](https://docs.astral.sh/ruff/formatter/).

## Contents

- [Exit codes](#exit-codes)
- [Inspection commands](#inspection-commands)
- [Syntax errors](#syntax-errors)
- [required-version and other configuration errors](#required-version-and-other-configuration-errors)
- [Suppressions to recognize, never to add](#suppressions-to-recognize-never-to-add)

## Exit codes

| Command | 0 | 1 | 2 |
| --- | --- | --- | --- |
| `ruff check` | No findings left | Findings left (including `invalid-syntax`) | Usage or configuration error |
| `ruff check --fix` | Everything fixed or clean | Findings left after fixing | Same |
| `ruff check --diff` | No fix to show | A diff was printed | Same |
| `ruff format` | Ran (changed files or not) | Only with `--exit-non-zero-on-format` and a change | Error, including a file it cannot parse |
| `ruff format --check` / `--diff` | Nothing would change | A file would change | Same |

- `--exit-zero` forces 0 and `--exit-non-zero-on-fix` fails when a fix was
  applied. Never add `--exit-zero` to hide findings.
- Verified: `check` on a clean file 0; with `F401` 1; `--fix` that fixed
  everything 0; `format --check` on an unformatted file 1; `format` on
  `def f(:` 2; a `required-version` mismatch 2.

## Inspection commands

| Question | Command |
| --- | --- |
| Which configuration applies to this file, with every resolved value? | `ruff check --show-settings path/to/file.py` (first lines: `Resolved settings for`, `Settings path`) |
| Which files will Ruff check? | `ruff check --show-files [paths]` |
| What does a rule check, and is its fix safe? | `ruff rule <CODE>` (`--all` for every rule) |
| Which prefix is which plugin? | `ruff linter` |
| What does a setting do? | `ruff config <key>`, for example `ruff config lint.isort` |
| How big is the backlog per rule? | `ruff check --statistics` |
| What would the safe fixes change? | `ruff check --diff <files>` |
| What would an unsafe fix change? | `ruff check --unsafe-fixes --diff <files>` |
| What would formatting change? | `ruff format --diff <files>` |
| Is the cache stale? | `ruff clean`, or `--no-cache` for one run |
| Which version is this? | `ruff --version` (or `ruff version`) |

`--show-settings` is the first step for "Ruff ignores my configuration": it
names the file actually used. Common causes are a nearer configuration
(including a `pyproject.toml` with `[tool.ruff]` in a subfolder), a
`pyproject.toml` without `[tool.ruff]` being skipped, the user-level file
applying because the project has none, or a tool passing `--config` or
`--isolated`.

## Syntax errors

- `ruff check` reports them as `invalid-syntax` findings with exit 1; other
  rules on that file are unreliable until the syntax is fixed. Fix the syntax
  first.
- `ruff format` refuses the file ("Failed to parse …") and exits 2.
- Syntax that is valid only in newer Python is judged against the resolved
  target version: a new-syntax finding on valid code usually means
  `requires-python`/`target-version` is too low. Report it to the user; do not
  change the target to get green.

## required-version and other configuration errors

- Verified message: "Required version `>=99.0` does not match the running
  version `0.16.8`", after "Failed to load configuration `…/ruff.toml`",
  exit 2.
- Fix it by running the required version (the project's own install, or the
  route in [install-and-run.md](install-and-run.md)). Never remove or loosen
  the pin to make the command run.
- An unknown or misspelled key also exits 2 and names the key; check it with
  `ruff config`.
- Ruff warns about deprecated top-level lint settings and about
  formatter-conflicting rules; report those warnings to the user.

## Suppressions to recognize, never to add

Ruff understands all of these. Recognize them when reading code and explain
them when asked; adding one to make a check pass is never Claude's decision.

| Form | Scope |
| --- | --- |
| `# noqa: CODE` (bare `# noqa` suppresses everything on the line) | One line |
| `# ruff: ignore[CODE]` | End of the line, or the line before a diagnostic (0.16) |
| `# ruff: disable[CODE]` … `# ruff: enable[CODE]` | A range (0.15) |
| `# ruff: noqa: CODE`, `# ruff: file-ignore[CODE]`, `# flake8: noqa` | Whole file (all three verified on 0.16.8; `# flake8: noqa` silences every rule) |
| `# fmt: off` / `# fmt: on`, `# fmt: skip`, `# yapf: disable` / `# yapf: enable` | Formatter, at statement level |
| `<!-- fmt:off -->` / `<!-- fmt:on -->` | Formatter, in Markdown |
| `# isort: skip`, `# isort: skip_file` | Import sorting |
| `per-file-ignores`, `ignore`, `exclude`, `unfixable` | Configuration: project policy |
| `ruff check --add-noqa` / `--add-ignore` | Writes suppressions in bulk: only as a baseline the user chose |

`RUF100` (unused suppression) is in the 0.16.8 default set, and its fix
removes stale `noqa` comments: that removal is welcome. `PGH004` (blanket
`noqa`) is not a default in 0.16.8; enable it only if the user wants it.
