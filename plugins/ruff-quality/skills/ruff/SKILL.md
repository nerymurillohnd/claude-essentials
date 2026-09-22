---
name: ruff
description: Lint and format Python with Ruff and fix every finding in the code, never by silencing it. Covers installing Ruff, choosing the command route (project venv, uv run --locked --no-python-downloads, PATH, uvx only with consent), the working order (safe fixes, format, check), native configuration discovery, rule selection and formatter-compatible settings, migrating from black, isort, flake8, pylint, pyupgrade and autoflake, the native language server, pre-commit and CI, diagnosing exit codes and required-version errors, preview and unsafe fixes, and how to respond to the ruff-quality hook. Confirm ruff --version against the official changelog before relying on version-specific behavior.
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

1. **Fix the code, never silence it.** Never add or widen `# noqa`,
   `# flake8: noqa`, `# ruff: noqa`, `# ruff: ignore[...]`, `# ruff: file-ignore[...]`,
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
   or bulk-fix a whole codebase unasked. Before the first edit to a file, if
   `ruff format --diff <file>` would change lines you are not touching, the
   project probably does not use `ruff format`: say so and ask the user before
   editing it, because formatting (yours, or the hook's) rewrites the whole file.
4. **The project's configuration rules.** Run Ruff with native discovery.
   Never override the project's configuration with flags unless the user asks.

## Pick the command route once

Resolve how to run Ruff before the first command, then reuse it. Details and
the flags' evidence are in [install-and-run.md](references/install-and-run.md).

Use the first row that applies:

| Situation | Command |
| --- | --- |
| 1. The project has a virtual environment with Ruff | `.venv/bin/ruff …` (Windows: `.venv\Scripts\ruff.exe`) |
| 2. Ruff is a dev dependency of a uv project (`uv.lock`), with no `.venv` yet | `uv run --locked --no-python-downloads ruff …` |
| 3. Ruff is on `PATH` and the project pins no other version | `ruff …` |
| 4. None of these, and the user agrees to a download | `uvx --no-python-downloads ruff@<version> …` |

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
  stops falling between iterations. Ask in one message and end your turn; do
  not keep editing while you wait.

Finish with a short report: files in scope, what was fixed automatically,
what was fixed by hand, and anything left with its reason.

## When the ruff-quality hook is active (Claude Code)

The plugin's hooks run after Claude writes or edits a `.py`, `.pyw`, or `.pyi`
file with its Write or Edit tools. They use a Ruff the user owns inside the
project, or the one on `PATH` (never `uvx`, never a download), with native
configuration discovery, on the whole file:

1. `ruff check --fix --no-unsafe-fixes --unfixable F401`, then `ruff format`,
   then `ruff check --no-fix`, all with `--force-exclude`. A file the project
   excludes is not checked, and the user is told so.
2. **After every edit**, if the hook changed the file you are told to re-read
   it; do that before the next edit. Findings left come back to you: fix them
   in the code. An `F401` it reports is left on purpose: use the import or
   delete it.
3. At Stop, the hook re-fixes, re-formats and re-checks every file you touched
   and keeps you working while the findings change, up to 7 times; then it
   tells the user what still fails and stops asking until those files are
   edited again. If a finding needs the user's decision, ask them once and end
   your turn: when nothing changes between two attempts, the hook stops asking.
4. Edits through Write or Edit that add or widen a suppression, change
   `ruff.toml`, `.ruff.toml` or the Ruff settings of `pyproject.toml`, and
   shell commands with a visible write (`>`, `tee`, `sed -i`, heredocs) that
   carry a suppression, `--add-noqa` or `--add-ignore`, ask the user; nothing
   is denied. Other shell routes (`cp`, `mv`, a script) are not detected: never
   use them to change configuration. The prompt is not a way around rule 1.
5. A tool or configuration error (exit 2, such as a `required-version`
   mismatch) is reported, not a finding: tell the user what it says and do not
   change the code to work around it.
6. Ruff (or `jq`, which the hook needs) not installed: you and the user are
   told once per session. Offer the install routes above; do not run them.

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
  `pyproject.toml` next to the discovered configuration, or, when no
  configuration file is found, in the nearest `pyproject.toml`; otherwise it
  defaults to `py310`.
- **Rules:** Ruff 0.16.8 enables 413 rules by default. `lint.select`
  replaces that set; `lint.extend-select` adds to it. Choose deliberately:
  see [configuration.md](references/configuration.md#rule-selection-strategy).
- **Formatter conflicts:** keep `W191`, `E111`, `E114`, `E117`, `D203`,
  `D206`, `D300`, `Q000`–`Q004`, `COM812`, `COM819` (and `ISC002` in one
  setup) off when using `ruff format`
  ([official list](https://docs.astral.sh/ruff/formatter/#conflicting-lint-rules)).
  In 0.16.8 `E111`, `E114` and `E117` are preview-only, so selecting them
  without preview does nothing (Ruff warns).
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
