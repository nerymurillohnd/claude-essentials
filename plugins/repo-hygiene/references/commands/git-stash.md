# git stash

Official: https://git-scm.com/docs/git-stash · Areas: G8, G16 · Floor: any
(`show --include-untracked` 2.32, `push --staged` 2.35, `export`/`import` 2.51)

## Purpose in an audit

Inventory of work set aside outside any branch: entries, dates, base commits, files,
untracked part. Stashes live in `refs/stash` and its reflog; older entries exist only as
reflog entries `[doc]`.

## Safety class

| Form | Class | Why |
| --- | --- | --- |
| `stash list [<log-options>]` | read | Walks the `refs/stash` reflog |
| `stash show --no-ext-diff --no-textconv --name-status …` | read | Diff of the stash against its base; no contents |
| `stash show` with no format option | read, may print contents | `stash.showPatch=true` makes it print the patch `[doc]` |
| `git stash` (no subcommand), `push`, `save` | mutates | Creates an entry and resets the working tree and index (`-u`/`-a` also clean) `[doc]` |
| `apply`, `pop`, `branch` | mutates | Change the working tree and index; `pop` and `branch` also drop the entry on success `[doc]` |
| `drop`, `clear` | mutates | Remove entries; they become unreachable and may be pruned `[doc]` |
| `create` | mutates (objects) | Writes a stash commit without a ref `[doc]` |
| `store` | mutates (refs) | Adds a commit to `refs/stash` and its reflog `[doc]` |
| `export --print` / `export --to-ref` | mutates (objects / refs) | Builds a commit chain; `--to-ref` also stores a ref `[doc]` |
| `import <commit>` | mutates (refs) | Adds entries to the stash list `[doc]` |

## Options that matter

- A stash is a merge commit: first parent = `HEAD` at stash time, second parent = index
  state, third parent (only with `-u` or `-a`) = untracked files `[doc]` (DISCUSSION).
- `stash@{<n>}`: reflog syntax; `<n>` alone also works `[doc]`.
- `show -u`/`--include-untracked`, `--only-untracked`, `--no-include-untracked`;
  `stash.showIncludeUntracked`, `stash.showStat` (default true), `stash.showPatch`
  (default false) `[doc]`.
- `list` accepts log options: use `--format=`; see the date gotcha below.
- `push -u` stashes untracked files, `-a` also ignored files, and both "clean up with
  git clean" afterwards `[doc]`.
- `push -k`/`--keep-index`, `-S`/`--staged`, `-p`/`--patch`, `-- <pathspec>` `[doc]`.
- `apply --index`, `pop --index` (`stash.index`): also restore the index; can fail with
  conflicts `[doc]`.
- `--label-ours`, `--label-theirs`, `--label-base` for `apply` conflict markers `[doc]`.

## Verified recipes

```sh
git --no-replace-objects --no-pager stash list --format='%gd%x09%H%x09%P%x09%ci%x09%s'
```

`[observed]`: `stash@{0}` with three parents (`-u` stash), `stash@{1}` with two, dates
and `On main: <message>` subjects.

```sh
git --no-optional-locks --no-pager stash show --no-ext-diff --no-textconv --name-status \
  --include-untracked 'stash@{0}'
git --no-replace-objects --no-pager ls-tree -r -l 'stash@{0}^3'
```

`[observed]`: `A big.bin`, `A new.txt`; sizes `3072000` and `3`.

```sh
git --no-replace-objects rev-parse --verify --quiet --end-of-options 'stash@{1}:s.txt'
git --no-replace-objects rev-parse --verify --quiet --end-of-options 'main:s.txt'
git --no-replace-objects rev-parse --verify --quiet --end-of-options 'stash@{1}^1:s.txt'
```

`[observed]`: saved blob differs from `main`, `main` equals the base: the change exists
only in the stash. The full classification loop is in
`areas/stashes-worktrees-submodules.md` (deep check 1).

```sh
git --no-replace-objects -c core.fsmonitor=false -c gc.auto=0 -c maintenance.auto=false \
  fsck --unreachable --no-reflogs --no-progress 2>/dev/null | awk '$2=="commit"{print $3}' \
  | git --no-replace-objects --no-pager log --no-walk --merges --stdin \
    --format='%H %P | %ci | %s'
```

`[observed]`: the dropped entry (`On main: dropped`) **and** the live `stash@{1}`; subtract
`git stash list --format=%H`.

## Footprint it leaves when interrupted or misused

- `refs/stash` and `logs/refs/stash`; dropped entries become dangling merge commits until
  `gc` prunes them.
- A conflicted `apply` or `pop` leaves conflict markers and keeps the entry `[doc]`.
- `push -u` or `-a` deletes the untracked (and ignored) files it saved `[doc]`.
- `rebase --autostash` / `rebase --quit` can add entries to the list `[doc]`
  (`git-rebase`).

## Gotchas

- `stash list --date=iso` replaces `stash@{0}` with `stash@{2026-09-22 21:49:27 -0600}`:
  the index is lost `[observed]`. Use `%gd` without `--date` and `%ci` for the date.
- Two stashes made from the same state share their index commit (same SHA as second
  parent) `[observed]`; do not count index commits as separate work.
- `rev-parse --verify` takes exactly one argument; with three it exits 1 `[observed]`.
- `git stash push` for one file restored an assume-unchanged file with a hidden edit, and
  the edit was not saved `[observed]`. Check `git ls-files -v` before any stash item.
- `git clone --mirror` copies `refs/stash` but not its reflog: only `stash@{0}` survives
  in the copy `[observed]`. A mirror is not a stash backup; an archive branch per stash is.
- A subject `WIP on` is not proof of which tool made the stash (contract section 9).
