# git lfs (third-party)

Official: https://git-lfs.com · Manual: https://github.com/git-lfs/git-lfs/tree/main/docs/man
· Areas: G4, G12, G14, G17 · Floor: latest release checked v3.8.0 (2026-09-22)

Detect and use only when installed (`command -v git-lfs`); never install it. Not installed on
the verification machine: every fact here is `[doc]`.

## Purpose in an audit

Tell whether Git LFS (large files stored outside Git, replaced by small pointer files) is in
use, which paths it tracks, whether pointers and local objects agree, and what hooks and
config it installed.

## Safety class

| Form | Class | Why |
| --- | --- | --- |
| `git lfs env` | read | Prints version, endpoints and config; redact URLs |
| `git lfs ls-files [--all] [--size] [--long]` | read | Lists LFS-tracked files |
| `git lfs track` (no argument) | read | Lists patterns from `.gitattributes` |
| `git lfs status` | read | Like `git status`, refreshes like it |
| `git lfs fsck --dry-run` | read | Checks objects and pointers without moving bad objects `[doc]` |
| `git lfs fsck` | mutates | Moves corrupt objects to `.git/lfs/bad` `[doc]` |
| `git lfs migrate info` | read | Size report of what could move to LFS |
| `git lfs fetch`, `pull`, `push` | network | Transfers objects |
| `git lfs install`, `uninstall`, `track <pattern>` | mutates | Hooks, config, `.gitattributes` |
| `git lfs migrate import` / `export` | mutates | Rewrites history |
| `git lfs prune` | mutates | Deletes local objects |

## Options that matter

- `ls-files --all` covers every ref; `--size` prints sizes `[doc]`.
- `migrate info --everything` scans commits reachable from every local and remote ref
  `[doc]`.
- `git lfs install` sets the `filter.lfs` clean and smudge filters (global config unless
  `--local` or `--worktree`) and installs a `pre-push` hook, in `core.hooksPath` when set
  `[doc]`. Hooks written by LFS call `git lfs`; recognize them by that text in `deep`.
- `fsck` without `--dry-run` moves corrupt files to `.git/lfs/bad` `[doc]`.

## Verified recipes

```sh
command -v git-lfs
git --no-pager config --show-scope --show-origin --get-regexp '^(filter\.lfs\.|lfs\.)' | cut -d' ' -f1
git --no-pager ls-files -z | git check-attr --stdin -z filter | tr '\0' '\n' | paste - - - \
  | awk -F'\t' '$3=="lfs"' | wc -l
git lfs env | sed -E 's#(://)[^/@[:space:]]+@#\1***@#g'
git lfs ls-files --all --size | head -n 50
```

The first three lines are plain Git and work without LFS `[observed]` (no LFS paths on the
fixture: count 0). The last two were not run (tool absent).

## Footprint it leaves when interrupted or misused

`.git/lfs/objects/` (content), `.git/lfs/tmp/`, `.git/lfs/bad/` (after `fsck`), the
`pre-push` hook, the `filter.lfs` config, and `.lfsconfig` in the tree. After a
sensitive-data rewrite, `orphaned_lfs_objects` lists server objects to purge
(`commands/git-filter-repo.md`).

## Gotchas

- `filter.lfs.*` is a command-executing filter (`git-lfs filter-process`): `git status` and
  `git add` run it.
- Pointer files committed without LFS installed look like tiny text files; content is
  missing locally.
- Hosting quotas and per-file limits for LFS are provider-specific; check the provider.
