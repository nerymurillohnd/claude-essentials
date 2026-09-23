# git diff

Official: https://git-scm.com/docs/git-diff · Areas: G3, G4, G8, G10 · Floor: any

## Purpose in an audit

Names and counts of changes between the working tree, the index, commits and trees; the
conflict-marker check; mode changes. In an audit use name, status and stat forms; a patch
prints file contents and can leak secrets.

## Safety class

| Form | Class | Why |
| --- | --- | --- |
| `git --no-optional-locks diff --no-ext-diff --no-textconv --name-status\|--stat\|--numstat\|--summary\|--check …` | read | No external program, no contents |
| `git diff` with a patch (default output) | read, but prints contents | Secret-shaped paths must be excluded (contract section 4) |
| `git diff` without `--no-ext-diff` when `diff.external` or a `diff=<driver>` attribute with `command` is set | executes-config | Runs the external program `[doc]`, `[observed]` |
| `--textconv` (default for `git diff`) with a `textconv` driver | executes-config | Runs the conversion program `[doc]` |
| `--output=<file>` | mutates (outside the repository) | Writes a file `[doc]` |
| `--no-index <path> <path>` | read, but reads arbitrary files | Can read any file on disk, secrets included |

## Options that matter

- Forms: `git diff` (worktree vs index), `--cached`/`--staged` (index vs `HEAD` or a
  commit), `<commit>` (worktree vs commit), `<a> <b>`, `<a>..<b>`, `<a>...<b>`
  (merge base to `b`), `--merge-base` `[doc]`. `AUTO_MERGE` is a tree you can diff against
  after an ort conflict `[doc]`.
- `--no-ext-diff`: disallow external diff drivers `[doc]`. `--no-textconv`: disallow
  textconv filters `[doc]`.
- `--name-only`, `--name-status`, `--stat[=<width>]`, `--numstat`, `--shortstat`,
  `--dirstat`, `--summary` (creations, renames, mode changes) `[doc]`.
- `--check`: conflict markers and whitespace errors; non-zero exit when found `[doc]`.
- `--exit-code`: exit 1 if differences; `--quiet` implies it and disables untrusted
  external diff helpers `[doc]`.
- `--diff-filter=[ACDMRTUXB…]`: select change types; lowercase excludes `[doc]`.
- `--submodule[=short|log|diff]`, `--ignore-submodules[=none|untracked|dirty|all]` `[doc]`.
- `-z`: NUL-separated output for `--name-*` and `--numstat`.
- `--relative[=<path>]`: limit to a subdirectory `[doc]`.
- `-R`, `--binary`, `--full-index`: patch forms, not audit forms.

## Verified recipes

```sh
git --no-optional-locks --no-pager diff --no-ext-diff --no-textconv --check
```

`[observed]`: `conf.txt:1: leftover conflict marker` (and lines 3, 5), exit 2.

```sh
git --no-optional-locks --no-pager diff --no-ext-diff --no-textconv --name-status
git --no-optional-locks --no-pager diff --no-ext-diff --no-textconv --cached --name-status
```

`[observed]`: worktree side `U conf.txt`, `M conf.txt`, `A ita.txt`, `M run.sh`; index
side `U conf.txt`, `M run.sh`.

```sh
git --no-optional-locks --no-pager -c core.filemode=true diff --no-ext-diff \
  --no-textconv --summary
```

`[observed]`: `mode change 100644 => 100755 mode.sh`, invisible without the `-c`.

```sh
git --no-optional-locks --no-pager diff --no-ext-diff --no-textconv --quiet
```

`[observed]`: exit 1 with changes present.

## Footprint it leaves when interrupted or misused

- `--output=<file>` leaves a file.
- An external diff helper can leave whatever it writes: a test helper configured through
  `diff.external` ran and created a marker file `[observed]`.

## Gotchas

- `diff.external` ran for a patch-producing `git diff` but not for `--name-only` or
  `--stat`, and not when `--no-ext-diff` was given `[observed]`. Always pass
  `--no-ext-diff --no-textconv`; that also keeps name-only forms safe if Git changes.
- `git diff` without arguments compares with the index, not `HEAD`: staged changes do not
  show.
- An empty three-dot diff is not proof of equal endpoints (contract section 9).
- Assume-unchanged and skip-worktree files are skipped even by `git diff HEAD`
  `[observed]`.
- `--quiet` exits 1 on differences; do not read that as an error.
