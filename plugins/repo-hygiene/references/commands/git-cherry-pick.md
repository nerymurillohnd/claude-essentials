# git cherry-pick

Official: https://git-scm.com/docs/git-cherry-pick · Areas: G2, G5, G16 · Floor: any

## Purpose in an audit

Recognise an unfinished cherry-pick (G2), and, in the program phase, bring a recovered
commit onto a branch as an approved item. Patch-equivalence checks use `git cherry` /
`git patch-id`, not a real pick.

## Safety class

| Form | Class | Why |
| --- | --- | --- |
| `cherry-pick <commit>…` | mutates, executes-config | new commits on HEAD; merge drivers and commit hooks run |
| `--no-commit` / `-n` | mutates | index and worktree only |
| `--abort`, `--quit`, `--skip`, `--continue` | mutates | state machine of the sequencer |
| `-x` | mutates | appends "(cherry picked from commit …)" — keeps provenance; prefer it |

## Options that matter

- `-x`: record the source SHA in the message (traceability for recovered work).
- `--empty=drop|keep|stop`, `--allow-empty`, `--keep-redundant-commits`: what happens when
  the change already landed.
- `-m <parent>`: pick a merge relative to a parent.
- `--ff`: fast-forward when possible.

## Verified recipes

Detect state (reads):

```sh
git rev-parse -q --verify CHERRY_PICK_HEAD; echo "exit=$?"
ls <git-dir>/sequencer 2>/dev/null
```

`[observed]` scratch repository: a conflicting single pick left `AUTO_MERGE
CHERRY_PICK_HEAD MERGE_MSG MERGE_RR ORIG_HEAD`; a two-commit pick that stopped also left
`sequencer/` with `abort-safety`, `head`, `todo`.

## Footprint it leaves when interrupted or misused

`CHERRY_PICK_HEAD`, `MERGE_MSG`, `AUTO_MERGE`, `ORIG_HEAD`, `sequencer/` (`todo`, `head`,
`abort-safety`, `opts`), conflict markers.

## Gotchas

- `sequencer/` is shared with `revert`; read `sequencer/todo` (commands and SHAs, no file
  content) to see what remained.
- `--quit` leaves the picked commits and forgets the rest of the todo.
- Picking a commit that already landed by squash produces an empty or conflicting pick;
  check the ladder first.
