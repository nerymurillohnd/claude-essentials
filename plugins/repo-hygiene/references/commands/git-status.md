# git status

Official: https://git-scm.com/docs/git-status · Areas: G3, G4, G8, G10 · Floor: any
(`--porcelain=v2` stash line: 2.35)

## Purpose in an audit

One snapshot of staged, unstaged, conflicted, untracked and (on request) ignored paths,
plus branch, upstream and stash headers. Parse only `--porcelain=v2`; the long format is for
explaining an operation in progress to the user.

## Safety class

| Form | Class | Why |
| --- | --- | --- |
| `git --no-optional-locks status --porcelain=v2 …` | read | Skips the opportunistic index refresh and its lock `[doc]` (BACKGROUND REFRESH) |
| `git status` (no `--no-optional-locks`) | writes-local-state | "refresh the index, updating the cached stat information … and writing out the result" `[doc]` |
| any form with `core.fsmonitor` set to a hook path | executes-config | The FSMonitor hook runs to list changed files `[doc]` (`git-update-index`, FILE SYSTEM MONITOR). In `deep`, add `-c core.fsmonitor=false` |
| any form in a repository with submodules | read (recursive) | Runs status inside submodules; `GIT_OPTIONAL_LOCKS=0` is inherited `[doc]` (`git`) |

## Options that matter

- `--porcelain=v2`: stable format "regardless of user configuration" `[doc]`. Line kinds:
  `1` changed, `2` renamed/copied, `u` unmerged, `?` untracked, `!` ignored, `#` header.
  `XY` uses `.` for unchanged; `<sub>` is `N...` or `S<c><m><u>` for submodules (commit
  changed, tracked changes, untracked changes) `[doc]`.
- `--branch`: `# branch.oid`, `# branch.head` (`(detached)`), `# branch.upstream`,
  `# branch.ab +A -B` `[doc]`.
- `--show-stash`: `# stash <N>` when non-zero `[doc]`.
- `-u<mode>` / `--untracked-files=<mode>`: `no`, `normal` (directories collapsed), `all`
  (every file). Given without a mode it means `all`, and the mode must be stuck to the
  option (`-uno`, not `-u no`) `[doc]`. Use `normal` for counts, `all` only bounded.
- `--ignored[=<mode>]`: `traditional` (default), `no`, `matching` (only paths that match a
  pattern; contents of an ignored directory not listed) `[doc]`.
- `--ignore-submodules[=<when>]`: `none`, `untracked`, `dirty`, `all` (default when given
  without a value). Use `none` in audits to override `submodule.<name>.ignore` `[doc]`.
- `-z`: NUL-terminated, unquoted paths; alone it implies `--porcelain=v1` `[doc]`.
- `--no-ahead-behind`: skip the ahead/behind count on huge histories `[doc]`.
- `--no-renames` / `--find-renames[=<n>]`: control rename detection `[doc]`.
- Avoid `-v` / `-v -v`: prints staged and unstaged patches (file contents) `[doc]`.

## Verified recipes

```sh
git --no-optional-locks --no-pager status --porcelain=v2 --branch --show-stash \
  --untracked-files=normal
```

`[observed]` on the main fixture: `# branch.head (detached)` (bisect in progress),
`# stash 2`, five `?` lines, no line for a file with a hidden assume-unchanged edit.

```sh
git --no-optional-locks --no-pager status --porcelain=v2 --ignored=matching \
  --untracked-files=normal | awk '{print $1}' | sort | uniq -c
```

`[observed]`: `4 !`, `5 ?`, `1 #`; the `!` lines were `.env`, `debug.log`, `dist/`,
`node_modules/`.

```sh
git --no-optional-locks --no-pager status --porcelain=v2 --ignore-submodules=none
```

`[observed]` in a superproject: `1 .M SC.. 160000 160000 160000 <sha> <sha> libs/a` for a
submodule checked out at another commit; `? nested/` for an untracked nested repository.

## Footprint it leaves when interrupted or misused

- Without `--no-optional-locks`: a transient `index.lock` and a rewritten `index`.
- An interrupted run can leave `index.lock` behind; every later write then fails with
  `Unable to create '…/index.lock': File exists` while `status` itself still exits 0
  `[observed]`.

## Gotchas

- Porcelain v2 does **not** report a merge, rebase, cherry-pick, revert, am or bisect in
  progress; the long format does ("You are currently reverting commit f90c32b.")
  `[observed]`. Detect operations with `git rev-parse --git-path` (see
  `areas/repository-and-operations.md`).
- `status.showStash=true` in config adds `# stash <N>` to porcelain v2 even without
  `--show-stash` `[observed]`.
- Files hidden by assume-unchanged or skip-worktree never appear `[observed]`; see
  `commands/git-ls-files.md` (`-v`).
- A directory whose `.git` file points to a missing repository does not appear at all,
  while `git ls-files -o` lists it `[observed]`.
- With `core.autocrlf=true`, stderr carries `LF will be replaced by CRLF` warnings
  `[observed]`; they are not errors.
- `core.filemode=false` hides executable-bit changes `[observed]`.
