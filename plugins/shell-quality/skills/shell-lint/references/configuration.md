# ShellCheck and shfmt configuration in depth

Verified on 2026-09-22 against ShellCheck 0.11.0 and shfmt v3.14.1. Each
"measured" statement below was run with the real binaries in a scratch
directory with `HOME` and `XDG_CONFIG_HOME` pointed at empty scratch folders.
Sources: the ShellCheck [man page](https://github.com/koalaman/shellcheck/blob/master/shellcheck.1.md),
the [Directive wiki page](https://github.com/koalaman/shellcheck/wiki/Directive),
the shfmt man page at the release tag
([v3.14.1](https://github.com/mvdan/sh/blob/v3.14.1/cmd/shfmt/shfmt.1.scd)),
and [editorconfig.org](https://editorconfig.org).

## Contents

- [ShellCheck rc files](#shellcheck-rc-files)
- [SHELLCHECK_OPTS](#shellcheck_opts)
- [rc keys and directives](#rc-keys-and-directives)
- [shfmt and EditorConfig](#shfmt-and-editorconfig)
- [EditorConfig keys by shfmt version](#editorconfig-keys-by-shfmt-version)
- [Migrating to ShellCheck and shfmt](#migrating-to-shellcheck-and-shfmt)

## ShellCheck rc files

Search order, per the man page: `.shellcheckrc` or `shellcheckrc` in the
script's directory, then each parent; then `~/.shellcheckrc`; then
`$XDG_CONFIG_HOME/shellcheckrc` (on Windows `%APPDATA%/shellcheckrc`). Only
the first file found is used.

| Measured case (each rc disabled a different code) | Result |
| --- | --- |
| rc in the script's directory and in its parent | Only the script-directory rc applied |
| Project rc (parent directory) and `~/.shellcheckrc` | Only the project rc applied |
| `~/.shellcheckrc` and `$XDG_CONFIG_HOME/shellcheckrc` | Only `~/.shellcheckrc` applied |
| Only `$XDG_CONFIG_HOME/shellcheckrc` | It applied |
| `.shellcheckrc` and `shellcheckrc` in the same directory | Only `.shellcheckrc` applied |
| `--rcfile FILE` (0.10.0+) | That file, no search |
| `--norc` | No rc file |

Consequences:

- **Nothing merges.** A project rc silently replaces a user's personal rc,
  including its `enable=` lines. Put project policy in the project rc.
- A Snap install cannot read hidden files; the man page's fallback name
  `shellcheckrc` exists for that. A Docker run sees only mounted files.
- The `master` man page describes `shellcheck.*` keys in `.editorconfig`.
  ShellCheck 0.11.0 ignored `shellcheck.disable` there (measured): unreleased.

## SHELLCHECK_OPTS

The man page: the value is split on spaces and prepended to every invocation.
Measured:

| Case | Result |
| --- | --- |
| `SHELLCHECK_OPTS='-e SC2034' shellcheck --norc t.sh` | SC2034 excluded: the variable survives `--norc` |
| `SHELLCHECK_OPTS='-S error' shellcheck t.sh` | Only errors, exit `0` on a file with warnings |
| `SHELLCHECK_OPTS='-S error' shellcheck -S style t.sh` | Style findings reported: the command line wins |
| `SHELLCHECK_OPTS='--rcfile r.rc' shellcheck --norc t.sh` | No rc read: `--norc` wins |

It is the only environment variable ShellCheck reads for options; there is no
`SHELLCHECK_SHELL` or `SHELLCHECK_CONFIG`. A value set in a shell profile, a
CI job, or an editor changes results silently, so name it whenever results
differ between machines. Never set it to exclude codes or raise the severity.

## rc keys and directives

An rc file holds `key=value` lines that act as file-wide directives; values
may be quoted to contain spaces. Directives in a script override the rc for
that script.

| Key | Use | Notes |
| --- | --- | --- |
| `source-path=SCRIPTDIR` | Resolve `source` relative to each script | Repeatable; any directory also works |
| `external-sources=true` | Open sourced files not on the command line (as `-x`) | rc only, per the Directive page |
| `enable=NAME` | Turn on an optional check | Name each; see [sc-codes.md](sc-codes.md#optional-checks) |
| `extended-analysis=false` | Turn off dataflow analysis for huge scripts | 0.10.0+ |
| `shell=` | Set the dialect | In a script only for files without a shebang; never in an rc |
| `disable=`, `severity=` | Suppress or filter | Never add them (see [SKILL.md](../SKILL.md#non-negotiable-rules)) |

Directive scope (Directive page): after the shebang and before the first
command, file-wide; elsewhere, the next command, which may be a whole
function, loop, or `case`. A directive cannot sit before `else` or a single
`case` branch. The page recommends a reason comment on the directive.

A sound project rc, as guidance rather than a file to copy:

```ini
source-path=SCRIPTDIR
external-sources=true
enable=check-extra-masked-returns
enable=require-variable-braces
```

## shfmt and EditorConfig

Measured with v3.14.1:

- shfmt reads every `.editorconfig` from the script's directory upward until
  one with `root = true`. Per key, the nearer file wins: a child
  `[*.sh] indent_size = 2` combined with a parent `[*] indent_style = space`
  produced 2-space indentation.
- Within one file, a later matching section overrides an earlier one.
- Passing `-s` made shfmt ignore EditorConfig completely (tabs came back).
  The man page: "If any parser or printer flags are given to the tool, no
  EditorConfig formatting options will be used."
- An extensionless script with a bash shebang was not matched by `[*.sh]`;
  a `[[shell]]` section matched it. `[[bash]]` and `[[zsh]]` also exist
  (`[[shell]]` since v3.13.0, `[[zsh]]` since v3.13.1). Other EditorConfig
  tools ignore these sections.
- `ignore = true` under `[vendor/**]`: skipped when walking `.`; an explicit
  `shfmt -l vendor/v.sh` still checked the file (exit `1`); with
  `--apply-ignore` it was skipped (exit `0`).
- `--filename a/b/t.sh` gave stdin input the EditorConfig of that path.
- `shell_variant = posix` rejected bash arrays in a `#!/bin/bash` file
  ("parsed as posix via EditorConfig", exit `1`); with no key, `auto` detects
  the dialect from the extension, then the shebang.

## EditorConfig keys by shfmt version

| Key | Flag | v3.14.1 | Notes |
| --- | --- | --- | --- |
| `indent_style`, `indent_size` | `-i` | Yes | `indent_style = tab` for tabs, the shfmt default |
| `shell_variant` | `-ln` | Yes | `bash`, `posix`, `mksh`, `bats`, `zsh`, `auto` |
| `language_dialect` | `-ln` | **No** (ignored, measured) | New name on `master`; the old name stays accepted and the new one wins |
| `switch_case_indent` | `-ci` | Yes | |
| `case_indent` | `-ci` | **No** (ignored, measured) | New name on `master` |
| `binary_next_line` | `-bn` | Yes | |
| `space_redirects` | `-sr` | Yes | |
| `keep_padding` | `-kp` | Yes, deprecated | Scheduled for removal in the next major version |
| `function_next_line` | `-fn` | Yes | Marked deprecated on `master` |
| `block_next_line` | `-bl` | **No** (no flag, key ignored, measured) | `master` only |
| `simplify` | `-s` | Yes (since v3.12.0) | |
| `minify` | `-mn` | Yes (since v3.12.0) | Implies `simplify` |
| `ignore` | none | Yes | See `--apply-ignore` above |

Before writing a key, run `shfmt --version` and check the man page **at that
release tag**, not `master`. Where both names are needed across a team with
mixed versions, the old names work everywhere today.

A common style, as guidance: 2-space indentation with indented `case` items
and operators starting lines (the Google Shell Style Guide). Measured: it
formats byte-for-byte like `shfmt -i 2 -ci -bn`.

```ini
root = true

[[shell]]
indent_style = space
indent_size = 2
switch_case_indent = true
binary_next_line = true
```

## Migrating to ShellCheck and shfmt

| From | To | Notes |
| --- | --- | --- |
| `bash -n script` | `shellcheck script` | Keep `bash -n` only as a smoke test in the target bash |
| checkbashisms | ShellCheck on `#!/bin/sh` scripts (SC3xxx) | Same ground, with explanations |
| beautysh or an editor reindenter | shfmt with EditorConfig | Reformat in one dedicated commit; list it in `.git-blame-ignore-revs` |
| `shfmt -i 2 -ci` in scripts, CI, pre-commit args | The same style as EditorConfig keys | One source of truth; plain `shfmt -d .` in CI |
| An rc with `shell=bash` | Correct shebangs, or `# shellcheck shell=` in the few files without one | `shell=` in an rc hides POSIX findings |
| An rc full of `disable=` | Fix the findings | Each removal is proposed to the user |
| An rc written for ShellCheck < 0.10 | `--rcfile`, `extended-analysis` need 0.10.0; `avoid-negated-conditions` needs 0.11.0 | Pin the version |
