# git reflog

Official: https://git-scm.com/docs/git-reflog · Areas: G5, G8, G16 · Floor: any
(`list` 2.45, `drop` 2.50)

## Purpose in an audit

Read where each ref has been (lost commits, rewritten tips, stash entries), and, as
approved deep items only, expire or delete entries during reclamation.

## Safety class

| Form | Class | Why |
| --- | --- | --- |
| `show [<log-options>] [<ref>]` (default) | read | same as `git log -g --oneline` |
| `list` | read | names every reflog (2.45) |
| `exists <ref>` | read | exit 0 if a reflog exists |
| `expire --dry-run [--verbose] …`, `delete --dry-run …` | read | reports what would go |
| `expire …` | mutates | removes entries; objects they held become unreachable |
| `delete <ref>@{<n>}` | mutates | removes single entries (`git stash drop` uses this) |
| `drop <ref>…` / `drop --all` | mutates | deletes whole reflogs (2.50) |
| `write <ref> <old> <new> <msg>` | mutates | appends an entry |

## Options that matter

- `--expire=<time>` (default `gc.reflogExpire`, 90 days), `--expire-unreachable=<time>`
  (default `gc.reflogExpireUnreachable`, 30 days): `now` removes everything.
- `--all` with `--single-worktree`: limit to the current worktree.
- `--rewrite`, `--updateref`: adjust neighbouring entries / the ref itself (used by stash).
- `--stale-fix`: prune entries pointing at broken commits (expensive).
- `--verbose` with `--dry-run`: without it nothing is printed `[observed]`.

## Verified recipes

```sh
git --no-replace-objects --no-pager log -g --format='%h %gd %gs' -n 50 HEAD
git --no-pager reflog list
git reflog exists refs/heads/main; echo "exit=$?"
git --no-replace-objects --no-pager log -g --all --format='%gd %h %gs' | grep -E 'faafec8'
git reflog expire --dry-run --verbose --expire=now --expire-unreachable=now --all | grep -c '^would prune'
git reflog delete --dry-run --verbose 'refs/stash@{1}'
```

`[observed]` `faafec8 HEAD@{11} commit: lost commit`; `main@{6}` also holds it; 67 entries
would be pruned; `would prune On main: old experiment` / `keep On main: untracked stash …`,
and `git stash list` still had 2 entries afterwards.

## Footprint it leaves when interrupted or misused

`logs/<ref>.lock` on a crash. After `expire --expire=now --all`: `[observed]` `git stash
list` was empty while `refs/stash` still existed, and the lower stash entries were
unreachable.

## Gotchas

- Deleting or pruning a ref deletes its reflog: `[observed]` a pruned remote-tracking ref's
  reflog was gone.
- Reflogs are local and per clone; they are not in a bundle, a clone or a push.
- `HEAD`'s reflog is per worktree; each linked worktree has its own.
- New refs outside `refs/heads`, `refs/remotes`, `refs/notes` and HEAD get no reflog unless
  `core.logAllRefUpdates=always` or `--create-reflog` `[observed]` (a `refs/recovered/*` pin
  had none).
