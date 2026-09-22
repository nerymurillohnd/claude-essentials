---
name: shell-lint
description: Lint and format shell scripts with shfmt and ShellCheck, fixing every finding in the script instead of silencing it. Covers installing both tools without breaking a project pin, the order that works (format, then check), exit codes and output formats, how each tool discovers its configuration and which file wins, SHELLCHECK_OPTS, the shfmt keys of EditorConfig, the correct code change for the SC codes met most often, POSIX and macOS bash 3.2 portability, editor, pre-commit and CI wiring, the suppressions that must never be added, and how to answer the shell-quality hook when it reports findings or asks the user to confirm a directive. Confirm the installed versions and read both changelogs before relying on version-specific behavior.
when_to_use: On every shell script Claude writes, edits, reviews or fixes (.sh, .bash, .bats, or an extensionless file with a sh, bash, dash or ksh shebang), before calling that work done, not only when the user asks. Also when the shell-quality hook reports shfmt or ShellCheck findings, to fix an SC code such as SC2086, SC2155 or SC2016, to install ShellCheck or shfmt, to set up .shellcheckrc or the shfmt keys of .editorconfig, to make a script POSIX or able to run on macOS bash 3.2, or to wire either tool into pre-commit, CI or an editor.
compatibility: Claude Code, Claude Cowork, and any Agent Skills host. The commands need shellcheck 0.10 or later and shfmt 3.13 or later; the guidance works without them. The after-edit hook runs only where plugin hooks run.
license: Apache-2.0
---

# Shell lint

