# git symbolic-ref

Official: https://git-scm.com/docs/git-symbolic-ref · Areas: G5, G6, G15 · Floor: any

## Purpose in an audit

Read what `HEAD` and `refs/remotes/<remote>/HEAD` point to: detached or on a branch, and
which branch the local copy believes is the remote default.

## Safety class

| Form | Class | Why |
| --- | --- | --- |
| `symbolic-ref [-q] [--short] [--no-recurse] <name>` | read | prints the target |
| `symbolic-ref <name> <ref>` | mutates | re-points a symbolic ref |
| `symbolic-ref --delete <name>` | mutates | deletes a symbolic ref |

## Options that matter

- `-q`: no error message when `<name>` is detached; exit 1.
- `--short`: `main` instead of `refs/heads/main`.
- `--no-recurse`: stop at the first level of a symref chain.

## Verified recipes

```sh
git symbolic-ref -q HEAD; echo "exit=$?"
git symbolic-ref --short refs/remotes/origin/HEAD
git --no-pager ls-remote --symref origin HEAD
```

`[observed]` exit 1 (HEAD detached by an unfinished bisect); `origin/main`; the server
reported `ref: refs/heads/main HEAD`. A local `origin/HEAD` that differs from the server's
`HEAD` means the default branch changed upstream; the fix is the item `git remote set-head
origin --auto` (network, writes).

## Footprint it leaves when interrupted or misused

Pointing HEAD at a non-existent branch gives an "unborn" HEAD; `--delete` of HEAD breaks
the worktree.

## Gotchas

- Detached HEAD is exit 1 with `-q`, not an error: check G2 for the operation that
  detached it (bisect, rebase).
- `refs/remotes/<r>/HEAD` is only as fresh as the last `clone`, `remote set-head`, or a
  fetch that updates it.
