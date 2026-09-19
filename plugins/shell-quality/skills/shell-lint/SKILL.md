---
name: shell-lint
description: This skill should be used whenever Claude writes, edits, reviews, or fixes a shell script (.sh, .bash, .bats, or an extensionless file with a sh/bash/dash/ksh shebang), and when the user asks to "run ShellCheck", "fix SC2086 / SC2155 / an SC code", "format with shfmt", "set up .shellcheckrc", "configure shfmt / EditorConfig for shell", "make this script portable / POSIX / work on macOS bash 3.2", "migrate from bash -n / beautysh / checkbashisms to ShellCheck and shfmt", "add ShellCheck or shfmt to pre-commit", or "lint shell scripts in CI / GitHub Actions". It teaches the current ShellCheck 0.11 and shfmt 3.14 workflow (format, then check), how both tools find their configuration, correct fixes for the common SC codes, and why findings are fixed in the script instead of silenced. For installing the Claude Code after-edit hook, use the shell-hooks skill instead.
compatibility: Claude Code, Claude Cowork, and any Agent Skills host. Needs shellcheck >= 0.10 and shfmt >= 3.12 to run commands; the guidance works without them.
license: Apache-2.0
---

# Shell lint

ShellCheck finds bugs in shell scripts; shfmt formats them. This skill covers
**ShellCheck 0.11** and **shfmt 3.14**. When installed versions differ, check
`shellcheck --version` and `shfmt --version` and the
[ShellCheck changelog](https://github.com/koalaman/shellcheck/blob/master/CHANGELOG.md)
before relying on version-specific behavior.

## Non-negotiable rules

1. **Fix findings in the script.** Never add `# shellcheck disable=...`,
   `# shellcheck disable=all`, or `# shellcheck source=/dev/null` to make a
   check pass; never add `disable=` to an rc file, set `SHELLCHECK_OPTS`, pass
   `-e`/`--exclude`/`--severity`/`--norc`, or add `ignore = true` to
   `.editorconfig` to get a green run. If a finding looks wrong, explain why
   and let the user decide; the suppression is theirs to add.
2. **Respect the project's configuration.** Read `.shellcheckrc` and
   `.editorconfig` first. Do not pass shfmt style flags (`-i`, `-ci`, `-bn`,
   `-s`, `-ln`, …) in a project that has EditorConfig: **any** parser or
   printer flag makes shfmt ignore EditorConfig entirely.
3. **Stay in scope.** Format and check the scripts being changed; ask before
   reformatting a whole tree that was never shfmt-formatted.
4. **Target the real shell.** The shebang decides the dialect. A `#!/bin/sh`
   script must be POSIX; a `#!/usr/bin/env bash` script may run on macOS's
   `/bin/bash` 3.2 (see below).

## The workflow for every change

```bash
shfmt -w -- <script>            # format first: it moves lines
shellcheck -f gcc -- <script>   # then check the settled file; one finding per line
```

- Order matters: formatting after checking makes the reported line numbers
  wrong.
- Exit codes: ShellCheck `0` clean, `1` findings (including parse errors),
  `2` a file could not be processed, `3` bad syntax in options, `4` bad
  options. shfmt `-w` exits `0`; `-d` and `-l` exit `1` when a file would
  change; a parse error exits `1`; a bad flag exits `2`.
- Read the explanation of every code before fixing it:
  `https://www.shellcheck.net/wiki/SC2086`.
- `shfmt -d` shows a diff without writing; `shfmt -l` lists files that would
  change. `shfmt -p -d` (or `-ln=posix`) is a stricter syntax check than
  `bash -n` for POSIX scripts, but it is a style flag (rule 2).
- In CI and loops use `shellcheck file1 file2 …` or
  `find … -print0 | xargs -0 shellcheck`; `find … -exec shellcheck {} \;`
  always exits `0` and hides failures.

End with a short report: scripts and scope, what shfmt changed, which findings
were fixed and how, and anything left with the reason.

## How the tools find their configuration

**ShellCheck** reads `.shellcheckrc` or `shellcheckrc` from the script's
directory and each parent, then `~/.shellcheckrc`, then
`$XDG_CONFIG_HOME/shellcheckrc` (usually `~/.config/shellcheckrc`;
`%APPDATA%\shellcheckrc` on Windows). **The first file found wins; nothing
merges**: a project rc silently replaces a user's global one. `--rcfile FILE`
(0.10+) forces one file; `--norc` ignores them all. The only environment
variable is `SHELLCHECK_OPTS` (extra flags, split on spaces); there is no
`SHELLCHECK_SHELL`, `SHELLCHECK_STRICT`, or `SHELLCHECK_CONFIG`.

Useful rc keys: `external-sources=true` (follow `source` outside the checked
files; only effective in an rc file), `source-path=SCRIPTDIR` (resolve sources
relative to each script), `enable=<optional check>`. Never put `shell=` in an
rc file: rc entries apply file-wide, so it overrides every shebang and hides
POSIX findings. Never `enable=all`: the optional checks are opinions and some
conflict.

**shfmt** reads EditorConfig (`.editorconfig` files up to one with
`root = true`). Keys in 3.14: `indent_style`, `indent_size`, `shell_variant`,
`binary_next_line`, `switch_case_indent`, `space_redirects`,
`function_next_line`, `simplify`, `minify`, `ignore` (`keep_padding` is
deprecated). `[*.sh]` sections miss `.bats` files and extensionless scripts;
shfmt's `[[shell]]` and `[[bash]]` sections match by language instead. `ignore
= true` applies to explicit file arguments only with `--apply-ignore`.

## Target shell and portability

ShellCheck picks the dialect from a `# shellcheck shell=` directive, then the
shebang, then the extension (`.bash`, `.bats`, `.dash`, `.ksh`); `-s` overrides
all of them. A file with none of these gets `SC2148`. zsh is not supported.

`#!/usr/bin/env bash` on a stock Mac finds `/bin/bash` **3.2**. ShellCheck does
**not** check Bash versions, so these pass lint and then fail at run time:
`declare -A`, `mapfile`/`readarray`, `${var,,}`/`${var^^}`, `local -n`,
`[[ -v var ]]`, `wait -n`, `${var@Q}`, `shopt -s inherit_errexit`, and (before
Bash 4.4) `"${arr[@]}"` of an empty array under `set -u`. Use
`${arr[@]+"${arr[@]}"}`, `while IFS= read -r` loops, and `tr` for case changes,
and test with `/bin/bash script.sh` when macOS support matters.

## Fixes for the codes you will meet most

The full list, with correct and incorrect fixes, is in
[`references/sc-codes.md`](references/sc-codes.md). The essentials:

- **SC2086** unquoted expansion: quote it, `"${var}"`; for deliberate word
  lists use an array, `"${args[@]}"`.
- **SC2046** unquoted `$(…)`: quote it; to split on purpose,
  `read -r -a parts <<<"$(cmd)"`.
- **SC2155** `local x=$(cmd)` hides `cmd`'s failure: `local x; x=$(cmd)`.
- **SC2164** `cd dir` without a check: `cd dir || exit 1` (`|| return` in a
  function).
- **SC2181** `if [ $? -ne 0 ]`: test the command directly, `if ! cmd; then`.
- **SC2206/SC2207** array from unquoted expansion: `read -r -a arr <<<"${v}"`;
  lines: `while IFS= read -r l; do arr+=("${l}"); done < <(cmd)`.
- **SC2034** unused variable: remove it, or use it; `_`-prefixed names are
  exempt for deliberate placeholders.
- **SC1090/SC1091** unresolved `source`: add `source-path=SCRIPTDIR` (rc or a
  `# shellcheck source-path=` directive before the first command) or a
  `# shellcheck source=relative/path.sh` directive that names the real file.
- **SC2312** (optional) status of `$(cmd)` lost inside another command: assign
  it first, `out=$(cmd)`, then use `"${out}"`.
- **SC2250** (optional) braces: `${var}`.

`set -e` is not a safety net: it is suspended inside `if`, `&&`, `||`, and
functions called from them, and it does not see failures masked by SC2155 or
SC2312. Enable `check-set-e-suppressed` to find those places.

## Directives: where they apply

A directive before the first command applies to the whole file; otherwise it
applies to the next command (a whole function, loop, `if`, or `{ }` block), and
in `a; b` only to `a`. A reason may follow on the same line after another `#`.
Recognize directives when you read code; adding one is the user's decision.

## Additional resources

- [`references/sc-codes.md`](references/sc-codes.md) — the common codes with
  correct fixes, the optional checks worth enabling, and anti-patterns.
- [`references/configuration.md`](references/configuration.md) — rc files and
  EditorConfig in depth, the recommended profile explained, and migration from
  `bash -n`, beautysh, checkbashisms, and older rc files.
- [`references/pipelines.md`](references/pipelines.md) — pre-commit, GitHub
  Actions and other CI, editors, and keeping every version pin equal.
