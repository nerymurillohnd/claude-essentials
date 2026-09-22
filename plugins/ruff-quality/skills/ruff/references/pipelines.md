# Ruff in editors, pre-commit, and CI

Verified on 2026-09-22 against Ruff 0.16.8 and
[editors](https://docs.astral.sh/ruff/editors/),
[editors/setup](https://docs.astral.sh/ruff/editors/setup/),
[editors/settings](https://docs.astral.sh/ruff/editors/settings/),
[editors/migration](https://docs.astral.sh/ruff/editors/migration/),
[integrations](https://docs.astral.sh/ruff/integrations/),
[ruff-pre-commit](https://github.com/astral-sh/ruff-pre-commit), and
[ruff-action](https://github.com/astral-sh/ruff-action). Look up the current
release of each before writing a pin; never write a version or a tag from
memory.

## Contents

- [The language server](#the-language-server)
- [Editors](#editors)
- [Migrating off ruff-lsp](#migrating-off-ruff-lsp)
- [pre-commit](#pre-commit)
- [GitHub Actions](#github-actions)
- [Other CI](#other-ci)

## The language server

- `ruff server` is Ruff's built-in language server (beta in 0.4.5, stable in
  0.5.3). It provides diagnostics, fix code actions (`source.fixAll`,
  `source.organizeImports`), and formatting. Since 0.16.1 it also lints TOML
  configuration, and since 0.16.4 it supports pull diagnostics for notebook
  cells ([changelog](https://github.com/astral-sh/ruff/blob/main/CHANGELOG.md)).
- It does not do navigation or completion: run it alongside another Python
  language server (Pyright, basedpyright, ty, …) and disable Ruff's hover
  where both offer it.
- `configurationPreference`: `editorFirst` (default) lets editor settings win
  over the project file, `filesystemFirst` lets the file win, `editorOnly`
  ignores files. `filesystemFirst` keeps the editor in line with the CLI,
  hooks, and CI. `configuration` can point to a file or hold inline settings.
- Other settings: `lint.enable`, `organizeImports`, `fixAll`,
  `showSyntaxErrors` (all default `true`), `lineLength`, `lint.select`,
  `lint.extendSelect`, `format.preview`, and more.
- In VS Code they use the `ruff.` prefix (`ruff.lineLength`); in other editors
  they go in `initialization_options.settings` (camelCase, no prefix).

## Editors

| Editor | Setup |
| --- | --- |
| VS Code | The official Ruff extension (`charliermarsh.ruff`, 2024.32.0 or later recommended). It uses `ruff server` automatically for Ruff 0.5.3+ (`ruff.nativeServer = "auto"`). Binary: `ruff.path`, else the active environment, else `PATH`, else the bundled copy |
| Neovim 0.11+ | `vim.lsp.config('ruff', { init_options = { settings = { … } } })` then `vim.lsp.enable('ruff')`; 0.10 uses `nvim-lspconfig`. Disable hover in an `LspAttach` autocmd with `client.server_capabilities.hoverProvider = false` when Ruff runs next to Pyright |
| Vim | `vim-lsp` with `lsp#register_server()` running `ruff server` |
| Helix | `[language-server.ruff]` with `command = "ruff"`, `args = ["server"]` in `languages.toml`, then `language-servers = ["ruff"]` for Python |
| Kate | LSP Client plugin, user server settings with `["ruff", "server"]` |
| Sublime Text | The `LSP` and `LSP-ruff` packages |
| PyCharm | Native Ruff support from 2025.3 (Python, Tools, Ruff); otherwise an External Tool or the third-party plugin |
| Emacs | Eglot (`eglot-server-programs`), or `flymake-ruff` / `emacs-ruff-format` |
| Zed | Built in; settings under `lsp.ruff.initialization_options.settings` |
| TextMate | `textmate2-ruff-linter` bundle |

VS Code on-save settings from the extension's README:

```json
{
  "[python]": {
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.fixAll": "explicit",
      "source.organizeImports": "explicit"
    },
    "editor.defaultFormatter": "charliermarsh.ruff"
  }
}
```

## Migrating off ruff-lsp

`ruff-lsp` is superseded by `ruff server`. When migrating:

- Remove `lint.run` (the server lints on every keystroke),
  `ignoreStandardLibrary`, and `showNotifications`.
- Replace `lint.args` and `format.args` with granular settings, for example
  `"ruff.lint.args": "--select=E,F"` → `"ruff.lint.select": ["E", "F"]`, and
  `"ruff.format.args": "--line-length 80"` → `"ruff.lineLength": 80`; use
  `configuration` for the rest.
- `path` and `interpreter` remain extension settings in VS Code; the server
  does not accept them.
- Uninstall the `ruff-lsp` package and point Neovim/Vim configs at `ruff`
  (`ruff server`), not `ruff_lsp`.

## pre-commit

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.16.8 # the project's Ruff version; check the latest tag first
    hooks:
      - id: ruff-check
        args: [--fix]
      - id: ruff-format
```

- Hook ids are `ruff-check` and `ruff-format`; `ruff` is a legacy alias of
  `ruff-check`.
- With `--fix`, `ruff-check` goes before `ruff-format` and before Black, isort,
  or any other formatter. Without `--fix` order does not matter.
- Both hooks run with `--force-exclude`, so the project's `exclude` applies.
- Default `types_or`: `python`, `pyi`, `jupyter`, and for `ruff-format` also
  `markdown`. Drop notebooks with `types_or: [python, pyi]`; lint
  `pyproject.toml` with `types_or: [python, pyi, jupyter, pyproject]`
  (needs `identify >= 2.6.18`).
- [prek](https://prek.j178.dev/) reads the same `.pre-commit-config.yaml`.
- A failing hook is fixed, never skipped with `--no-verify` or `SKIP=`.

## GitHub Actions

Follow the repository's pinning policy (many require a full commit SHA with a
version comment) before adding a step. CI checks; it never fixes.

With `astral-sh/ruff-action` (v4.1.0 on the verification date):

```yaml
- uses: astral-sh/ruff-action@<SHA or tag> # v4.x
  with:
    version: "0.16.8" # or version-file: uv.lock
    args: check --output-format github
- uses: astral-sh/ruff-action@<SHA or tag>
  with:
    version: "0.16.8"
    args: format --check --output-format github
```

- Inputs: `version` (else `version-file`, else the nearest `pyproject.toml`
  above `src`, else `latest`), `version-file` (`pyproject.toml`,
  `requirements.txt`, `uv.lock`), `args` (default `check`), `src`,
  `checksum`, `github-token`. Never leave the version at `latest`.

With the project's own locked environment:

```yaml
- run: uv run --locked --no-python-downloads ruff check --output-format github .
- run: uv run --locked --no-python-downloads ruff format --check --output-format github .
```

(Install Python with `actions/setup-python` or `uv python install` in an
explicit step first, so no download happens implicitly.)

- `--output-format github` produces inline annotations; `format --check`
  supports output formats since 0.16.0. Others: `concise`, `full`, `json`,
  `json-lines`, `junit`, `grouped`, `gitlab`, `pylint`, `rdjson`, `azure`,
  `sarif`. `RUFF_OUTPUT_FORMAT` sets the default.

## Other CI

- GitLab: the `ghcr.io/astral-sh/ruff:<version>-alpine` image, with
  `--output-format gitlab` for code-quality reports.
- Docker tags: `latest`, `<major>.<minor>.<patch>`, and `-alpine` / Debian
  variants.
- Any CI: run the same commands through the project's environment, no
  `--fix`, no `ruff format` without `--check`.
