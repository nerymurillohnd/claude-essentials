# git checkout

Official: https://git-scm.com/docs/git-checkout · Areas: G1, G3, G5 · Floor: any

## Purpose in an audit

Recognize its footprint and its two meanings: switching branches (prefer
`commands/git-switch.md`) and overwriting files from the index or a commit (prefer
`commands/git-restore.md`). The audit writes `switch` or `restore` in its items because
their names say what they do.

## Safety class

| Form | Class | Why |
| --- | --- | --- |
| `git checkout <branch>` | mutates | Like `git switch` |
| `git checkout -b\|-B <branch> [<start>]` | mutates (refs) | `-B` resets an existing branch `[doc]` |
| `git checkout [<tree-ish>] -- <path>` | mutates (working tree, index) | Overwrites files; local edits are lost |
| `git checkout -f` / `--force` | mutates | When switching, throws away local changes "and any untracked files or directories that are in the way"; with paths, ignores unmerged entries `[doc]` |
| `git checkout --orphan <new>` | mutates | New unborn branch `[doc]` |
| `git checkout -p` | mutates | Interactive; not used |
| `--ignore-other-worktrees` | mutates | Checks out a branch another worktree holds `[doc]` |

## Options that matter

- `--overwrite-ignore` (default) / `--no-overwrite-ignore`: "Silently overwrite ignored
  files when switching branches. This is the default behavior." `[doc]`.
- `--overlay` (default for checkout) / `--no-overlay`: with no-overlay, files absent from
  `<tree-ish>` are removed `[doc]`.
- `-m`/`--merge`, `--conflict=<style>`, `--ours`, `--theirs` for unmerged paths `[doc]`.
- `--recurse-submodules` `[doc]`.
- `-d`/`--detach`, `--guess` (`checkout.defaultRemote`), `-t`/`--track` `[doc]`.
- `--pathspec-from-file`, `--pathspec-file-nul` `[doc]`.
- `--` separates revisions from paths; without it, a name that is both a branch and a
  file is ambiguous (gitcli; contract section 3).

## Verified recipes

On disposable fixtures:

```sh
git checkout held
```

`[observed]`: `fatal: 'held' is already used by worktree at '<path>'`.

```sh
git checkout -q --no-overwrite-ignore other
```

`[observed]`: refused with `The following untracked working tree files would be
overwritten by checkout: local.cfg`; the ignored `local.cfg` kept its local content.

## Footprint it leaves when interrupted or misused

- Reflog entries `checkout: moving from <a> to <b>`.
- Detached HEAD after checking out a commit, tag or remote-tracking branch.
- `git checkout -- <path>` leaves no record of what it overwrote.

## Gotchas

- Without `--no-overwrite-ignore`, switching to a branch that tracks a path you keep
  ignored (`.env`, local config) replaces your file silently; observed with `git switch`,
  which shares this default (see `commands/git-switch.md`).
- `git checkout <name>` means "switch" if `<name>` is a branch and "restore file" if it is
  only a path: always use `--` or the dedicated commands.
- Skip-worktree and sparse-checkout entries are not written unless needed (conflicts)
  `[doc]` (`git-update-index`).
