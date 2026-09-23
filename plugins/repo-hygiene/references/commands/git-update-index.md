# git update-index

Official: https://git-scm.com/docs/git-update-index · Areas: G1, G3 · Floor: any
(`--show-index-version` 2.43)

## Purpose in an audit

Two read-only uses (index version, untracked-cache test) and the literal commands that
clear or set the flags that hide local changes. Everything else it does writes the index.

## Safety class

| Form | Class | Why |
| --- | --- | --- |
| `--show-index-version` | read | Reports the on-disk version; the index checksum and mtime did not change `[observed]` |
| `--test-untracked-cache` | writes-local-state | Creates and removes test directories in the working tree to check mtime behavior; left nothing behind `[observed]` |
| `--refresh`, `--really-refresh` | writes-local-state | Rewrites cached stat data in the index |
| `--assume-unchanged` / `--no-assume-unchanged` | mutates (index) | Sets or clears a per-entry bit |
| `--skip-worktree` / `--no-skip-worktree` | mutates (index) | Same |
| `--chmod=(+\|-)x` | mutates (index) | Changes the recorded mode |
| `--add`, `--remove`, `--force-remove`, `--cacheinfo`, `--index-info`, `--replace`, `--info-only` | mutates (index, objects) | Adds or removes entries; `--add <file>` writes a blob |
| `--unresolve`, `-g`/`--again` | mutates (index) | Re-creates conflict state or re-adds changed paths |
| `--index-version <n>`, `--split-index`, `--untracked-cache`, `--fsmonitor` (and `--no-` forms) | mutates (index format) | Rewrites the index |

## Options that matter

- `--assume-unchanged`: "the user promises not to change the file"; Git skips checking it
  and fails gracefully when it must modify it `[doc]`. List with `git ls-files -v`
  (lowercase tag) `[doc]`.
- `--skip-worktree`: treat the file as unchanged when absent and avoid writing it; the
  mechanism behind sparse checkout; in a sparse checkout Git clears the bit when the file
  reappears `[doc]`.
- `core.ignorestat=true`: paths updated by `update-index`, `apply --index`,
  `checkout-index -u`, `read-tree -u` are marked assume-unchanged automatically `[doc]`.
- `--index-version <n>`: 2, 3 or 4; the default is 2, or 3 when extended flags are used;
  v4 is path-compressed and supported by Git 1.8.0+, libgit2 since 2016, JGit since 2020
  `[doc]`.
- `--split-index`: index plus `$GIT_DIR/sharedindex.<hash>` `[doc]`; see
  `git rev-parse --shared-index-path`.
- `--untracked-cache`: caches directory mtimes; `core.untrackedCache` is the easier
  switch `[doc]`. Before 2.17 it had a bug; the workaround is
  `git -c core.untrackedCache=false status` `[doc]`.
- `--fsmonitor`, `--fsmonitor-valid`: FSMonitor integration; `core.fsmonitor` can name a
  hook program `[doc]`.
- `-z`, `--stdin`: NUL-separated path input `[doc]`.
- Paths beginning with `.` components (`./file`, `dir/./file`) are discarded `[doc]`.

## Verified recipes

```sh
git update-index --show-index-version
```

`[observed]`: `3` in a repository with skip-worktree and intent-to-add entries; `4` after
`--index-version 4`; the index hash was unchanged afterwards.

```sh
git update-index --test-untracked-cache
```

`[observed]`: `Testing mtime in '<repo>' ...... OK`, exit 0, no leftover files.

Approved-item forms, run literally, one path per call:

```sh
git update-index --no-assume-unchanged -- app.txt
git update-index --no-skip-worktree -- skip.txt
```

## Footprint it leaves when interrupted or misused

- `index.lock` while writing; a crash leaves it behind.
- `sharedindex.*` files in split-index mode; old ones expire after
  `splitIndex.sharedIndexExpire` `[doc]`.
- A hidden local change (assume-unchanged) that later commands overwrite: after marking
  `a` assume-unchanged and editing it, a `git stash push` for another file restored `a`
  and the edit was not saved in the stash `[observed]`.

## Gotchas

- People use assume-unchanged to "ignore changes to a tracked file"; the manual defines it
  as a performance promise, not an ignore mechanism `[doc]`. Edits under it can be lost
  `[observed]`.
- Skip-worktree set by hand outside a sparse checkout hides edits from `status`,
  `ls-files -m` and `diff HEAD` `[observed]`.
- `--refresh` errors out when the index needs updating unless `-q` is given `[doc]`.
- `--ignore-submodules` is honored only before `--refresh` `[doc]`.
- `update-index` honors `core.filemode` `[doc]`.
