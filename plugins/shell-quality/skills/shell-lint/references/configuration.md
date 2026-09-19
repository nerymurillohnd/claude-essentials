# ShellCheck and shfmt configuration in depth

Verified against ShellCheck 0.11.0, shfmt 3.14.1, `man shellcheck`, and the
shfmt man page (v3.14.1 tag) on 2026-09-19.

## ShellCheck rc files

| Situation | What ShellCheck does |
| --- | --- |
| `.shellcheckrc` and a parent `.shellcheckrc` | Uses the closest one only |
| No project rc | `~/.shellcheckrc`, else `$XDG_CONFIG_HOME/shellcheckrc` (usually `~/.config/shellcheckrc`) |
| Snap install | Cannot read hidden files: name it `shellcheckrc` |
| Docker | Only mounted files are visible; `~/.shellcheckrc` is not |
| `--rcfile FILE` (0.10+) | That file, instead of searching |
| `--norc` | No rc file at all |
| `SHELLCHECK_OPTS='--external-sources -o all'` | Extra command-line flags, split on spaces |

An rc file holds `key=value` lines that act as file-wide directives:
`external-sources`, `source-path`, `enable`, `disable`, `shell`, `severity`,
`extended-analysis`. Directives inside a script override the rc for that script.

## shfmt and EditorConfig

- shfmt reads `.editorconfig` from the script's directory up to a file with
  `root = true`, merging matching sections (later ones win).
- Passing **any** parser or printer flag (`-i`, `-ln`, `-p`, `-s`, `-bn`, `-ci`,
  `-sr`, `-kp`, `-fn`, `-mn`) makes shfmt ignore EditorConfig completely.
  Tested in 3.14.1: `shfmt -s` turned a 2-space EditorConfig indent back into
  tabs.
- Section `[*.sh]` does not match `.bats` files or extensionless scripts;
  shfmt's `[[shell]]` (every shell language) and `[[bash]]` sections do.
  Other EditorConfig tools ignore these sections.
- `ignore = true` skips files when shfmt walks a directory; for files named on
  the command line it only applies with `--apply-ignore`.
- `--filename path` lets stdin input pick up EditorConfig.
- `-ln`/`shell_variant`: `bash`, `posix`, `mksh`, `bats`, `zsh`, or `auto`
  (extension, then shebang, then bash).
- Unreleased on master (not in 3.14.1): `language_dialect`, `case_indent`,
  `-bl`. Use the 3.14.1 keys until a release ships them.

## The recommended profile, explained

The shell-hooks skill can install this profile (in the plugin:
`skills/shell-hooks/assets/shellcheckrc` and `editorconfig-shell`).

| Setting | Why |
| --- | --- |
| `external-sources=true`, `source-path=SCRIPTDIR` | Sourced files are analyzed, found relative to each script |
| The ten optional checks, enabled by name | Masked return values, `set -e` traps, missing default cases, braces, nullary and negated tests, `which`, useless `cat`, unassigned uppercase variables, unquoted safe variables |
| No `shell=`, no `enable=all`, no `disable=` | See the anti-patterns in [sc-codes.md](sc-codes.md) |
| `[[shell]]`: 2-space indent, `switch_case_indent`, `binary_next_line`, `simplify` | The Google Shell Style Guide (equivalent to `shfmt -i 2 -ci -bn -s`), applied to every shell script including extensionless ones |

## Migrating to ShellCheck and shfmt

| From | To | Notes |
| --- | --- | --- |
| `bash -n script` | `shellcheck script` (parses and analyzes) | Keep `bash -n` only as a smoke test in the target bash |
| checkbashisms | ShellCheck on `#!/bin/sh` scripts (SC3xxx) | ShellCheck covers the same ground with explanations |
| beautysh, `bash-beautify`, editor reindenters | shfmt with EditorConfig | Reformat in one dedicated commit (add it to `.git-blame-ignore-revs`) |
| `shfmt -i 2 -ci` in scripts, CI, and pre-commit args | The same style as EditorConfig keys | One source of truth; plain `shfmt -d .` in CI |
| An rc file with `shell=bash` | Correct shebangs, or a `# shellcheck shell=` directive in the few files without one | `shell=` in an rc hides POSIX findings |
| An rc file full of `disable=` | Fix the findings, or move each justified exception inline next to its code with a reason | Each removal is a decision for the user |
| `.shellcheckrc` for ShellCheck < 0.10 | `--rcfile` and `extended-analysis` need 0.10; `useless-use-of-cat` and `avoid-negated-conditions` need 0.11 | Pin the version in CI |
| Ubuntu `apt install shellcheck` (0.9.0 on ubuntu-24.04 runners) | A pinned release binary | Older versions miss 0.10–0.11 checks |
