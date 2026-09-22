# Migrating to Ruff

Verified on 2026-09-22 against Ruff 0.16.8, the
[FAQ](https://docs.astral.sh/ruff/faq/), the
[formatter](https://docs.astral.sh/ruff/formatter/) and
[settings](https://docs.astral.sh/ruff/settings/) pages, and `ruff linter`
(the prefix-to-plugin mapping below is its output).

## Contents

- [Procedure](#procedure)
- [Tool by tool](#tool-by-tool)
- [Flake8 plugins](#flake8-plugins)
- [Upgrading a configuration written for an older Ruff](#upgrading-a-configuration-written-for-an-older-ruff)

## Procedure

1. Record the baseline: run the old tools and save their output and exit
   codes.
2. Translate the configuration into `ruff.toml` or `[tool.ruff]`, keeping
   `line-length` and the Python target identical (prefer
   `requires-python` over a separate `target-version`).
3. Run `ruff check --statistics .` and `ruff format --check .`. Explain each
   difference: a rule the old setup lacked, an option that did not map, or a
   formatter difference.
4. Remove the old tools from pre-commit, CI, `tox`/`nox`, `Makefile`, editor
   settings, and dependency lists in the same change. Two formatters on one
   codebase undo each other.
5. Apply `ruff check --fix` and `ruff format` in a separate, purely
   mechanical commit, and suggest adding its hash to `.git-blame-ignore-revs`.

The whole-codebase run in step 5 is the migration the user asked for; it is
not a license to reformat anything else unasked.

## Tool by tool

| From | To | Notes |
| --- | --- | --- |
| Black | `ruff format` | Designed as a Black-compatible formatter (over 99.9% identical lines on Django and Zulip). `line-length`, `skip-magic-trailing-comma`, and the target carry over; `quote-style` and `indent-style` are `[format]` options. `black --check`/`--diff` map to `ruff format --check`/`--diff` |
| isort | `I` rules (`I001` is in the 0.16 defaults), applied with `ruff check --fix` | "Near-equivalent to isort's when using isort's `profile = "black"`", with differences for aliased imports and inline comments. Map `known_first_party` → `lint.isort.known-first-party`, `known_third_party`, `sections`, `force_sort_within_sections`, etc. to `lint.isort.*` (`ruff config lint.isort` lists them). Set `src` so first-party detection works. Avoid the formatter-incompatible options (`force-single-line`, `force-wrap-aliases`, `lines-after-imports`, `lines-between-types`, `split-on-trailing-comma`). `isort --check` maps to `ruff check --select I` |
| Flake8 | `ruff check` | `max-line-length` → `line-length`; `per-file-ignores` maps one to one; review every `extend-ignore` entry with `ruff rule <CODE>`: many were workarounds for Black (for example `E203`, `W503`); some are not Ruff rules at all (`ruff rule W503` is an error in 0.16.8), so drop them rather than carry them over |
| pyupgrade | `UP` (in the defaults) | Driven by the resolved target version, not a `--py3X-plus` flag |
| autoflake | `F401` (unused import), `F841` (unused variable) | `F401`'s fix is safe except in `__init__.py`; `F841`'s fix is unsafe (it can delete attached comments) |
| pydocstyle | `D` with `lint.pydocstyle.convention` (`google`, `numpy`, `pep257`) | "Enabling a convention will disable all rules that are not included in the specified convention" (`ruff config lint.pydocstyle.convention`) |
| pycodestyle | `E`, `W` | Keep the formatter-conflicting codes off (see [configuration.md](configuration.md#formatter-settings-and-conflicting-rules)) |
| Pylint | `PL` (`PLC`, `PLE`, `PLR`, `PLW`) | Ruff implements a subset and Pylint does more type inference. Keep Pylint only for checks Ruff lacks, name them, and pair Ruff with a type checker |
| Bandit | `S` | Bandit's `# nosec` comments are not Ruff suppressions; each skip becomes an explicit decision for the user |
| eradicate, yesqa | `ERA`, `RUF100` | `RUF100` (unused `noqa`) is in the 0.16 defaults |

## Flake8 plugins

From `ruff linter` on 0.16.8. Check each plugin's options in the matching
`lint.flake8-*` table (`ruff config lint` lists them).

| Plugin | Prefix | Plugin | Prefix |
| --- | --- | --- | --- |
| flake8-bugbear | `B` | flake8-comprehensions | `C4` |
| flake8-simplify | `SIM` | flake8-bandit | `S` |
| flake8-annotations | `ANN` | flake8-docstrings (pydocstyle) | `D` |
| flake8-print | `T20` | flake8-debugger | `T10` |
| flake8-pytest-style | `PT` | flake8-quotes | `Q` (formatter conflicts) |
| flake8-commas | `COM` (formatter conflicts) | flake8-implicit-str-concat | `ISC` |
| flake8-builtins | `A` | flake8-datetimez | `DTZ` |
| flake8-return | `RET` | flake8-raise | `RSE` |
| flake8-pie | `PIE` | flake8-errmsg | `EM` |
| flake8-type-checking | `TC` | flake8-tidy-imports | `TID` |
| flake8-use-pathlib | `PTH` | flake8-logging-format | `G` |
| flake8-logging | `LOG` | flake8-blind-except | `BLE` |
| flake8-unused-arguments | `ARG` | flake8-boolean-trap | `FBT` |
| flake8-self | `SLF` | flake8-todos / flake8-fixme | `TD` / `FIX` |
| flake8-async | `ASYNC` | flake8-pyi | `PYI` |
| pep8-naming | `N` | mccabe | `C90` |
| flynt | `FLY` | tryceratops | `TRY` |

A plugin missing from `ruff linter` has no Ruff equivalent: tell the user
which checks would be lost.

## Upgrading a configuration written for an older Ruff

1. Read [BREAKING_CHANGES.md](https://github.com/astral-sh/ruff/blob/main/BREAKING_CHANGES.md)
   and the [changelog](https://github.com/astral-sh/ruff/blob/main/CHANGELOG.md)
   for every minor release crossed.
2. Run the new version with `--statistics` before and after, so the size of
   the change is known.
3. Changes to check when crossing into 0.16:
   - The default set grew from 59 to 413 rules, and 18 rules left it
     (`E401`, `E402`, `E701`–`E703`, `E711`–`E714`, `E721`, `E731`,
     `E741`–`E743`, `F403`, `F405`, `F406`, `F722`): select them explicitly
     if the project wants them. An existing `select` list keeps replacing the
     defaults; decide whether to keep it (see
     [configuration.md](configuration.md#rule-selection-strategy)).
   - `ruff format` formats Python code blocks in Markdown files by default.
   - `format --check` supports `--output-format` (for example `github`).
   - JSON output fields such as `filename` and `location` may be `null`;
     update tools that parse it.
   - `# ruff: ignore[...]` comments are recognized.
4. Crossing 0.15: the 2026 formatter style guide (expect a formatting diff),
   and `# ruff: disable[...]`/`# ruff: enable[...]` range comments.
5. Crossing 0.14: the default target became `py310`.
6. Move deprecated top-level lint settings under `lint` (Ruff warns and
   names them).
7. Bump every pin together (see
   [install-and-run.md](install-and-run.md#one-version-everywhere)).
