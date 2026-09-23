# git check-ignore

Official: https://git-scm.com/docs/git-check-ignore · Areas: G4, G20 · Floor: any

## Purpose in an audit

Names the exact rule (file, line, pattern) that ignores a path, so a finding can say where
the rule lives and whether it belongs to the repository or to one user's global file.

## Safety class

| Form | Class | Why |
| --- | --- | --- |
| every form | read | Evaluates exclude rules; reads the index unless `--no-index` |

## Options that matter

- `-v`, `--verbose`: print `<source>:<linenum>:<pattern><TAB><pathname>` `[doc]`.
  `<source>` is absolute for `core.excludesFile`, relative for `.git/info/exclude` and
  per-directory files `[doc]`.
- `-n`, `--non-matching`: also print paths that match nothing, with empty fields; only
  meaningful with `-v` `[doc]`.
- `--no-index`: ignore the index, so tracked paths are checked too `[doc]`. Needed to
  explain why a tracked file "should" be ignored.
- `--stdin`: paths from standard input; with `-z`, NUL-separated input and output
  `[doc]`.
- `-z` with `-v`: `<source> NUL <linenum> NUL <pattern> NUL <pathname> NUL` `[doc]`.
- `-q`: exit status only; single path only `[doc]`.
- Exit status: `0` one or more paths ignored, `1` none, `128` fatal `[doc]`.

## Verified recipes

```sh
git --no-pager check-ignore -v --no-index -- app.log build/out.o sub/local.txt excluded.tmp
```

`[observed]`: `.gitignore:2:*.log`, `.gitignore:1:build/`, `sub/.gitignore:1:local.txt`,
`.git/info/exclude:7:excluded.tmp`, exit 0.

```sh
git --no-pager check-ignore -v --no-index -- .DS_Store
```

`[observed]`: `<home>/.gitignore_global:4:.DS_Store` (absolute path of the global file).

```sh
git --no-optional-locks --no-pager ls-files -z -o -i --exclude-standard --directory \
  | git --no-pager check-ignore -z -v --stdin | tr '\0' '\n' | paste - - - - \
  | awk -F'\t' '{print $1":"$2":"$3}' | sort | uniq -c
```

`[observed]`: one count per rule in use (`.gitignore:1:node_modules/`, …). Rules absent
from the output match nothing today.

```sh
git --no-pager check-ignore -v -n -- id_rsa app.log
```

`[observed]`: `::<TAB>id_rsa` and `::<TAB>app.log`, exit 1: `id_rsa` matches no rule, and
`app.log` is tracked, so without `--no-index` it is not checked.

## Footprint it leaves when interrupted or misused

None.

## Gotchas

- Without `--no-index`, tracked paths are never reported (exit 1) even when a rule matches
  them `[observed]`, `[doc]`.
- With `-v`, a matching **negated** pattern (`!keep.log`) is printed and the exit status is
  0, although the path is not ignored; without `-v` the exit status is 1 `[observed]`. Read
  the pattern, not the exit code.
- A negation under an excluded directory cannot re-include: `!build/keep.o` after
  `build/` still reports `build/` `[observed]`, as `gitignore` documents.
- `-n` records have empty `<source>`, `<linenum>` and `<pattern>` fields, so `-n -v` output
  lines start with `::` `[observed]`.
- Results include the user's global excludes file; a collaborator's result differs.
- Streaming with `--stdin` follows `GIT_FLUSH` buffering; feed a finite list (as above)
  rather than an interactive pipe `[doc]`.
