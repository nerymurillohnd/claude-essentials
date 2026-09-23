# git clean

Official: https://git-scm.com/docs/git-clean · Areas: G2, G3, G4, G10 · Floor: any

## Purpose in an audit

The dry run (`-n`) is the most honest preview of what an untracked or ignored clean-up would
delete, including which nested repositories Git would skip. The real run is an approved,
irreversible removal.

## Safety class

| Form | Class | Why |
| --- | --- | --- |
| `git clean -n …` / `--dry-run` | read | "Don't actually remove anything, just show what would be done" `[doc]` |
| `git clean -f …` | mutates | Deletes untracked files; no undo |
| `git clean -f -d …` | mutates | Also deletes untracked directories |
| `git clean -f -x …` | mutates | Also deletes ignored files (`.env`, build output, local config) |
| `git clean -f -X …` | mutates | Deletes only ignored files |
| `git clean -f -f -d …` | mutates | Also deletes untracked nested repositories with their history |
| `git clean -i` | mutates | Interactive; the audit never uses it |

## Options that matter

- `-n`, `--dry-run`: preview; ignores `clean.requireForce` `[doc]`.
- `-f`, `--force`: required unless `clean.requireForce=false`; a second `-f` also removes
  untracked nested Git repositories `[doc]`.
- `-d`: recurse into untracked directories when no pathspec is given `[doc]`.
- `-x`: do not use the standard ignore rules (removes ignored files too), but still use
  `-e` patterns `[doc]`.
- `-X`: remove only files ignored by Git `[doc]`.
- `-e <pattern>`: add an ignore rule. Under `-X` that marks more files for removal; to
  protect a path use a negated pattern (`-e '!.env'`) (contract section 4).
- `-q`: quiet; `<pathspec>`: limit to paths.
- `clean.requireForce`: defaults to true `[doc]`.

## Verified recipes

```sh
git clean -n -d
```

`[observed]`: `Would remove app.txt.orig`, `broken-link`, `outside-link`, `s.txt.rej`, and
`Would skip repository vendor/other`.

```sh
git clean -n -d -X
git clean -n -d -X -e '!.env'
```

`[observed]`: the first listed `.env`, `debug.log`, `dist/`, `node_modules/`; the second
the same without `.env`.

```sh
git clean -n -d -f -f
```

`[observed]`: `Would remove vendor/` (the nested repository is now included). In a
superproject, plain `-n -d` listed `elsewhere/` (a directory with a broken `.git` file) and
omitted the nested repository `nested/`; `-n -d -f -f` listed both.

## Footprint it leaves when interrupted or misused

- Nothing to recover: removed files are not in the object store unless they were once
  added or stashed.
- Symlinks are removed as links; their targets are untouched (`broken-link`,
  `outside-link` listed as files `[observed]`).

## Gotchas

- It works from the **current directory** down: run from `sub/`, `git clean -n` listed only
  `u1.txt`, while from the top it listed secret-shaped files too `[observed]`, `[doc]`
  ("starting from the current directory"). Always pass `-C <top-level>` or run at the top.
- `-X` follows every ignore source, including `.git/info/exclude` and the user's global
  excludes file: `excluded.tmp` from `info/exclude` was listed `[observed]`.
- `-x` and `-X` treat ignored files as disposable; an ignored path is not a disposable
  path (contract section 9).
- A `.git` directory or file inside an untracked directory changes what is skipped; always
  read the dry run before approving.
- `git stash -u` and `-a` also run a clean after saving `[doc]` (`git-stash`).