shfmt formats shell scripts; ShellCheck finds their bugs. Verified on
**2026-09-22** against **ShellCheck 0.11.0** and **shfmt v3.14.1**, by running
both binaries. Before relying on version-specific behavior, run
`shellcheck --version` and `shfmt --version` and read the
[ShellCheck changelog](https://github.com/koalaman/shellcheck/blob/master/CHANGELOG.md)
and the [shfmt changelog](https://github.com/mvdan/sh/blob/master/CHANGELOG.md).
The man pages on `master` can describe unreleased behavior: shfmt's `master`
page documents `language_dialect`, `case_indent`, `block_next_line`, and `-bl`,
which v3.14.1 does not have.

## Non-negotiable rules

1. **Fix findings in the script.** Never add any of these to get a clean run:
   `# shellcheck disable=…` (including `disable=all`),
   `# shellcheck source=/dev/null`, `disable=` in a `.shellcheckrc`,
   `-e`/`--exclude`, `SHELLCHECK_OPTS='-e …'`, a raised `--severity`,
   `--norc` to dodge the project rc, or `ignore = true` in `.editorconfig`.
   If a finding looks wrong, show why and let the user decide; a suppression
   is theirs to add.
2. **Respect the project's configuration.** Read `.shellcheckrc` and
   `.editorconfig` first. Never pass a shfmt parser or printer flag (`-i`,
   `-ln`, `-p`, `-s`, `-bn`, `-ci`, `-sr`, `-kp`, `-fn`, `-mn`) where
   EditorConfig exists: any one of them makes shfmt ignore every EditorConfig
   formatting key.
3. **Stay in scope.** Format and check the scripts being changed. Ask before
   reformatting a tree that was never shfmt-formatted.
4. **Target the real shell.** The shebang sets the dialect. `#!/bin/sh` means
   POSIX. `#!/usr/bin/env bash` on a stock Mac runs `/bin/bash` 3.2.
5. **Never install or upgrade a tool silently.** Use the project's pinned
   install first; propose an install and let the user run or approve it.

## The workflow for every change

```bash
shfmt -w -- script.sh              # 1. format: it moves lines
shellcheck -x -f gcc -- script.sh  # 2. check the settled file, one finding per line
```

- Format first; checking first leaves stale line numbers.
- Read the wiki page before fixing an unfamiliar code:
  `https://www.shellcheck.net/wiki/SC2086`.
- Re-run both tools until ShellCheck exits `0`, then report: scripts touched,
  what shfmt changed, each finding and its fix, anything left and why.

| Tool | Exit codes (verified with the binaries) |
| --- | --- |
| ShellCheck | `0` clean · `1` findings, including SC1071 for zsh · `2` a file could not be read · `3` bad invocation syntax (an unknown flag) · `4` bad option value (`-s zsh`, `-f nope`, `-S nope`) |
| shfmt | `0` success · `1` `-d`/`-l` found differences, or a parse error · `2` bad flag |

Useful ShellCheck flags: `-x` follows `source` into files not on the command
line; `-P SCRIPTDIR` sets the source search path; `-S error|warning|info|style`
filters the report (never to hide findings); `-o NAME` enables an optional
check (`shellcheck --list-optional` lists them); `-f gcc|tty|json1|checkstyle|diff|quiet`
chooses output. `-f diff` prints a patch for the auto-fixable subset, which
you review before applying. `-a` also reports findings inside sourced files.

Useful shfmt flags: `-d` prints a diff without writing; `-l` lists files that
differ; `-f .` lists shell files found by extension and shebang; `--filename`
names stdin so EditorConfig applies. In loops and CI, pass files as arguments
or use `xargs`; `find … -exec shellcheck {} \;` exits `0` whatever it finds.

## How the tools find their configuration

**ShellCheck** looks for `.shellcheckrc`, then `shellcheckrc`, in the script's
directory and each parent; then `~/.shellcheckrc`; then
`$XDG_CONFIG_HOME/shellcheckrc` (`%APPDATA%\shellcheckrc` on Windows). **The
first file found is the only one read; nothing merges.** A project rc hides a
user's global rc completely. `--rcfile FILE` reads that file instead of
searching; `--norc` reads none. `SHELLCHECK_OPTS` is split on spaces and
**prepended** to the arguments: flags given on the command line win, and it
still applies with `--norc`. When a finding appears or disappears unexpectedly,
check `echo "${SHELLCHECK_OPTS-}"` and name it in the report.

**shfmt** reads EditorConfig: every `.editorconfig` from the script's directory
up to one with `root = true`, the nearer file winning per key. `[*.sh]` misses
extensionless scripts and `.bats`; the shfmt-only sections `[[shell]]`,
`[[bash]]` and `[[zsh]]` match by detected language. `ignore = true` applies
when walking a directory and to explicit files only with `--apply-ignore`.

Depth, verified experiments, and every key:
[references/configuration.md](references/configuration.md).

## Fixes for the codes you will meet most

| Code | Correct change |
| --- | --- |
| SC2086 | Quote the expansion, `"${var}"`; for a deliberate list use an array, `"${args[@]}"` |
| SC2046 | Quote `"$(cmd)"`; to split on purpose, `read -r -a parts <<<"$(cmd)"` |
| SC2155 | `local out; out=$(cmd)` so `cmd`'s failure is not masked |
| SC2016 | Want expansion: double quotes. Want a literal `$`: `jq --arg n "${n}" '…$n…'`, or `"\$HOME"` |
| SC2034 | Delete the variable or use it; `_` placeholders (`read -r _ b`) are exempt |
| SC2154 | Assign it, or require it: `: "${VAR:?VAR must be set}"` |
| SC1090/SC1091 | `source-path=SCRIPTDIR` plus `-x` (or `external-sources=true`), or `# shellcheck source=lib/x.sh` naming the real file |
| SC2329 | Call the function, delete it, or for a `trap` handler inline the command: `trap 'rm -f -- "${tmp}"' EXIT` |
| SC2312 | Capture first, `now=$(date)`, then use `"${now}"` |

Every other common code, POSIX SC3xxx codes, and the optional checks:
[references/sc-codes.md](references/sc-codes.md).

`set -euo pipefail` is not a safety net: `set -e` is off inside `if`, `&&`,
`||`, and functions called from them, and it never sees the failures SC2155
and SC2312 describe.

## Portability

ShellCheck takes the dialect from a `# shellcheck shell=` directive, then the
shebang, then the extension; `-s` overrides all three. zsh is not supported
(SC1071). ShellCheck does **not** check Bash versions: `declare -A`, `mapfile`,
`${x,,}`, `[[ -v x ]]`, `local -n`, `${x@Q}`, and `"${a[@]}"` of an empty
array under `set -u` all pass lint and fail on `/bin/bash` 3.2 (verified on
macOS). Use `${a[@]+"${a[@]}"}`, `while IFS= read -r` loops, and `tr` for case,
and test with `/bin/bash script.sh`. Details:
[references/sc-codes.md](references/sc-codes.md#portability).

## Directives: recognize them, never add them

A directive after the shebang and before the first command applies to the
whole file; elsewhere it covers only the next command (a whole function, loop,
`if`, or `case`). Read them when reviewing code, question the ones without a
reason comment, and propose removing each by fixing the code. Adding one is
the user's decision.

## Responding to the shell-quality hook

The plugin ships hooks that run after Claude writes or edits a `.sh` or `.bash`
file: `shfmt -w`, then `shellcheck -x -f gcc` from the script's directory, on
the whole file, with each tool's native configuration discovery and
`SHELLCHECK_OPTS`, using the project install or the `PATH` (never a download).
zsh scripts are skipped.

- **Findings reported after an edit:** fix them in the script, re-read the
  file (shfmt may have rewritten it), and continue. A long report is cut
  short; run ShellCheck yourself to see the rest. Do not argue with the hook
  or reach for a directive.
- **Stop is blocked:** a touched script still has findings. Fix them; the hook
  keeps Claude working up to 7 times, and the 8th attempt ends with a failure
  message to the user. If a finding truly cannot be fixed, say so plainly with
  the code, the line, and the reason.
- **A confirmation prompt:** adding a `# shellcheck disable=` or
  `source=/dev/null` directive, changing `.shellcheckrc` or `shellcheckrc`, or
  changing the sections or shfmt keys of `.editorconfig` (by an edit or a Bash
  command) asks the user first. Expect the prompt; never reshape an edit or a
  command to avoid it.
- **A tool is missing** (shfmt, ShellCheck, or `jq`, which the hook needs):
  the hook tells the user once per session how to
  install it and does not block. Offer the install from
  [references/pipelines.md](references/pipelines.md#installing); do not run it
  unasked.
- **`SHELLCHECK_OPTS` is named in a report:** it changed what ShellCheck saw.
  Tell the user; do not unset it for them.

## Additional resources

- [references/sc-codes.md](references/sc-codes.md): code-by-code fixes,
  POSIX and bash 3.2 portability, the optional checks, and anti-patterns.
- [references/configuration.md](references/configuration.md): rc discovery,
  `SHELLCHECK_OPTS`, rc keys, shfmt and EditorConfig keys by version, and
  migration from other tools.
- [references/pipelines.md](references/pipelines.md): installing, pinning,
  pre-commit, GitHub Actions, editors and LSP.
