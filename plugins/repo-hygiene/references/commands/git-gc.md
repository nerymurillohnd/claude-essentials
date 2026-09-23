# git gc

Official: https://git-scm.com/docs/git-gc · Areas: G17 · Floor: any (cruft packs by
default 2.41)

## Purpose in an audit

Never an inspection. Its configuration is audited (drift from defaults), its leftovers are
audited (`gc.log`), and it is the last step of the reclamation runbook, as an approved deep
item only.

## Safety class

| Form | Class | Why |
| --- | --- | --- |
| `gc` | mutates, executes-config | repacks, expires reflogs, prunes unreachable objects older than `gc.pruneExpire`, packs refs, prunes worktrees, rerere gc; runs `gc.recentObjectsHook` |
| `gc --auto` | mutates, executes-config | same when thresholds hit; runs the `pre-auto-gc` hook; may detach |
| `gc --prune=now` | mutates | no grace period: irreversible and unsafe with concurrent writers |
| `gc --no-prune` | mutates | repacks without deleting unreachable objects |
| `gc --aggressive` | mutates | slow full recompression |

## Options that matter

- `--prune=<date>`: default `2.weeks.ago` (`gc.pruneExpire`).
- `--keep-largest-pack`, `gc.bigPackThreshold`.
- `--[no-]detach`, `gc.autoDetach`.
- `--force`: run even if another gc may be running.
- Defaults `[doc]`: `gc.auto` 6700 (0 disables every auto heuristic), `gc.autoPackLimit` 50,
  `gc.reflogExpire` 90 days, `gc.reflogExpireUnreachable` 30 days,
  `gc.worktreePruneExpire` 3 months, `gc.logExpiry` 1 day, `gc.cruftPacks` true,
  `gc.writeCommitGraph` true, `gc.packRefs` true, `gc.rerereResolved` 60 days,
  `gc.rerereUnresolved` 15 days.

## Verified recipes

Inspection is config only:

```sh
git --no-pager config --show-scope --show-origin --get-regexp '^gc\.'
test -f <git-dir>/gc.log && head -c 400 <git-dir>/gc.log
```

Reclamation (approved deep items, after the backup; see `areas/object-store.md`):

```sh
git reflog expire --expire=now --expire-unreachable=now --all
git gc --prune=now
```

`[observed]` on a seeded copy: 0 unreachable objects afterwards, no cruft pack, the
`tmp_pack_*` removed, the `.pack` without `.idx` and its `.keep` left in place. A plain
`git gc` on 2.55 created a cruft pack (`.mtimes`) with the 7 unreachable objects.

## Footprint it leaves when interrupted or misused

`gc.pid` (lock), `gc.log` from a failed detached run (blocks later `--auto` runs for
`gc.logExpiry`), `tmp_pack_*`, `packed-refs.lock`.

## Gotchas

- `[doc]` NOTES: concurrent gc "may corrupt the repository if the other process later adds
  a reference to the deleted object"; the `--prune` grace period is the mitigation, and
  `now` removes it.
- gc keeps everything reachable from refs, the index, reflogs and any worktree; a note
  does not keep its target alive `[doc]`.
- It does not remove a `.pack` without `.idx` or a `.keep` `[observed]`.
- Automatic gc runs after many porcelain commands; inspections in `deep` pass
  `-c gc.auto=0 -c maintenance.auto=false`.
