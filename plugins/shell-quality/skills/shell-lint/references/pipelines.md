# ShellCheck and shfmt in pre-commit, CI, and editors

Verified on 2026-09-19 (ShellCheck 0.11.0, shfmt 3.14.1). Look up current
releases before writing a pin (`gh release view --repo koalaman/shellcheck`,
`gh release view --repo mvdan/sh`); never write a version from memory.

## One version everywhere

Pin the same ShellCheck and shfmt versions in pre-commit, CI, and developer
setup notes. A newer ShellCheck adds checks; an older one misses them.

## pre-commit

```yaml
repos:
  - repo: https://github.com/scop/pre-commit-shfmt
    rev: v3.14.1-1
    hooks:
      - id: shfmt # formats with EditorConfig; add no style args
  - repo: https://github.com/koalaman/shellcheck-precommit
    rev: v0.11.0
    hooks:
      - id: shellcheck
```

- shfmt before ShellCheck, so line numbers are final.
- Do not pass `args: [-i, "2"]` to shfmt when the repository has EditorConfig.
- `shellcheck-precommit` runs ShellCheck in Docker; `shellcheck-py`
  (`rev: v0.11.0.1`) installs a binary through pip instead.
- A failing hook is fixed, never skipped with `--no-verify`.

## GitHub Actions

Pin actions to a full commit SHA if the repository requires it. The
ubuntu-24.04 runner image and its apt ship ShellCheck 0.9.0, so install a
pinned, checksum-verified release instead:

```yaml
- name: Install ShellCheck and shfmt (pinned)
  env:
    SHELLCHECK_VERSION: "0.11.0"
    SHFMT_VERSION: "3.14.1"
  run: |
    set -euo pipefail
    tmp="$(mktemp -d)"
    curl -fsSL -o "${tmp}/sc.tar.xz" "https://github.com/koalaman/shellcheck/releases/download/v${SHELLCHECK_VERSION}/shellcheck-v${SHELLCHECK_VERSION}.linux.x86_64.tar.xz"
    tar -xJf "${tmp}/sc.tar.xz" -C "${tmp}"
    sudo install -m 0755 "${tmp}/shellcheck-v${SHELLCHECK_VERSION}/shellcheck" /usr/local/bin/shellcheck
    curl -fsSL -o "${tmp}/shfmt" "https://github.com/mvdan/sh/releases/download/v${SHFMT_VERSION}/shfmt_v${SHFMT_VERSION}_linux_amd64"
    sudo install -m 0755 "${tmp}/shfmt" /usr/local/bin/shfmt
- name: Lint shell scripts
  run: |
    shfmt -d .
    shfmt -f . | xargs shellcheck -f gcc
```

Add a `sha256sum --check` of each download for supply-chain safety.
Alternatives: `reviewdog/action-shellcheck` and `reviewdog/action-shfmt`
(review comments), `luizm/action-sh-checker` (both tools).

- CI checks, it never formats: `shfmt -d`, not `-w`.
- `shfmt -f .` lists shell files (by extension and shebang) for ShellCheck.
- `-f gcc` gives one line per finding; `-f checkstyle` or `-f json1` feed
  other tools; `-f diff` produces a patch for the auto-fixable subset.

## Editors

- VS Code: the ShellCheck extension (`timonwong.shellcheck`) and a shfmt-based
  formatter; bash-language-server runs both.
- Neovim: bash-language-server (ShellCheck diagnostics, shfmt formatting).
- Keep the editor on the repository's rc file and EditorConfig; do not set
  shfmt flags in editor settings.

## Claude Code

- The shell-quality plugin's `shell-hooks` skill installs an after-edit gate
  (shfmt and ShellCheck on every script Claude edits, plus a Stop gate).
