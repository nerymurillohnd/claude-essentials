# git prune

Official: https://git-scm.com/docs/git-prune · Areas: G16, G17 · Floor: any

## Purpose in an audit

Preview which loose unreachable objects a prune would delete. The deletion itself is only
ever reached through the reclamation runbook (`gc --prune=…`), never called directly.

## Safety class

| Form | Class | Why |
| --- | --- | --- |
| `prune --dry-run [--verbose] [--expire <time>]` | read | lists what would go |
| `prune [--expire <time>]` | mutates | deletes loose unreachable objects; irreversible |
| `prune-packed [--dry-run]` | mutates (read with `-n`) | deletes loose objects already in packs |

## Options that matter

- `--expire <time>`: only objects older than `<time>`. **Without it there is no grace
  period** `[observed]`: `--dry-run` alone listed the same 7 objects as `--expire=now`.
- `<head>…`: extra roots to keep.
- It keeps objects reachable from refs, reflogs and the index of every worktree; it only
  handles loose objects (packs are `repack`'s job; cruft packs expire via `gc`).

## Verified recipes

```sh
git --no-replace-objects prune --dry-run --expire=2.weeks.ago | awk '{print $2}' | sort | uniq -c
git --no-replace-objects prune --dry-run --expire=now | awk '{print $2}' | sort | uniq -c
git prune-packed --dry-run | wc -l
```

`[observed]` fixture (all objects minutes old): 0 with the two-week window; 2 blob, 1
commit, 4 tree with `now`; 0 prune-packable.

## Footprint it leaves when interrupted or misused

A partially pruned store; with a concurrent writer, a ref to a deleted object (corruption,
see `commands/git-gc.md`).

## Gotchas

- The census in `fsck --unreachable` (with reflogs) matches what `prune` would consider;
  reflog-protected objects are not pruned until the reflog entries expire.
- A shallow or partial clone has more "missing" objects by design; never prune to "fix"
  them.
