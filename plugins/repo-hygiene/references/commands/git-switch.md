# git switch

Official: https://git-scm.com/docs/git-switch · Areas: G1, G3, G5, G9 · Floor: 2.23

## Purpose in an audit

The literal command for approved items that leave a branch (before deleting it), leave a
detached HEAD, or create a recovery branch. Know what it refuses and what it silently
overwrites.

## Safety class

| Form | Class | Why |
| --- | --- | --- |
| `git switch <branch>` | mutates (HEAD, index, working tree) | Carries local changes when they do not conflict `[observed]` |
| `git switch -c <new> [<start>]` | mutates (refs) | Creates a branch |
| `git switch -C <name> <start>` | mutates | Resets an existing branch to `<start>`: its unique commits leave the branch |
| `git switch --discard-changes <branch>` | mutates | Throws away local changes `[doc]` |
| `git switch --detach <rev>` | mutates (HEAD) | Detached HEAD |
| `git switch --orphan <new>` | mutates | Unborn branch; all tracked files removed `[doc]` |
| `--ignore-other-worktrees` | mutates | Checks out a branch another worktree holds `[doc]` |

## Options that matter

- `-m`/`--merge`: three-way merge of local changes into the target `[doc]`.
- `--recurse-submodules`: update submodule working trees too `[doc]`.
- `--no-overwrite-ignore`: abort when the target would overwrite ignored files
  `[observed]` (see Gotchas).
- `-t`/`--track`, `--guess`/`--no-guess` (`checkout.defaultRemote`) `[doc]`.
- `--conflict=<style>` with `-m` `[doc]`.

## Verified recipes

On disposable fixtures:

```sh
git switch held
```

`[observed]`: `fatal: 'held' is already used by worktree at '<path>'`, exit 128.

```sh
git switch --discard-changes main
```

`[observed]`: an unstaged edit to `f` was dropped; `git switch main` without the flag had
carried it over (`M f`).

```sh
git switch --detach HEAD
git symbolic-ref -q HEAD
```

`[observed]`: exit 1 (detached); reflog entry `checkout: moving from main to HEAD`.

```sh
git switch --no-overwrite-ignore other
```

`[observed]`: `error: The following untracked working tree files would be overwritten by
checkout: local.cfg` and the switch stopped.

## Footprint it leaves when interrupted or misused

- Reflog entries `checkout: moving from <a> to <b>` (the reflog calls every switch
  "checkout") `[observed]`.
- A detached HEAD after `--detach` or after checking out a tag or remote branch.

## Gotchas

- **Ignored files are overwritten silently by default**: with `local.cfg` ignored and
  holding local settings, `git switch other` (where `local.cfg` is tracked) replaced it
  with the branch version, no warning `[observed]`. Pass `--no-overwrite-ignore` in every
  approved switch when ignored files such as `.env` or local config exist.
- A worktree holding a branch blocks switching to it; `prunable` worktrees still hold
  theirs (G9).
