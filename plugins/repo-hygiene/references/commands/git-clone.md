# git clone

Official: https://git-scm.com/docs/git-clone · Areas: G1, G22, G8, G15 · Floor: any

## Purpose in an audit

Two uses: (1) make a safe copy of an untrusted local repository before auditing it
(`--no-local`, so its config and hooks never run), and (2) make a backup before a risky
item. Know exactly which refs each form copies.

## Safety class

| Form | Class | Why |
| --- | --- | --- |
| `git clone --no-local <path> <new-path>` | network (local transport), mutates outside | New repository; source config and hooks are not copied `[doc]` (git SECURITY), `[observed]` |
| `git clone <path>` (local, default `--local`) | mutates outside | Copies or hardlinks `.git/objects`; refuses repositories owned by another user without `--no-local` `[doc]` |
| `git clone --mirror` | mutates outside | Bare copy of every ref under `refs/*` `[doc]` |
| `git clone --recurse-submodules` | network, mutates outside | Also clones submodules |
| `git clone <url>` | network | Downloads |

## Options that matter

- `--no-local`: use the Git transport for a local path; required for repositories owned by
  other users `[doc]`. `--local` fails if `$GIT_DIR/objects` holds symlinks `[doc]`.
- `--no-hardlinks`: copy object files instead of hardlinking; desirable for backups `[doc]`.
- `--mirror` (implies `--bare`): all refs, and `remote.origin.fetch=+refs/*:refs/*`,
  `remote.origin.mirror=true` `[doc]`, `[observed]`.
- `--bare`, `--no-checkout` `[doc]`.
- `--reference[-if-able]=<repo>` sets up `objects/info/alternates`; `--dissociate` copies
  the borrowed objects and stops borrowing `[doc]`.
- `--depth`, `--shallow-since`, `--filter=<spec>` (`blob:none`, `blob:limit=<n>`),
  `--also-filter-submodules`, `--reject-shallow` `[doc]`.
- `--template=<dir>`: template files copied into the new `.git/` `[doc]`.
- `-c <key>=<value>`/`--config`: written into the new repository's config before fetch
  and checkout `[doc]`.
- `--bundle-uri=<uri>`: fetches a bundle first; refs land in `refs/bundle/*` `[doc]`.

## Verified recipes

```sh
git clone -q --no-local --no-checkout <audited-repo> <scratch>/cl
git -C <scratch>/cl config --local --name-only --list
```

`[observed]`: the copy's config held only `core.*`, `remote.origin.url` and
`remote.origin.fetch`; the source's `core.hooksPath`, `alias.nuke` and `url.*.insteadOf`
were absent; no non-sample hooks; no `objects/info/alternates`.

```sh
git -C <scratch>/cl --no-pager for-each-ref --format='%(refname)'
```

`[observed]`: only branches (as `refs/remotes/origin/*`) and tags; no `refs/stash`,
`refs/notes/*`, `refs/replace/*`, `refs/original/*`, `refs/bisect/*`, or the tool ref
`refs/codex/snapshot-1`.

```sh
git clone -q --mirror --no-local <audited-repo> <scratch>/mir.git
git -C <scratch>/mir.git --no-pager for-each-ref --format='%(refname)'
git -C <scratch>/mir.git rev-list --count --walk-reflogs refs/stash
```

`[observed]`: every ref was copied (`refs/stash`, `refs/notes/commits`,
`refs/replace/…`, `refs/original/…`, `refs/bisect/…`, `refs/codex/snapshot-1`,
remote-tracking refs), but the stash reflog was not: the walk counted `0`, so only the
newest stash is in the mirror.

## Footprint it leaves when interrupted or misused

- An interrupted clone leaves a partial directory; delete it and retry.
- `--reference` without `--dissociate` leaves `objects/info/alternates`: the clone breaks
  if the reference repository is pruned or deleted `[doc]`.
- `--filter` leaves a partial clone (promisor remote, `.promisor` packs) `[observed]`.

## Gotchas

- A plain or `--mirror` clone is **not** a full backup: reflogs (older stashes, reset
  history), the index, untracked and ignored files, `rr-cache`, hooks and config stay
  behind `[observed]` (stash reflog). For a byte-level backup copy the directory.
- Cloning a case-colliding tree on a case-insensitive filesystem warns "the following paths
  have collided" and checks out only one of each group `[observed]`.
- Git's SECURITY section: cloning untrusted content is generally safe; running Git inside
  an untrusted `.git` directory is not `[doc]`.
