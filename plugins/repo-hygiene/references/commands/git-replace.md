# git replace

Official: https://git-scm.com/docs/git-replace · Areas: G15 · Floor: any
(`--convert-graft-file` 2.20)

## Purpose in an audit

Find replace refs (`refs/replace/<oid>`), which make Git show one object in place of
another in almost every command, and remove them as an approved item. They are the reason
every count and walk in this corpus runs with `git --no-replace-objects`.

## Safety class

| Form | Class | Why |
| --- | --- | --- |
| `replace -l [--format=short\|medium\|long] [<pattern>]` | read | lists replace refs |
| `replace [-f] <object> <replacement>` | mutates | creates `refs/replace/<object>` |
| `replace --edit <object>` | mutates, executes-config | opens the editor |
| `replace --graft <commit> [<parent>…]` | mutates | writes a new commit and a replace ref |
| `replace --convert-graft-file` | mutates | converts `info/grafts` into replace refs and deletes the file |
| `replace -d <object>…` | mutates | deletes replace refs |

## Options that matter

- `--format=long`: `<object> (<type>) -> <replacement> (<type>)`.
- Global `--no-replace-objects` or `GIT_NO_REPLACE_OBJECTS=1`: ignore all replace refs.
- `core.useReplaceRefs=false` in config: same, persistently.

## Verified recipes

```sh
git --no-pager replace -l --format=long
git cat-file commit 21a4d8d | tail -n 1
git --no-replace-objects cat-file commit 21a4d8d | tail -n 1
```

`[observed]` `21a4d8d… (commit) -> 0b5d6e5… (commit)`; `remove config` vs `big blob`.
Approved item and its undo, literal:

```sh
git replace -d 21a4d8dfeaeb702fe8644b81b2cabfe6f44f896e
git replace 21a4d8dfeaeb702fe8644b81b2cabfe6f44f896e 0b5d6e58937c6e0e036f6264f646538f4c55474d
```

`[observed]` "Deleted replace ref '21a4d8d…'", then `replace -l` listed it again after the
undo.

## Footprint it leaves when interrupted or misused

A replace ref pins both objects. Pushed replace refs (`refs/replace/*` is not in the
default refspecs) affect everyone who fetches them explicitly.

## Gotchas

- `[observed]` with the replace ref active, `rev-list --left-right --count` and
  `%(ahead-behind)` reported 4 instead of 5, `log` showed the wrong subject, and a
  `bisect run` walked the replaced history.
- `fsck` results were identical with and without `--no-replace-objects` on the fixture
  `[observed]`; pass it anyway for uniformity.
- Replace objects disable the commit-graph `[doc]` git-commit-graph CAVEATS.
