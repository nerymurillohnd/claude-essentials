# git rebase

Official: https://git-scm.com/docs/git-rebase · Areas: G2, G5, G16 · Floor: any

## Purpose in an audit

Recognise an unfinished rebase (G2), reconstruct what it was doing from its state files,
and know which tips it rewrote (reflog). Rebasing is never an audit action; in the program
phase history is integrated with merges.

## Safety class

| Form | Class | Why |
| --- | --- | --- |
| `rebase <upstream>`, `-i`, `--onto`, `--rebase-merges` | mutates, executes-config | rewrites commits and moves the branch; runs `pre-rebase`, commit hooks, `exec` lines, `sequence.editor` |
| `--abort` | mutates | restores the original branch and HEAD |
| `--quit` | mutates | forgets the rebase, leaves HEAD where it is |
| `--skip`, `--continue`, `--edit-todo` | mutates | sequencer steps |
| `--autostash` | mutates | stash kept in `rebase-merge/autostash` while running |
| `--update-refs` | mutates | also moves other branches pointing into the series |

## Options that matter

- `--rebase-merges`: recreates merges; uses `refs/rewritten/*` (per-worktree) labels.
- `--exec <cmd>`: runs a shell command per commit (execution).
- `--fork-point`: default when no upstream is given; uses the upstream's reflog.
- `rebase.autoStash`, `rebase.updateRefs`, `rebase.missingCommitsCheck`.

## Verified recipes

Detect and describe the state (reads):

```sh
ls -d <git-dir>/rebase-merge <git-dir>/rebase-apply 2>/dev/null
head -c 200 <git-dir>/rebase-merge/head-name
head -c 200 <git-dir>/rebase-merge/onto
wc -l < <git-dir>/rebase-merge/done
grep -c -v -E '^(#|$)' <git-dir>/rebase-merge/git-rebase-todo
git --no-pager for-each-ref --format='%(refname)' refs/rewritten
```

`[observed]` scratch repository: a conflicted `git rebase --rebase-merges side` left
`AUTO_MERGE`, `ORIG_HEAD`, `REBASE_HEAD` and `rebase-merge/` with `head-name`, `onto`,
`orig-head`, `done`, `git-rebase-todo`, `git-rebase-todo.backup`, `stopped-sha`,
`message`, `author-script`, `patch`, `refs-to-delete` and others, plus the ref
`refs/rewritten/onto`.

## Footprint it leaves when interrupted or misused

`rebase-merge/` (interactive / merge backend) or `rebase-apply/` (apply backend, also used
by `git am`), `REBASE_HEAD`, `ORIG_HEAD`, `AUTO_MERGE`, `refs/rewritten/*`, an autostash
commit, a detached HEAD, and the branch named in `head-name` blocked from deletion
`[observed]` (see `commands/git-branch.md`).

## Gotchas

- `rebase-merge/patch` and `message` contain diff text and commit messages: read names and
  counts, not those files.
- The pre-rebase tip is in `rebase-merge/orig-head` and in the branch reflog entry before
  `rebase (finish)`; `HEAD`'s reflog shows `rebase (start)`. It is the recovery point.
- `rebase-apply/` alone may mean an interrupted `git am`, not a rebase; G2 tells them apart
  from the reflog (`am:` vs `rebase` entries).
- `%(worktreepath)` is empty for the branch being rebased (HEAD is detached).
