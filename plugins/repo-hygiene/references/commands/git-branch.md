# git branch

Official: https://git-scm.com/docs/git-branch · Areas: G5 · Floor: any

## Purpose in an audit

List local branches with their upstream and merge state, and, as an approved item, delete,
rename or re-point one. For machine-readable inventories prefer `git for-each-ref` (same
format atoms); `git branch --format` is fine for filters such as `--merged`.

## Safety class

| Form | Class | Why |
| --- | --- | --- |
| `--list`, `-a`, `-r`, `--format=…`, `--merged`, `--no-merged`, `--contains`, `--no-contains`, `--points-at`, `--show-current` | read | lists refs |
| `-v`, `-vv` | read | human output; do not parse |
| `-d <b>` | mutates | deletes a ref and its reflog |
| `-D <b>` (`-d -f`) | mutates | deletes even when unmerged, or pointing at an invalid commit |
| `-m`/`-M`, `-c`/`-C` | mutates | rename or copy; `-M`/`-C` overwrite an existing name |
| `-f <b> <start>` | mutates | re-points an existing branch; old tip only in the reflog |
| `-u`, `--set-upstream-to`, `--unset-upstream`, `--edit-description` | mutates | writes config (`branch.<b>.*`); `--edit-description` runs the editor (executes config) |
| `<new> [<start>]` | mutates | creates a ref |

## Options that matter

- `--merged <commit>` / `--no-merged <commit>`: tips reachable (not reachable) from
  `<commit>`, HEAD by default. Pure ancestry: a squash-merged branch appears in
  `--no-merged`.
- `--contains` / `--no-contains <commit>`: branches holding a commit (who would be affected
  by rewriting it).
- `--sort=-committerdate`, `--format='%(refname:short) %(upstream:track)'`: see
  `commands/git-for-each-ref.md`; `branch.sort` in config changes the default order.
- `-r` remote-tracking only, `-a` both. `--omit-empty` (2.41) drops empty format lines.
- `-d` refuses unless the branch is "fully merged in its upstream branch, or in HEAD if no
  upstream was set" `[doc]`; it also refuses a branch checked out in any worktree, and one
  being bisected or rebased `[observed]`.
- `-D` has no safety check beyond the worktree rule. Record the SHA first; the reflog of
  the deleted branch is deleted with it.

## Verified recipes

```sh
git --no-replace-objects --no-pager branch --format='%(refname:short)' --merged origin/main
git --no-replace-objects --no-pager branch --format='%(refname:short)' --merged feat/squashed
git --no-pager branch --format='%(refname:short) %(upstream:track)' --list 'feat/*'
```

`[observed]` `--merged main` listed `main`, `wt/branch`, `wt/live` (branches at the same
commit count as merged). Approved deletes, one per call:

```sh
git branch -d feat/merged
git branch -D feat/squashed
```

`[observed]` `-d feat/squashed` → "not fully merged", exit 1; `-d feat/merged` → "Deleted
branch feat/merged (was c3544d8)"; recovery `git branch feat/merged c3544d8…`.

## Footprint it leaves when interrupted or misused

- A deleted branch leaves no reflog; only `HEAD`'s reflog may still name its commits.
- `-f`/`-M` leave the previous tip only in the reflog of the (new) name.
- `--set-upstream-to` to a remote that is later removed leaves `branch.<b>.remote` pointing
  nowhere (`areas/branches-remotes-tags.md` check 3).

## Gotchas

- `[observed]` `git branch -d loc/abandoned` **succeeded** although the branch was not in
  `main`: it was merged into its upstream, a stale remote-tracking ref of a branch already
  deleted on the server. Git warned "not yet merged to HEAD". `-d` is not "merged into the
  default branch".
- `[observed]` `git branch -D main` failed while a bisect had detached HEAD
  (`BISECT_START` named `main`), even though `%(worktreepath)` was empty.
- `[observed]` on case-insensitive filesystems, `git branch feat/MERGED` was listed as
  `Feat/MERGED` because a `Feat/` directory already existed.
- Counts and `--merged` honor replace refs; use `git --no-replace-objects branch …`.
