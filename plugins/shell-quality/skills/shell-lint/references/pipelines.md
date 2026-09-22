# Installing, pinning, pre-commit, CI, and editors

Verified on 2026-09-22 (ShellCheck 0.11.0, shfmt v3.14.1). Release numbers
change: look up the current ones before writing a pin
(`gh release view --repo koalaman/shellcheck`, `gh release view --repo mvdan/sh`,
or the releases pages), never from memory. Sources: the
[ShellCheck README](https://github.com/koalaman/shellcheck/blob/master/README.md),
the [shfmt README](https://github.com/mvdan/sh/blob/master/README.md), the
[bash-language-server README](https://github.com/bash-lsp/bash-language-server/blob/main/README.md).

## Contents

- [Installing](#installing)
- [One version everywhere](#one-version-everywhere)
- [pre-commit](#pre-commit)
- [GitHub Actions and other CI](#github-actions-and-other-ci)
- [Editors and LSP](#editors-and-lsp)

## Installing

Prefer what the project already pins; propose an install and let the user run
it. Never install or upgrade silently.

| Route | ShellCheck | shfmt |
| --- | --- | --- |
| macOS (Homebrew) | `brew install shellcheck` | `brew install shfmt` |
| Debian/Ubuntu | `sudo apt install shellcheck` (Ubuntu 24.04 ships 0.9.0) | `sudo apt install shfmt` |
| Fedora | `dnf install ShellCheck` | `dnf install shfmt` |
| Arch | `pacman -S shellcheck` | `pacman -S shfmt` |
| Windows | `winget install --id koalaman.shellcheck`, `scoop install shellcheck`, `choco install shellcheck` | `scoop install shfmt` |
| Go toolchain | none | `go install mvdan.cc/sh/v3/cmd/shfmt@v3.14.1` |
| Container | `docker run --rm -v "$PWD:/mnt" koalaman/shellcheck:stable script.sh` | `mvdan/shfmt` image (tag `v3`, or an exact version) |
| Release binary | [GitHub releases](https://github.com/koalaman/shellcheck/releases): Linux x86_64/aarch64/armv6hf, macOS x86_64/aarch64, Windows | [GitHub releases](https://github.com/mvdan/sh/releases): one static binary per OS and arch |
| Python dev dependency | `shellcheck-py` | `shfmt-py` |

**As project dev dependencies (Python projects).** `shellcheck-py` and
`shfmt-py` put the real binaries into the virtualenv, so every contributor and
CI job gets the same version from the lockfile:

```bash
uv add --dev shellcheck-py shfmt-py   # or pin exact versions in pyproject.toml
uv run shellcheck --version
uv run shfmt --version
```

Their versions differ from the tools': `shellcheck-py` 0.11.0.1 carries
ShellCheck 0.11.0, while `shfmt-py` 4.2.0 carries shfmt v3.14.1 (both measured
in this repository's venv). Always confirm with `--version` after installing.

Distribution packages lag: Ubuntu 24.04 (`noble`) ships ShellCheck 0.9.0-1
([packages.ubuntu.com](https://packages.ubuntu.com/noble/shellcheck)), which
lacks every 0.10.0 and 0.11.0 check and flag.

## One version everywhere

Pin the same ShellCheck and shfmt versions in the developer setup, pre-commit,
CI, and the editor. A newer ShellCheck adds checks (0.11.0 added SC2329 and
moved SC2002 to optional); an older one misses them, and results differ
between machines.

## pre-commit

```yaml
repos:
  - repo: https://github.com/scop/pre-commit-shfmt
    rev: v3.14.1-1          # check the current tag
    hooks:
      - id: shfmt           # prebuilt binary; shfmt-src builds with Go, shfmt-docker uses Docker
  - repo: https://github.com/shellcheck-py/shellcheck-py
    rev: v0.11.0.1-1        # check the current tag; see the repo's README
    hooks:
      - id: shellcheck
```

- shfmt runs before ShellCheck so line numbers are final.
- Never add style `args` (`-i`, `-ci`, …) to the shfmt hook in a repository
  with EditorConfig. Since `pre-commit-shfmt` 3.12.0-2 its default args no
  longer include `-s`.
- [koalaman/shellcheck-precommit](https://github.com/koalaman/shellcheck-precommit)
  (`rev: v0.11.0`) is the upstream hook; it runs ShellCheck in Docker.
- A failing hook is fixed, never skipped with `--no-verify`.

## GitHub Actions and other CI

CI checks and never formats: `shfmt -d`, not `-w`. Install pinned,
checksum-verified binaries (or `uv sync` when the tools are dev dependencies)
instead of the runner's apt package:

```yaml
- name: Install ShellCheck and shfmt (pinned)
  env:
    SHELLCHECK_VERSION: "0.11.0"
    SHFMT_VERSION: "3.14.1"
  run: |
    set -euo pipefail
    tmp="$(mktemp -d)"
    curl -fsSL -o "${tmp}/sc.tar.xz" \
      "https://github.com/koalaman/shellcheck/releases/download/v${SHELLCHECK_VERSION}/shellcheck-v${SHELLCHECK_VERSION}.linux.x86_64.tar.xz"
    tar -xJf "${tmp}/sc.tar.xz" -C "${tmp}"
    sudo install -m 0755 "${tmp}/shellcheck-v${SHELLCHECK_VERSION}/shellcheck" /usr/local/bin/shellcheck
    curl -fsSL -o "${tmp}/shfmt" \
      "https://github.com/mvdan/sh/releases/download/v${SHFMT_VERSION}/shfmt_v${SHFMT_VERSION}_linux_amd64"
    sudo install -m 0755 "${tmp}/shfmt" /usr/local/bin/shfmt
- name: Lint shell scripts
  run: |
    shfmt -d .
    shfmt -f . | xargs shellcheck -x -f gcc
```

- Add a `sha256sum --check` of each download against a committed checksum.
- Pin every third-party action to a full commit SHA.
- `shfmt -f .` lists shell files by extension and shebang, honoring
  EditorConfig `ignore`; feed that list to ShellCheck so both tools check the
  same set. Use `shfmt -f=0 . | xargs -0 …` when paths may contain spaces.
- `-f gcc` gives one line per finding; `-f checkstyle` and `-f json1` feed
  annotation tools; `-f diff` prints a patch of the auto-fixable subset.
- Make sure no `SHELLCHECK_OPTS` is set in the job environment unless the
  repository documents it.
- Wrappers exist (for example `reviewdog/action-shellcheck`,
  `luizm/action-sh-checker`), but a two-line script over pinned binaries is
  easier to audit.

## Editors and LSP

- **bash-language-server** (`npm i -g bash-language-server`) runs ShellCheck
  on every change when `shellcheck` is on `PATH` (`shellcheckPath`,
  `shellcheckArguments` settings) and formats with shfmt when installed
  (`shfmtPath`). It reads `.editorconfig` for shfmt unless its "Ignore
  Editorconfig" setting is on. VS Code client: the "Bash IDE" extension.
- Its ShellCheck quick fix inserts `# shellcheck disable=SC…`. Do not accept
  it: fix the code.
- VS Code alternatives: `timonwong.shellcheck` (vscode-shellcheck) and
  `mkhl.shfmt` (vscode-shfmt). Point them at the project's pinned binaries
  (for example the venv's `bin/`), and put no shfmt style flags in editor
  settings.
- Vim/Neovim: ALE or an LSP client with bash-language-server. Emacs: Flycheck
  or Flymake plus `shfmt.el`. JetBrains: BashSupport Pro or the bundled Shell
  Script plugin.
- Editors, pre-commit, CI, and the shell-quality hook should all use the same
  binaries and the same rc and EditorConfig, so a clean result in one is a
  clean result in all.
