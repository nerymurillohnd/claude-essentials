# Ruff in pre-commit, CI, and editors

Verified on 2026-09-19 (Ruff 0.16.8). Look up the current release before
writing a pin: `gh release view --repo astral-sh/ruff-pre-commit --json tagName`
or <https://github.com/astral-sh/ruff-pre-commit/releases>. Never write a
version from memory.

## One version everywhere

Ruff's findings change between releases, so the version must match in
`uv.lock` / dev dependencies, pre-commit, CI, and `required-version`. Bump them
in one commit.

## pre-commit

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.16.8 # keep equal to the project's Ruff version
    hooks:
      - id: ruff-check
        args: [--fix]
      - id: ruff-format
```

- Hook ids are `ruff-check` and `ruff-format`; `ruff` is a legacy alias.
- `ruff-check` with `--fix` runs **before** `ruff-format` and before any other
  formatter.
- The hooks already pass `--force-exclude`, so the project's `exclude` applies.
- `ruff-format` includes Markdown files in `types_or`. To lint `pyproject.toml`
  add `types_or: [python, pyi, jupyter, pyproject]` (needs `identify >= 2.6.18`).
- [prek](https://prek.j178.dev/) reads the same configuration.
- A failing pre-commit hook is fixed, never skipped with `--no-verify`.

## GitHub Actions

Check the repository's conventions for pinning (many require a full commit
SHA) before adding a step.

```yaml
- uses: astral-sh/ruff-action@<pinned SHA> # v4.x
  with:
    version: "0.16.8"
    args: check --output-format github
- run: ruff format --check --output-format github .
```

Or with uv:

```yaml
- run: uv run --frozen ruff check --output-format github .
- run: uv run --frozen ruff format --check --output-format github .
```

- CI checks, it never fixes: no `--fix`, no `ruff format` without `--check`.
- `--output-format github` produces inline annotations; `format --check`
  supports output formats since 0.16. Other formats: `concise`, `full`,
  `json`, `json-lines`, `junit`, `grouped`, `gitlab`, `pylint`, `rdjson`,
  `azure`, `sarif`. `RUFF_OUTPUT_FORMAT` sets the default.

## Editors: the Ruff language server

- `ruff server` is the built-in language server; the old `ruff-lsp` package
  is retired. VS Code's Ruff extension and Zed use it directly; Neovim uses
  `vim.lsp.config('ruff', …)`.
- Since 0.16 it also lints TOML configuration and supports notebooks.
- `configurationPreference` (default `editorFirst`) decides whether editor
  settings or the project file win; `filesystemFirst` makes the editor follow
  the project exactly, which keeps editor, hook, and CI in agreement.

## Claude Code

- The ruff-quality plugin's `ruff-hooks` skill installs an after-edit gate
  (fix, format, and lint every Python file Claude edits, plus a Stop gate).
- Keep a short Ruff section in the project's `CLAUDE.md` naming the command
  route (`uv run ruff`), so every session uses the same one.
