# git worktree

Official: https://git-scm.com/docs/git-worktree · Areas: G9, G22, G2 · Floor: any
(`prunable` annotation 2.31, `list --porcelain -z` 2.36)

## Purpose in an audit

Lists every working folder attached to the repository, which branch each holds, and which
are locked or gone; previews what `prune` would delete.

## Safety class

| Form | Class | Why |
| --- | --- | --- |
| `list`, `list --porcelain [-z]`, `list -v` | read | Reads `$GIT_COMMON_DIR/worktrees/*` |
| `prune --dry-run [--verbose]` | read | "do not remove anything; just report" `[doc]` |
| `prune` | mutates | Deletes admin files of missing worktrees (contract section 1) |
| `add` | mutates | Creates a folder, admin files, maybe a branch (`-b`, `-B` resets one) |
| `remove` | mutates | Deletes the folder; `--force` drops uncommitted work |
| `move`, `repair` | mutates | Rewrite link files |
| `lock`, `unlock` | mutates | Create or remove `worktrees/<id>/locked` `[doc]` |

## Options that matter

- `list --porcelain`: one attribute per line; `worktree <path>`, `HEAD <sha>`,
  `branch <ref>` or `detached`, `bare`, `locked [<reason>]`, `prunable [<reason>]`; empty
  line ends a record; stable across versions `[doc]`. Add `-z` for NUL-terminated lines
  `[doc]`.
- `list -v`: reasons on an indented next line `[doc]`.
- `prune -n`/`--dry-run`, `-v`/`--verbose`, `--expire <time>` (only older than) `[doc]`.
  `gc.worktreePruneExpire` prunes automatically during `gc` `[doc]`.
- `remove --force` (twice for a locked worktree), `add --force` (twice for a missing but
  locked path) `[doc]`.
- `add -B <branch>` resets an existing branch to the start point `[doc]`: a history loss
  if the branch had unique commits.
- `--relative-paths` / `worktree.useRelativePaths` for link files `[doc]`.
- `lock --reason <string>` `[doc]`.

Per-worktree refs: `HEAD` and pseudo refs, plus `refs/bisect/*`, `refs/worktree/*`,
`refs/rewritten/*`; reach another worktree's with `main-worktree/HEAD` or
`worktrees/<id>/HEAD` `[doc]`. Admin files: `$GIT_COMMON_DIR/worktrees/<id>/` with `gitdir`,
`HEAD`, `index`, `locked`, and `config.worktree` when `extensions.worktreeConfig` is on
`[doc]`.

## Verified recipes

```sh
git --no-pager worktree list --porcelain -z | tr '\0' '\n'
```

`[observed]`: main worktree `detached` (bisect), `wt-gone` with `branch refs/heads/wt/branch`
and `prunable gitdir file points to non-existent location`, `wt-live` with
`locked on usb disk`.

```sh
git --no-pager worktree prune --dry-run --verbose
```

`[observed]`: `Removing worktrees/orphan: gitdir file does not exist` and
`Removing worktrees/wt-gone: gitdir file points to non-existent location`; nothing was
removed.

```sh
ls "$(git rev-parse --git-common-dir)/worktrees"
```

`[observed]`: `orphan wt-gone wt-live`, while `list` showed only 3 records (main,
`wt-gone`, `wt-live`): `orphan` is an admin directory with no registration.

```sh
git -C <worktree-path> --no-optional-locks --no-pager status --porcelain=v2 --branch \
  --untracked-files=normal
```

`[observed]`: `? dirty.txt` in the linked worktree.

## Footprint it leaves when interrupted or misused

- Deleting a worktree folder by hand leaves `worktrees/<id>/` and keeps its branch
  "checked out": `git switch held` then fails with
  `fatal: 'held' is already used by worktree at '<path>'` `[observed]`.
- Per-worktree operation state (`MERGE_HEAD`, `BISECT_LOG`, `refs/bisect`) lives under
  `worktrees/<id>/` `[observed]`; it disappears with `prune`.
- `locked` files keep entries forever until unlocked.

## Gotchas

- `prune --dry-run --verbose` says "Removing" for what it would remove `[observed]`.
- A worktree on removable media shows as prunable when unmounted; lock it instead of
  pruning `[doc]`.
- `extensions.worktreeConfig` makes older Git refuse the repository `[doc]`.
- `git sparse-checkout set` turns on `extensions.worktreeConfig` by itself `[observed]`.
- Paths in the non `-z` porcelain output are C-quoted when unusual `[doc]`; use `-z`.
