# git fetch

Official: https://git-scm.com/docs/git-fetch · Areas: G5, G6, G7, G17 · Floor: any
(`fetch.pruneTags` 2.17, `--refetch` 2.36)

## Purpose in an audit

Never an inspection tool. It is the approved item that refreshes remote-tracking refs before
the ladder, and the command whose configured prune policy can delete local tags.

## Safety class

| Form | Class | Why |
| --- | --- | --- |
| `git fetch <remote>` | network, mutates, executes-config | moves `refs/remotes/*`, writes `FETCH_HEAD`, downloads objects, may run `git maintenance run --auto`, runs credential helper / SSH command |
| `--dry-run` | network, writes-local-state | updates no ref and no `FETCH_HEAD`, but **downloads objects** `[observed]` |
| `--prune` / `fetch.prune` | mutates | deletes tracking refs (and their reflogs) gone on the server |
| `--prune-tags` / `fetch.pruneTags` (with prune) | mutates | deletes every local tag the remote lacks |
| `+<src>:<dst>` refspec, `--force` | mutates | overwrites local refs, including tags |
| `--refetch`, `--unshallow`, `--depth`, `--filter` | mutates | rewrites the object set / shallow state |
| `--update-head-ok` | mutates | may move the checked-out branch without updating the tree |

## Options that matter

- `--no-prune`: overrides a configured `fetch.prune`/`remote.<n>.prune` for this call.
- `--prune-tags` is equivalent to adding `refs/tags/*:refs/tags/*` to the refspec and only
  prunes when prune is also on `[doc]`.
- `--no-tags` / `--tags`, `remote.<n>.tagOpt`.
- `--no-auto-maintenance` (`--no-auto-gc`): skip the post-fetch maintenance.
- `--no-write-fetch-head`, `--no-show-forced-updates`, `--atomic`.
- `--negotiate-only`, `--prefetch` (writes `refs/prefetch/*`, used by maintenance).

## Verified recipes

Approved item, literal, with the prune policy neutralised:

```sh
git fetch --no-prune origin
git fetch --no-prune origin '+refs/tags/v0.3:refs/tags/v0.3'
```

`[observed]` with `fetch.prune=true` and `fetch.pruneTags=true` set **globally**, the second
command moved `v0.3` to the server's target and kept the local-only tag. Preview what the
configured policy would delete (this still downloads objects):

```sh
git fetch --dry-run origin
```

`[observed]` it printed `- [deleted] (none) -> origin/feat/abandoned` and
`- [deleted] (none) -> local-only`; with the global file masked, `fetch.pruneTags=true`
alone deleted nothing, and `fetch.prune=true` alone deleted only the tracking ref.

## Footprint it leaves when interrupted or misused

`FETCH_HEAD`; `*.lock` files under `refs/remotes/` after a crash; `objects/pack/tmp_pack_*`
from an interrupted download; loose objects from `--dry-run`; a background `gc`/maintenance
process and possibly `gc.log`.

## Gotchas

- `git fetch --dry-run` is not a read: `[observed]` an object that existed only on the
  server was present locally afterwards. Use `git ls-remote` to compare.
- A global `fetch.prune` + `fetch.pruneTags` makes every fetch in every repository delete
  local-only tags (see `areas/branches-remotes-tags.md` check 13).
- Pruning a tracking ref deletes its reflog, the only local record of the server's last tip
  `[observed]`.
- A refspec such as `refs/tags/*:refs/tags/*` combined with `--prune` deletes tags that came
  from other remotes `[doc]` PRUNING.
