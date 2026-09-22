# Configuring Ruff

Verified on 2026-09-22 against Ruff 0.16.8. Sources:
[configuration](https://docs.astral.sh/ruff/configuration/),
[settings](https://docs.astral.sh/ruff/settings/),
[linter](https://docs.astral.sh/ruff/linter/),
[formatter](https://docs.astral.sh/ruff/formatter/),
[preview](https://docs.astral.sh/ruff/preview/),
[default rules](https://docs.astral.sh/ruff/default-rules/). Every row in
the discovery table was reproduced with `ruff check --show-settings` in a
scratch directory (the `Settings path` line names the file used).

This page teaches how to decide. It ships no configuration to copy: a
configuration is a project policy the user owns.

## Contents

- [Discovery and precedence](#discovery-and-precedence)
- [File selection](#file-selection)
- [Rule selection strategy](#rule-selection-strategy)
- [Per-file policy](#per-file-policy)
- [Target version](#target-version)
- [Formatter settings and conflicting rules](#formatter-settings-and-conflicting-rules)
- [Fix safety](#fix-safety)
- [Preview](#preview)
- [Common mistakes](#common-mistakes)
- [Legacy codebases: options for the user](#legacy-codebases-options-for-the-user)

## Discovery and precedence

| Situation | What Ruff 0.16.8 did |
| --- | --- |
| `.ruff.toml`, `ruff.toml`, `pyproject.toml` (with `[tool.ruff]`) in one directory | Used `.ruff.toml`; without it `ruff.toml`; then `pyproject.toml` |
| `pyproject.toml` without `[tool.ruff]` | Skipped; discovery kept walking up to the parent's `ruff.toml` |
| Nested `pkg/ruff.toml`, no `extend` | Files in `pkg/` used only it (parent's `line-length` ignored, back to the default 88) |
| Nested file with `extend = "../pyproject.toml"` | Parent's settings applied, nested keys on top |
| No project configuration, user-level file present | Used `$XDG_CONFIG_HOME/ruff/ruff.toml` (also `.ruff.toml` or `pyproject.toml` there) |
| Project configuration and user-level file both present | Used the project's; the user-level file was not layered on |
| `--config path/to/ruff.toml` | That file for every checked file |
| `--config "line-length = 55"` | Overrode that key on top of the discovered file |
| `--line-length 44 --config "line-length = 55"` | 44: a dedicated flag beats `--config` |
| `--isolated` | No file read; built-in defaults |

- Relative paths in a configuration (`exclude`, `src`, `per-file-ignores`
  globs) resolve from that configuration's directory.
- User-level location: `~/.config/ruff/` or `$XDG_CONFIG_HOME/ruff/` on macOS
  and Linux, `~\AppData\Roaming\ruff\` on Windows
  ([FAQ](https://docs.astral.sh/ruff/faq/)). Relative paths in it resolve
  from the current directory.
- `extend` is the only inheritance. There is no cascade.
- `required-version` (a PEP 440 specifier such as `">=0.16"` or `"==0.16.8"`)
  makes a different Ruff exit `2` instead of checking with other rules.
- Editors: the language server's `configurationPreference` decides whether
  editor settings or the file win (see [pipelines.md](pipelines.md)).

## File selection

- Discovered by default: `*.py`, `*.pyi`, `*.ipynb`, `pyproject.toml`;
  `*.pyw` only in preview (verified: `--show-files` listed a `.pyw` file only
  with `--preview`, although naming it explicitly lints it).
- `ruff format` also formats Python code blocks in Markdown (0.16.0+;
  verified). `ruff check` does not lint Markdown.
- Default `exclude` covers `.git`, `.venv`, `venv`, `.tox`, `.nox`,
  `node_modules`, `build`-like folders (`_build`, `dist`, `buck-out`), and
  tool caches; `respect-gitignore = true` also skips ignored files. Use
  `extend-exclude` to add paths without dropping the defaults.
- **Named files bypass exclusion.** Verified: with `extend-exclude = ["gen"]`,
  `ruff check gen/x.py` still reported findings; `--force-exclude` skipped
  it. Tools that pass file names (pre-commit, hooks, editors) need
  `--force-exclude` or `force-exclude = true`.
- Notebooks are linted and formatted by default. To opt out of one side,
  put `exclude = ["*.ipynb"]` under `[lint]` or `[format]`.

## Rule selection strategy

Facts:

- Ruff 0.16.8 enables **413 rules** with no configuration (counted from
  `--show-settings`). 0.16.0 expanded the default from 59 to 413 and dropped
  18 opinionated rules from it: `E401`, `E402`, `E701`–`E703`,
  `E711`–`E714`, `E721`, `E731`, `E741`–`E743`, `F403`, `F405`, `F406`,
  `F722` ([BREAKING_CHANGES.md](https://github.com/astral-sh/ruff/blob/main/BREAKING_CHANGES.md)).
  The [default rules page](https://docs.astral.sh/ruff/default-rules/)
  follows the latest release and may show a different count.
- `lint.select` **replaces** the default set. `lint.extend-select` **adds**
  to whatever is active. Verified: `--config 'lint.select=["F"]'` dropped
  `UP035` that the defaults reported.
- A more specific selector wins over a less specific one (`ALL` < prefix <
  code), and the command line beats the file. Verified:
  `--select F401 --ignore F` still reports `F401`.
- `ALL` grows with every release; preview rules never join it without
  preview mode.

The decision to put to the user:

| Approach | When | Cost |
| --- | --- | --- |
| No `select`: defaults, plus `extend-select` for extra families | The project wants to follow Ruff's curated defaults | New defaults arrive with minor upgrades; review them then |
| Explicit `select` listing every family | The project wants a rule set that changes only when someone edits it. The linter docs say: "Prefer `lint.select` over `lint.extend-select` to make your rule set explicit." | Must be revisited on upgrades, or new defaults are silently missed |

Either way:

- Size a family before adopting it:
  `ruff check --statistics --extend-select <PREFIX> .`
- `ruff linter` lists every prefix and its origin; `ruff rule <CODE>` and
  `ruff rule --all` explain rules; `ruff config <key>` documents a setting.
- `ignore` expresses a decision the project made (a rule that contradicts
  its style), not a way to make noise go away.

## Per-file policy

`lint.per-file-ignores` (and `extend-per-file-ignores`) is a policy decision
for the user: for example tests may legitimately use `assert` (`S101`) and
magic values (`PLR2004`), and CLI scripts may print (`T201`). Propose it with
the reason; never add it to get a green run. Glob negation is supported
(`"!src/**.py"`). Prefer a few broad, documented entries over many narrow
ones.

## Target version

- Resolution: `target-version` if set; otherwise `requires-python` from the
  `pyproject.toml` in the same directory as the discovered configuration, or,
  when no configuration file is found at all, from the nearest
  `pyproject.toml`; otherwise `py310` (since 0.14.0). Verified on 0.16.8: a
  directory holding only a `pyproject.toml` with `requires-python = ">=3.12"`
  resolved to 3.12 with no `Settings path`. Verified: `requires-python = ">=3.12"`
  next to `[tool.ruff]` resolved to 3.12; the same field in a
  `pyproject.toml` without `[tool.ruff]`, below a `ruff.toml`, was not used.
- With `--config <file>` no inference happens.
- Prefer `requires-python` as the single source of truth; set
  `target-version` only when the two must differ. `UP` rules and
  version-specific syntax checks follow this value.

## Formatter settings and conflicting rules

`ruff format` is a Black-compatible formatter (over 99.9% identical lines on
Django and Zulip). Its options live under `[format]`: `quote-style`
(`double`), `indent-style` (`space`), `skip-magic-trailing-comma` (`false`),
`line-ending` (`auto`), `docstring-code-format` (`false`),
`docstring-code-line-length` (`dynamic`). `line-length` (default 88) is
top-level and shared with `E501`; the formatter wraps on a best-effort basis.

Keep these rules off when using the formatter
([official list](https://docs.astral.sh/ruff/formatter/#conflicting-lint-rules)):
`W191`, `E111`, `E114`, `E117`, `D203`, `D206`, `D300`, `Q000`, `Q001`,
`Q002`, `Q003`, `Q004`, `COM812`, `COM819`, and `ISC002` when used without
`ISC001` and with `flake8-implicit-str-concat.allow-multiline = false`.
In 0.16.8 `E111`, `E114` and `E117` are preview-only: selecting them without
preview does nothing, and `ruff format` warns "has no effect because preview is
not enabled".
Incompatible isort options: `force-single-line`, `force-wrap-aliases`,
`lines-after-imports`, `lines-between-types`, `split-on-trailing-comma`.
Verified: selecting `COM812` makes `ruff format` warn and name the rule.

## Fix safety

- Safe fixes preserve runtime behavior and only remove comments when
  removing a whole statement. Unsafe fixes may change behavior (for example
  `list(...)[0]` to `next(iter(...))` raises a different exception).
- Only safe fixes apply by default. Verified: `F841` reported "1 hidden fix
  can be enabled with the `--unsafe-fixes` option", and
  `ruff check --unsafe-fixes --diff` showed it without writing (exit 1 when a
  diff exists).
- Project-level knobs, all policy decisions for the user: `unsafe-fixes`,
  `lint.extend-safe-fixes`, `lint.extend-unsafe-fixes`, `lint.fixable`,
  `lint.unfixable`.

## Preview

- Enable per side: `lint.preview = true`, `format.preview = true`, or
  `--preview` per command.
- A preview rule can be selected only in preview mode, even through `ALL`.
  `lint.explicit-preview-rules = true` requires full codes instead of
  prefixes.
- In preview, deprecated rules are disabled; selecting one explicitly is an
  error.
- Preview changes between patch releases. Turn it on only when the user
  wants it, and pin the Ruff version.

## Common mistakes

| Mistake | Effect | Fix |
| --- | --- | --- |
| A `select` list written for Ruff 0.15 or older | Most of the 0.16 defaults (`I`, `B`, `UP`, `RUF`, …) stay off | Decide explicitly (see the table above) |
| Expecting a root file to apply inside a package with its own file | The package ignores it | `extend = "../ruff.toml"` in the nested file |
| `exclude` set, file still checked by a hook or editor | The tool names the file | `--force-exclude` or `force-exclude = true` |
| Formatter-conflicting rules pulled in by a prefix (`Q`, `COM`, `ALL`) | Linter and formatter disagree | Add those codes to `ignore` (a documented, legitimate use) |
| `select` or `ignore` at the top level instead of under `lint` | Ruff warns that top-level linter settings are deprecated | Move them under `[lint]` / `[tool.ruff.lint]` |
| Relaxing `ignore` to pass CI | Debt hidden, not paid | Fix the code, or offer the options below |

## Legacy codebases: options for the user

When an existing codebase fails a new rule set, present these; never pick
one on the user's behalf:

1. Fix family by family, planned with `--statistics`, one commit each.
2. Enforce on changed files only in CI, and burn down the rest over time.
3. A one-time baseline with `ruff check --add-noqa="<reason>"` (or
   `--add-ignore`), committed separately. `RUF100` (on by default in 0.16.8)
   then reports suppressions that became unused. This is the user's decision,
   never Claude's shortcut.
