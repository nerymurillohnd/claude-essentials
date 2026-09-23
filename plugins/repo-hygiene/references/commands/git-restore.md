# git restore

Official: https://git-scm.com/docs/git-restore · Areas: G3 · Floor: 2.23

## Purpose in an audit

The literal command for an approved "discard these changes" or "unstage these paths" item.
It overwrites files; uncommitted content it replaces is not recoverable from Git.

## Safety class

| Form | Class | Why |
| --- | --- | --- |
| `git restore -- <path>` (default `--worktree`) | mutates (working tree) | Replaces the file with the index version; the edit is gone |
| `git restore --staged -- <path>` | mutates (index) | Unstages; the working file stays |
| `git restore --staged --worktree -- <path>` | mutates | Both, from `HEAD` by default |
| `git restore --source=<tree> …` | mutates | From any commit; in the default no-overlay mode, removes tracked files absent from `<tree>` `[doc]` |
| `git restore --merge -- <path>` | mutates | Re-creates the conflicted merge in the file |
| `git restore -p` | mutates | Interactive; not used by the audit |

## Options that matter

- `-W`/`--worktree` (default), `-S`/`--staged` `[doc]`.
- `-s <tree>`/`--source=<tree>`: default is the index for `--worktree`, `HEAD` for
  `--staged` `[doc]`.
- `--overlay` / `--no-overlay` (default no-overlay: remove files not in the source)
  `[doc]`.
- `--ours`, `--theirs`, `-m`/`--merge` (re-create the conflicted merge; not with
  `--source`), `--conflict=<style>` for unmerged paths `[doc]`.
- `--ignore-unmerged`: leave unmerged paths alone instead of aborting `[doc]`.
- `--recurse-submodules`: without it, submodule working trees are not updated `[doc]`.
- `--pathspec-from-file`, `--pathspec-file-nul` `[doc]`.

## Verified recipes

On a disposable fixture:

```sh
git restore f
```

`[observed]`: an unstaged edit in `f` was replaced by the index version.

```sh
git restore --source=HEAD~1 --staged --worktree -- .
```

`[observed]`: `new.txt`, added in `HEAD`, was deleted from the working tree and the index
(`1 D.` in porcelain v2): no-overlay mode.

## Footprint it leaves when interrupted or misused

- No reflog entry, no backup: the overwritten content is gone unless it was once staged
  (then a dangling blob may remain until `gc`).

## Gotchas

- `git restore .` from a subdirectory only touches that subdirectory.
- With `--source`, files absent from the source are **deleted** `[observed]`; add
  `--overlay` when that is not wanted.
- Before any restore item, save the at-risk content (`git stash push -- <path>` or a copy
  outside the repository) as a separate preservation item.
