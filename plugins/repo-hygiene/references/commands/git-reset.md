# git reset

Official: https://git-scm.com/docs/git-reset · Areas: G2, G3, G16 · Floor: any

## Purpose in an audit

Two roles: recognizing its footprint (`ORIG_HEAD`, `reset: moving to …` reflog entries,
commits lost to `--hard`), and the literal command for approved unstage or move-back items.

## Safety class

| Form | Class | Why |
| --- | --- | --- |
| `git reset -q HEAD -- <path>` | mutates (index) | Unstages paths; working tree untouched |
| `git reset --soft <commit>` | mutates (ref) | Moves the branch; index and working tree unchanged `[doc]` |
| `git reset [--mixed] <commit>` | mutates (ref, index) | Default mode `[doc]` |
| `git reset --hard <commit>` | mutates (ref, index, working tree) | "Overwrite all files and directories … and may overwrite untracked files" `[doc]`; uncommitted edits are lost |
| `git reset --merge <commit>` | mutates | Keeps unstaged changes; aborts on conflict `[doc]` |
| `git reset --keep <commit>` | mutates | Aborts if a changed file has local changes `[doc]` |
| `--recurse-submodules` | mutates submodules | Resets their working trees too `[doc]` |

## Options that matter

- `-N` with `--mixed`: removed paths become intent-to-add `[doc]`.
- `--no-refresh`: skip the index refresh after a mixed reset `[doc]`.
- `-q`, `--pathspec-from-file`, `-p` (interactive; not used) `[doc]`.
- `ORIG_HEAD` records the previous tip for commands that move `HEAD` drastically
  (`[doc]` git-reset, git-merge).

## Verified recipes

On a disposable fixture:

```sh
git reset -q --hard HEAD~1
cat "$(git rev-parse --git-path ORIG_HEAD)"
git --no-pager reflog -n 3 --format='%gd %h %gs'
```

`[observed]`: `ORIG_HEAD` held the old tip; `HEAD@{0} reset: moving to HEAD~1`,
`HEAD@{1} … commit: c2`; the uncommitted edit in `f` was lost; the untracked
`untracked.txt` stayed.

Recovery for a commit moved away from by reset (approved item):

```sh
git branch recover/c2 aa96d618fcb3ab55ac4cf5ec1a01ce63fc6a1650
```

`[observed]`: `recover/c2` pointed at `aa96d61 c2`. Use the SHA from `ORIG_HEAD` or the
reflog; see the reflog area (G16) and `commands/git-reflog.md`.

## Footprint it leaves when interrupted or misused

- `ORIG_HEAD` (single value, no history) and reflog entries `reset: moving to <rev>`
  `[observed]`.
- Commits reachable only from the reflog until it expires (`gc.reflogExpire`,
  `gc.reflogExpireUnreachable`), then pruned.
- Working-tree edits discarded by `--hard` leave nothing, unless they were staged
  (dangling blobs).

## Gotchas

- `git reset --hard` in a repository with an assume-unchanged or skip-worktree file may
  overwrite a hidden edit (see `commands/git-update-index.md`).
- `ORIG_HEAD` is overwritten by the next reset, merge, rebase or am: read it early.
- `reset --hard` does not delete untracked files `[observed]` but can overwrite an
  untracked file whose path exists in the target `[doc]`.
