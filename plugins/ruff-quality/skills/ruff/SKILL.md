---
name: ruff
description: Lint and format Python with Ruff and fix every finding in the code, never by silencing it. Covers installing Ruff, choosing the command route (project venv, PATH, uv run --locked --no-python-downloads, uvx only with consent), the working order (safe fixes, format, check), native configuration discovery, rule selection and formatter-compatible settings, migrating from black, isort, flake8, pylint, pyupgrade and autoflake, the native language server, pre-commit and CI, diagnosing exit codes and required-version errors, preview and unsafe fixes, and how to respond to the ruff-quality hook. Confirm ruff --version against the official changelog before relying on version-specific behavior.
when_to_use: On every Python file Claude writes, edits, reviews or fixes (.py, .pyw, .pyi, .ipynb) before calling that work done, not only when asked. Also when the ruff-quality hook reports findings or asks to confirm a suppression, and to install Ruff, explain or choose rules, write ruff.toml or [tool.ruff], upgrade a configuration written for an older Ruff, migrate from black, isort, flake8, pylint, pyupgrade or autoflake, set up the Ruff language server in an editor, wire Ruff into pre-commit or CI, or resolve a required-version or exit code 2 error.
compatibility: Claude Code, Claude Cowork, and any Agent Skills host. Running commands needs Ruff >= 0.16 from the project's own install or PATH; the guidance works without it. The after-edit hook runs only in Claude Code.
license: Apache-2.0
---

# Ruff

Ruff is Astral's Python linter (`ruff check`) and formatter (`ruff format`),
one binary that replaces Black, isort, Flake8 and its common plugins,
pyupgrade, autoflake, and part of Pylint.

