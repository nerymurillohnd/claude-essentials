# git ls-files

Official: https://git-scm.com/docs/git-ls-files · Areas: G3, G4, G10, G20 · Floor: any
(`--eol` 2.8, `--format` 2.38)

## Purpose in an audit

The index, seen path by path: tracked files, stages of a conflict, flags that hide changes,
line endings, sizes, and (with `-o`) untracked or ignored files on disk. It is the only
porcelain-free way to see assume-unchanged and skip-worktree.

## Safety class

| Form | Class | Why |
| --- | --- | --- |
| every form | read | Reads the index and, with `-o`/`-m`/`-d`/`-k`, the working tree |
| `--format='%(objectsize)'` in a partial clone | network | Reading a missing blob's size may fetch it; add `git --no-lazy-fetch` `[doc]` (`git`) |
| `--recurse-submodules` | read (recursive) | Runs in each active submodule; only `--cached` and `--stage` supported `[doc]` |

## Options that matter

- `-c` (default), `-m` unstaged modification (deletions count), `-d` unstaged deletion,
  `-o` untracked, `-i` only ignored (needs `-c` or `-o` **and** an `--exclude*` option),
  `-s` stage info, `-u` unmerged only (forces `--stage`), `-k` untracked paths blocking a
  checkout (file/directory conflicts), `--resolve-undo` `[doc]`.
- `-t` status tags: `H` tracked, `S` skip-worktree, `M` unmerged, `R` removed, `C`
  changed, `K` to be killed, `?` untracked, `U` resolve-undo `[doc]`.
- `-v`: like `-t`, lowercase for assume-unchanged `[doc]`. `-f`: lowercase for
  fsmonitor-valid `[doc]`.
- `--exclude-standard`: `.gitignore` per directory, `$GIT_COMMON_DIR/info/exclude`,
  `core.excludesFile` (or `$XDG_CONFIG_HOME/git/ignore`) `[doc]`. `-x`, `-X`,
  `--exclude-per-directory` give custom rules.
- `--directory` (with `-o`): an untracked directory once, with a trailing `/`;
  `--no-empty-directory` drops empty ones `[doc]`. Use it for bounded listings.
- `--eol`: `i/<eolinfo> w/<eolinfo> attr/<eolattr>`; eolinfo is `-text`, `none`, `lf`,
  `crlf`, `mixed` or empty `[doc]`.
- `--format=<fmt>`: `%(objectmode)`, `%(objecttype)`, `%(objectname)`,
  `%(objectsize[:padded])`, `%(stage)`, `%(eolinfo:index)`, `%(eolinfo:worktree)`,
  `%(eolattr)`, `%(path)`; not combinable with `-s -o -k -t --resolve-undo --eol` `[doc]`.
- `--sparse`: show sparse directories without expanding them `[doc]`.
- `--error-unmatch`: exit 1 if a given path is not tracked `[doc]`.
- `--deduplicate`: one line per path when stages repeat it `[doc]`.
- `-z`: NUL-terminated, unquoted paths `[doc]`.
- `--debug`: cache-entry internals (ctime, mtime, dev, ino, uid, size, flags); format may
  change at any time `[doc]`, read only.
- `--full-name`: paths from the top level when run in a subdirectory `[doc]`.

## Verified recipes

```sh
git --no-optional-locks --no-pager ls-files -v | grep -E '^[a-zS]'
```

`[observed]`: `h app.txt` (assume-unchanged), `S skip.txt` (skip-worktree).

```sh
git --no-optional-locks --no-pager ls-files -c -i --exclude-standard
```

`[observed]`: `app.log` (repository rule) plus `.DS_Store`, `.idea/workspace.xml`,
`.notes.txt.swp` (user's global excludes file); with `-c core.excludesFile=/dev/null` only
`app.log`.

```sh
git --no-optional-locks --no-pager ls-files -o -i --exclude-standard --directory
```

`[observed]`: `build/`, `excluded.tmp` (from `info/exclude`), `sub/local.txt` (nested
`.gitignore`).

```sh
git --no-optional-locks --no-pager ls-files --eol | grep -E '^i/(crlf|mixed)'
```

`[observed]`: `i/crlf  w/crlf  attr/text=auto  crlf.txt`; an intent-to-add file shows
`i/none`.

```sh
git --no-optional-locks --no-pager ls-files --format='%(objectsize) %(path)' | sort -rn \
  | head -n 20
```

`[observed]`: `6000000 big.bin` first.

```sh
git --no-optional-locks --no-pager ls-files -u
```

`[observed]`: three lines for `conf.txt`, stages 1, 2 and 3.

```sh
git --no-optional-locks --no-pager ls-files | LC_ALL=C tr '[:upper:]' '[:lower:]' | sort \
  | uniq -d
```

`[observed]`: `readme.md` for a tree holding `README.md` and `readme.md`.

## Footprint it leaves when interrupted or misused

None: it never writes.

## Gotchas

- `-m` lists an unmerged path once per stage (three `conf.txt` lines) `[observed]`; add
  `--deduplicate` or count unique paths.
- `-m` does not list skip-worktree files with edits nor mode flips under
  `core.filemode=false` `[observed]`.
- `-i` without an `--exclude*` option reports nothing: "Standard ignore rules are not
  automatically activated" `[doc]`.
- `--exclude-standard` includes the user's global excludes file, so results differ between
  users `[observed]`.
- A pathspec `*` matches across `/`: `'*/.gitignore'` finds every nested file, and
  `'*.env*'` matches `deep/x/.env` `[observed]`.
- `ls-files -o --directory` lists a directory holding only a broken `.git` file that
  `git status` hides `[observed]`.
