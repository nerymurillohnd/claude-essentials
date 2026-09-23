# git merge

Official: https://git-scm.com/docs/git-merge · Areas: G2, G5 · Floor: any
(`AUTO_MERGE` 2.42, `--autostash` 2.27)

## Purpose in an audit

Recognise the footprint of an unfinished merge (G2) and, in the program phase, integrate a
preserved history with a normal merge as an approved item. For "would this merge change
anything", use `commands/git-merge-tree.md`, never a real merge.

## Safety class

| Form | Class | Why |
| --- | --- | --- |
| `merge <commit>` | mutates, executes-config | moves HEAD, index, worktree; runs merge drivers, `pre-merge-commit`, `commit-msg`, `post-merge` hooks |
| `merge --no-commit`, `--squash` | mutates | changes index and worktree |
| `merge --abort` | mutates | resets to `ORIG_HEAD`; with `--autostash`, reapplies the stash |
| `merge --quit` | mutates | forgets the merge state, leaves the tree as is |
| `merge --continue` | mutates | commits the resolution |
| `-s ours` | mutates | records a merge that discards the other side's content |

## Options that matter

- `--ff-only`, `--no-ff`: whether a merge commit appears.
- `--autostash`: stashes local changes into `MERGE_AUTOSTASH` for the duration.
- `-X ours|theirs`: strategy options (content-changing).
- `-s ours` hides content; the program phase never uses it (spec D15).
- `rerere.enabled`: records resolutions in `rr-cache/` (`MERGE_RR` appears).

## Verified recipes

Detect an unfinished merge (reads):

```sh
git rev-parse -q --verify MERGE_HEAD; echo "exit=$?"
ls <git-dir> | grep -E '^(MERGE_|AUTO_MERGE|ORIG_HEAD)'
```

`[observed]` in a scratch repository, a conflicted `git merge --autostash side` left
`AUTO_MERGE MERGE_AUTOSTASH MERGE_HEAD MERGE_MODE MERGE_MSG MERGE_RR ORIG_HEAD`; `git merge
--abort` printed "Applied autostash." and restored the staged file.

## Footprint it leaves when interrupted or misused

`MERGE_HEAD`, `MERGE_MSG`, `MERGE_MODE`, `MERGE_RR` (rerere), `MERGE_AUTOSTASH`,
`AUTO_MERGE` (tree of the auto-merged result, 2.42), `ORIG_HEAD`; conflict markers in the
worktree; `*.orig` files if a mergetool ran.

## Gotchas

- A `MERGE_AUTOSTASH` holds the user's local changes during the merge. `merge --abort`
  reapplies it `[observed]`; `merge --quit` saves it to the stash list `[doc]`. After a
  crash, the file's OID is the only pointer: record it before any cleanup.
- `ORIG_HEAD` is overwritten by many commands; it is evidence only right after the
  operation.
- Rerere may resolve conflicts automatically with an old recorded resolution.
