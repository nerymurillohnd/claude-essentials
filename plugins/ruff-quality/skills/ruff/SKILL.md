---
name: ruff
description: This skill should be used whenever Claude writes, edits, reviews, or fixes Python code (.py, .pyi, .ipynb) in a project, and when the user asks to "lint", "format", "fix Ruff errors", "explain a Ruff rule", "configure Ruff", "set up ruff.toml or [tool.ruff]", "migrate from black / isort / flake8 / pylint / pyupgrade to Ruff", "upgrade to Ruff 0.16", "add Ruff to pre-commit", "run Ruff in CI / GitHub Actions", or "set up the Ruff language server". It teaches the current Ruff workflow (safe fixes, then format, then check), how configuration is discovered, how to choose rules, and why findings are fixed in code instead of silenced. For installing the Claude Code after-edit hook, use the ruff-hooks skill instead.
compatibility: Claude Code, Claude Cowork, and any Agent Skills host. Needs ruff >= 0.16 on PATH, in the project's virtual environment, or through uv to run commands; the guidance works without it.
license: Apache-2.0
---

# Ruff

Ruff is the linter and formatter for Python from Astral. It replaces Black,
isort, Flake8 and most of its plugins, pyupgrade, autoflake, pydocstyle, and
large parts of Pylint and Bandit. This skill covers **Ruff 0.16** (0.16.0
shipped on 2026-07-23). When the installed version differs, check
`ruff --version` and the [changelog](https://github.com/astral-sh/ruff/blob/main/CHANGELOG.md)
before relying on version-specific behavior.

## Non-negotiable rules

1. **Fix findings in the code.** Never add `# noqa`, `# ruff: noqa`,
   `# ruff: ignore[...]`, `# ruff: disable[...]`, `# ruff: file-ignore[...]`,
   `# fmt: off` / `# fmt: skip`, or `# isort: skip` to make a check pass, and
   never add rules to `ignore`, `per-file-ignores`, or `exclude`, lower
   `select`, or pass `--ignore`/`--isolated` to get a green run. If a finding
   seems wrong, explain why and let the user decide; the suppression or
   configuration change is theirs to make.
2. **Only safe fixes by default.** `--unsafe-fixes` may change behavior or drop
   comments. Use it only when the user asks, preview it first with
   `ruff check --unsafe-fixes --diff <paths>`, and show what changes.
3. **Stay in scope.** Lint, fix, and format the files being changed. Do not
   reformat a whole codebase that is not already Ruff-formatted: check first
   with `ruff format --check .` and ask before a mass reformat.
4. **Respect the project's configuration.** Read it before running Ruff; never
   pass flags that override it unless the user asks.

## Pick the command route once

Resolve how to run Ruff before the first command, then reuse it:

| Situation | Command |
| --- | --- |
| Ruff is a dependency of a uv project (`uv.lock` or `[dependency-groups]`) | `uv run ruff …` (in hooks and scripts: `uv run --no-sync ruff …`) |
| The project has a virtual environment with Ruff | `.venv/bin/ruff …` |
| Ruff is on `PATH` | `ruff …` |
| None of the above, and the user agrees | `uvx ruff@<version> …` (downloads a tool; pin the version the project uses) |

If `required-version` is set in the configuration, a different Ruff exits
with an error: install the required version rather than removing the pin.

## The workflow for every change

Run these on the files you changed, in this order:

```bash
ruff check --fix <files>      # safe fixes first (they can reorder or remove imports)
ruff format <files>           # then format; the formatter does not sort imports
ruff check <files>            # then read what is left and fix it by hand
```

- Pass `--force-exclude` whenever you name files explicitly (scripts, hooks,
  editors): without it Ruff lints a named file even when the configuration
  excludes it.
- Read a rule before fixing it: `ruff rule F841` prints its rationale, an
  example, and whether its fix is safe.
- Stop and ask when a finding needs a product decision (a public API rename, a
  behavior change), when several fixes are valid, or when the count of findings
  stops falling between iterations.
- When you add an import in one edit and use it in the next, run `ruff check
  --fix` only after both edits: `F401` (unused import) has a **safe** fix and
  would delete it.
- `ruff check` exits `0` when clean, `1` when findings remain, `2` on a usage
  or configuration error. `ruff format --check` and `--diff` exit `1` when a
  file would change.

End with a short report: files and scope, what was fixed automatically, what
was fixed by hand, and anything left with the reason.

## Configuration in one page

- **Files:** `.ruff.toml` > `ruff.toml` > `pyproject.toml` (only if it has a
  `[tool.ruff]` table), in that order within one directory.
- **Discovery:** each file uses the **closest** configuration above it. Ruff
  never merges configurations; a nested file replaces the parent unless it
  says `extend = "../ruff.toml"`.
- **User-level fallback:** `~/.config/ruff/` (or `$XDG_CONFIG_HOME/ruff/`;
  `%APPDATA%\ruff\` on Windows) applies **only when no project configuration
  exists**. It is not a layer on top of the project's.
- **Command line wins:** `--select`, `--config KEY=VALUE`, and
  `--config FILE` override every discovered file. `--isolated` ignores all of
  them.
- **Debugging:** `ruff check --show-settings path/to/file.py` prints the
  configuration file in use ("Settings path") and every resolved value.
- **Target version:** when `target-version` is not set, Ruff infers it from
  `requires-python` in the `pyproject.toml` next to the configuration.

## Choosing rules after Ruff 0.16

Ruff 0.16 turned on **413 rules by default** (up from 59), including isort
(`I`), bugbear (`B`), pyupgrade (`UP`), `RUF`, and `PGH004` (bare `noqa`), and
dropped 18 opinionated `E`/`F` rules from the defaults (`E401`, `E402`,
`E701`–`E703`, `E711`–`E714`, `E721`, `E731`, `E741`–`E743`, `F403`, `F405`,
`F406`, `F722`). Consequences:

- `lint.select` **replaces** the defaults; `lint.extend-select` **adds** to
  them. A configuration written for Ruff 0.15 with `select = [...]` silently
  turns the new defaults off. Prefer `extend-select`.
- `select = ["ALL"]` changes on every Ruff upgrade; use it only with a plan to
  review new rules.
- Never enable rules that conflict with the formatter: `W191`, `E111`,
  `E114`, `E117`, `D203`, `D206`, `D300`, `Q000`–`Q004`, `COM812`, `COM819`,
  and `ISC002` when used without `ISC001` and with
  `flake8-implicit-str-concat.allow-multiline = false`. `ruff format` warns
  and names the rule.
- Rules marked *preview* need `lint.preview = true` and an explicit selection.

The plugin's recommended profile, with the reasoning for each choice, is in
[`references/configuration.md`](references/configuration.md).

## Suppressions: what exists, and why this skill does not add them

Ruff understands `# noqa: CODE`, `# ruff: ignore[CODE]` (end of line or the
line before, 0.16+), `# ruff: disable[CODE]` … `# ruff: enable[CODE]` ranges
(0.15+), `# ruff: file-ignore[CODE]` and `# ruff: noqa: CODE` for a whole
file, `per-file-ignores`, and `--add-noqa`/`--add-ignore` to baseline a legacy
codebase. Recognize them when you read code; remove the ones `RUF100` reports
as unused. Adding one is the user's decision, never a way to finish a task.

## Formatter facts that prevent surprises

- `ruff format` is a Black-compatible formatter (over 99.9% identical output on
  Black-formatted code); differences are mostly around end-of-line comments.
- It also formats Python code blocks in Markdown (`python`, `py`, `pyi`,
  `pycon`, and Quarto's `{python}` fences) since 0.16; `ruff check` does not
  lint Markdown.
- Notebooks (`.ipynb`) are linted and formatted by default.
- `# fmt: off` / `# fmt: on` and `# fmt: skip` exist; they are suppressions
  under rule 1.

## Additional resources

- [`references/configuration.md`](references/configuration.md) — discovery
  edge cases, the recommended profile explained, rule selection strategy,
  per-file policy, preview, and common configuration mistakes.
- [`references/migration.md`](references/migration.md) — moving from Black,
  isort, Flake8 (and plugins), Pylint, pyupgrade, autoflake, pydocstyle, and
  Bandit, and upgrading a Ruff 0.15 configuration to 0.16.
- [`references/pipelines.md`](references/pipelines.md) — pre-commit and prek,
  GitHub Actions and other CI, the Ruff language server, and keeping every pin
  on the same version.
