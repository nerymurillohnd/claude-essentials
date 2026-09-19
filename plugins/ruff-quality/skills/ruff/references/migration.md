# Migrating to Ruff

Verified against Ruff 0.16.8 and the [Ruff FAQ](https://docs.astral.sh/ruff/faq/)
on 2026-09-19. Migrate in one reviewed change per tool, so each diff is
explainable.

## General procedure

1. Record the baseline: run the old tools and save their output.
2. Translate the configuration (tables below) into `ruff.toml` or
   `[tool.ruff]`, keeping `line-length` and `target-version` identical.
3. Run `ruff check --statistics .` and compare with the baseline. Differences
   are either rules the old setup did not have, or options that did not map.
4. Replace the old tools in pre-commit, CI, `tox`/`nox`, `Makefile`, editor
   settings, and dependency lists **in the same change**. Two formatters on one
   codebase fight forever.
5. Run `ruff check --fix` and `ruff format` in a separate commit, so review can
   skip a purely mechanical diff (add it to `.git-blame-ignore-revs`).

## Tool by tool

| From | To | Notes |
| --- | --- | --- |
| Black | `ruff format` | Same style; `line-length`, `skip-magic-trailing-comma`, and `target-version` carry over. Quote and indent style are `[format]` options. Remove `black` from every pipeline |
| isort | `ruff check --select I --fix` (on by default in 0.16) | Map `known_first_party` → `lint.isort.known-first-party`, `profile = "black"` needs nothing. Avoid `force-single-line`, `force-wrap-aliases`, `lines-after-imports`, `lines-between-types` (formatter conflicts) |
| Flake8 | `ruff check` | `max-line-length` → `line-length`; `extend-ignore` → `lint.ignore` (re-check each entry, most were formatter workarounds); `per-file-ignores` maps one-to-one |
| Flake8 plugins | Ruff prefixes | bugbear `B`, comprehensions `C4`, simplify `SIM`, bandit `S`, docstrings `D`, annotations `ANN`, print `T20`, pytest-style `PT`, quotes `Q` (conflicts with the formatter), eradicate `ERA`, pie `PIE`, return `RET`, tidy-imports `TID`, type-checking `TC`, use-pathlib `PTH`, naming `N`, builtins `A`, datetimez `DTZ`, logging-format `G`. Check each plugin's options in the `lint.flake8-*` tables |
| pyupgrade | `UP` (on by default) | Driven by `target-version`, not a `--py3X-plus` flag |
| autoflake | `F401`, `F841` fixes | `F401`'s fix is safe except in `__init__.py`; `F841`'s is unsafe |
| pydocstyle | `D` with `lint.pydocstyle.convention` | `google`, `numpy`, or `pep257` |
| Pylint | `PL` (partial) | Ruff implements a subset; keep Pylint only for checks Ruff lacks, and say which |
| Bandit | `S` | `# nosec` is not read; Bandit's skips must become explicit decisions |
| pycodestyle | `E`, `W` | Leave the formatter-conflicting codes off |

## Upgrading a Ruff 0.15 configuration to 0.16

1. Read the [0.16.0 release notes](https://astral.sh/blog/ruff-v0.16.0).
2. If the configuration uses `select`, decide whether to keep an exact list or
   switch to `extend-select` to adopt the new defaults; either way, run
   `ruff check --statistics .` to see what changes.
3. Rules removed from the defaults (`E401`, `E402`, `E701`–`E703`,
   `E711`–`E714`, `E721`, `E731`, `E741`–`E743`, `F403`, `F405`, `F406`,
   `F722`) must be selected explicitly if the project wants them.
4. `ruff format` now formats Python blocks in Markdown files. Opt out with
   `extend-exclude = ["*.md"]` in `[format]` if that is unwanted.
5. JSON output may contain `null` locations; update tools that parse it.
6. Bump every pin together (see [pipelines.md](pipelines.md)).
