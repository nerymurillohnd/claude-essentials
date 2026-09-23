# git revert

Official: https://git-scm.com/docs/git-revert · Areas: G2, G14 · Floor: any

## Purpose in an audit

Recognise an unfinished revert (G2). As an item, undo a published commit without
rewriting history. Reverting does not remove a secret from history (G14).

## Safety class

| Form | Class | Why |
| --- | --- | --- |
| `revert <commit>…` | mutates, executes-config | new commits; hooks and merge drivers run |
| `--no-commit` / `-n` | mutates | index and worktree |
| `--abort`, `--quit`, `--skip`, `--continue` | mutates | sequencer state |

## Options that matter

- `-m <parent>`: required to revert a merge; reverting a merge makes Git consider the
  merged commits "already merged" for future merges (documented pitfall).
- `--no-edit`, `-s`, `--reference` (message style).

## Verified recipes

Detect state (reads):

```sh
git rev-parse -q --verify REVERT_HEAD; echo "exit=$?"
ls <git-dir>/sequencer 2>/dev/null
```

`[observed]` scratch repository: a clean `git revert --no-edit HEAD~1` exited 0 and left
no `REVERT_HEAD`; `git revert --abort` then reported "no cherry-pick or revert in
progress".

## Footprint it leaves when interrupted or misused

`REVERT_HEAD`, `MERGE_MSG`, `AUTO_MERGE`, `sequencer/` for multi-commit reverts, conflict
markers.

## Gotchas

- A revert of a secret-adding commit leaves the secret in history; rotation plus history
  rewriting (G14) is the fix.
- The same `sequencer/` directory serves cherry-pick; `REVERT_HEAD` vs `CHERRY_PICK_HEAD`
  tells which one stopped.