Verified against **Ruff 0.16.8** (released 2026-09-16) and **uv 0.12.17** on
2026-09-22. Ruff changes rules, defaults, and formatter style in minor
releases ([versioning policy](https://docs.astral.sh/ruff/versioning/)). Run
`ruff --version`, then read the
[changelog](https://github.com/astral-sh/ruff/blob/main/CHANGELOG.md) and
[BREAKING_CHANGES.md](https://github.com/astral-sh/ruff/blob/main/BREAKING_CHANGES.md)
for every release after 0.16.8 before relying on anything below that can drift.

## Non-negotiable rules

1. **Fix the code, never silence it.** Never add `# noqa`, `# ruff: noqa`,
   `# ruff: ignore[...]`, `# ruff: file-ignore[...]`,
   `# ruff: disable[...]`, `# fmt: off`/`# fmt: on`, `# fmt: skip`,
   `# yapf: disable`, or `# isort: skip` to get a green run. Never add codes to
   `ignore`, `per-file-ignores`, `exclude`, or `unfixable`, narrow `select`, or
   pass `--ignore`, `--select`, `--exit-zero`, or `--isolated` for the same
   purpose. If a finding looks wrong, read `ruff rule <CODE>`, explain why,
   and let the user decide; a suppression or policy change is theirs.
2. **Safe fixes only by default.** Unsafe fixes can change behavior or drop
   comments. Use them only when the user asks, after showing
   `ruff check --unsafe-fixes --diff <files>`.
3. **Stay in scope.** Fix and format the files being changed. Never reformat
   or bulk-fix a whole codebase unasked. If `ruff format --diff <file>` would
   rewrite most of an untouched file, the project probably does not use
   `ruff format`: say so and ask before formatting it.
4. **The project's configuration rules.** Run Ruff with native discovery.
   Never override the project's configuration with flags unless the user asks.

## Pick the command route once

Resolve how to run Ruff before the first command, then reuse it. Details and
the flags' evidence are in [install-and-run.md](references/install-and-run.md).

| Situation | Command |
| --- | --- |
| The project has a virtual environment with Ruff | `.venv/bin/ruff …` (Windows: `.venv\Scripts\ruff.exe`) |
| Ruff is on `PATH` (and no project pin disagrees) | `ruff …` |
| Ruff is a dev dependency of a uv project (`uv.lock`) | `uv run --locked --no-python-downloads ruff …` |
| None of these, and the user agrees to a download | `uvx --no-python-downloads ruff@<version> …` |

- Without `--no-python-downloads`, `uv run` and `uvx` may silently download
  a Python interpreter ([uv docs](https://docs.astral.sh/uv/concepts/python-versions/)).
- `--locked` makes `uv run` fail when `uv.lock` is stale instead of rewriting
  it ([uv docs](https://docs.astral.sh/uv/concepts/projects/sync/)).
- `uvx` downloads a tool from PyPI: never use it without the user's consent,
  and pin the version the project uses.
- Ruff is missing: tell the user how to install it (dev dependency first) and
  stop; never install it yourself unasked.

## The working order

Run on the files you changed, in this order:

```bash
ruff check --fix <files>   # safe fixes first: they can add, remove, or reorder code and imports
ruff format <files>        # then format; the formatter does not sort imports
ruff check <files>         # then read what is left and fix it by hand
```

- `ruff check --diff <files>` previews safe fixes without writing.
- Read a rule before fixing it: `ruff rule F841` prints what it checks, why,
  an example, and its fix safety.
- `F401` (unused import) has a safe fix outside `__init__.py`: if you add an
  import in one edit and use it in the next, a `--fix` in between deletes it.
- When you name files explicitly (scripts, hooks), add `--force-exclude` so
  the project's `exclude` still applies.
- Stop and ask when a fix needs a product decision (public API rename,
  behavior change), when several fixes are valid, or when the finding count
  stops falling between iterations.

Finish with a short report: files in scope, what was fixed automatically,
what was fixed by hand, and anything left with its reason.

## When the ruff-quality hook is active (Claude Code)

The plugin's hooks run after Claude writes or edits a `.py`, `.pyw`, or
`.pyi` file. They use the project's own Ruff or the one on `PATH` (never
`uvx`, never a download) with native configuration discovery, on the whole
file:

1. `ruff check --fix --no-unsafe-fixes --unfixable F401`, then
   `ruff format`, then `ruff check --no-fix`, all with `--force-exclude`
   (files the project excludes are skipped).
2. Remaining findings come back to Claude. Fix them in the code, re-read the
   file (the hook rewrote it), and continue. An `F401` it reports is left for
   you on purpose: use the import or delete it.
3. At Stop, the hook re-checks every file touched and keeps Claude working,
   up to 7 times; the 8th attempt ends with a failure message to the user.
   Do not end the turn with findings left.
4. An edit or shell command that adds a suppression (including
   `--add-noqa` and `--add-ignore`) or changes Ruff configuration triggers a confirmation
   prompt for the user; it is never denied. That prompt is not a way around
   rule 1: do not propose such a change to get green.
5. Ruff (or `jq`, which the hook needs) not installed: the hook tells the
   user once per session how to install it and does not block. Offer the
   install routes; do not run them.

Because the hook formats the whole file, warn the user before editing a
file that is far from Ruff-formatted (rule 3).

## Configuration in brief

Full detail, every claim checked with `ruff check --show-settings`, is in
[configuration.md](references/configuration.md).

- **Per file, the closest configuration wins.** In one directory,
  `.ruff.toml` beats `ruff.toml` beats `pyproject.toml`; a `pyproject.toml`
  without `[tool.ruff]` is skipped. Configurations never merge: a nested file
  replaces its parent unless it says `extend = "../pyproject.toml"`.
- **User-level configuration** (`~/.config/ruff/`, or `$XDG_CONFIG_HOME/ruff/`;
  `%APPDATA%\ruff\` on Windows) applies only when no project configuration is
  found.
- **Command line:** `--config <file>` replaces discovery; `--config "KEY = VALUE"`
  overrides one key everywhere; a dedicated flag beats both; `--isolated`
  ignores every file.
- **`target-version`** is inferred from `requires-python` in the
  `pyproject.toml` next to the discovered configuration; otherwise it
  defaults to `py310`.
- **Rules:** Ruff 0.16.8 enables 413 rules by default. `lint.select`
  replaces that set; `lint.extend-select` adds to it. Choose deliberately:
  see [configuration.md](references/configuration.md#rule-selection-strategy).
- **Formatter conflicts:** keep `W191`, `E111`, `E114`, `E117`, `D203`,
  `D206`, `D300`, `Q000`–`Q004`, `COM812`, `COM819` (and `ISC002` in one
  setup) off when using `ruff format`
  ([official list](https://docs.astral.sh/ruff/formatter/#conflicting-lint-rules)).
- **Preview** (`lint.preview`, `format.preview`, `--preview`) is opt-in and
  unstable; preview rules are never selected without it.

## Diagnosing

| Symptom | Next step |
| --- | --- |
| Exit `1` from `check` | Findings remain (syntax errors are reported as `invalid-syntax` findings) |
| Exit `1` from `format --check`/`--diff` | A file would be reformatted |
| Exit `2` | Usage or configuration error, including a `required-version` mismatch and a file `format` cannot parse |
| Unexpected rules or settings | `ruff check --show-settings <file>` (prints `Settings path` and every resolved value) |
| A file is or is not checked | `ruff check --show-files` |
| Planning a large fix | `ruff check --statistics` |

More in [diagnosing.md](references/diagnosing.md).

## References

- [install-and-run.md](references/install-and-run.md): install routes,
  command routes, uv flags, keeping one version everywhere.
- [configuration.md](references/configuration.md): discovery and precedence,
  rule selection, per-file policy, target version, formatter settings,
  preview, unsafe fixes, legacy codebases.
- [migration.md](references/migration.md): Black, isort, Flake8 and plugins,
  Pylint, pyupgrade, autoflake, pydocstyle, Bandit, and upgrading an older
  Ruff configuration.
- [pipelines.md](references/pipelines.md): the `ruff server` language server
  and editors, migrating off `ruff-lsp`, pre-commit, GitHub Actions and other
  CI.
- [diagnosing.md](references/diagnosing.md): exit codes, inspection commands,
  syntax errors, `required-version`, and the suppression forms to recognize.
