# git filter-branch

Official: https://git-scm.com/docs/git-filter-branch · Areas: G14, G15 · Floor: any

## Purpose in an audit

Recognize its leftovers and never recommend it. Its own manual opens with a WARNING that
it has many pitfalls and recommends `git filter-repo` instead `[doc]`.

## Safety class

| Form | Class | Why |
| --- | --- | --- |
| any run | mutates + executes-config | Rewrites every selected ref and runs the filter scripts given on the command line |
| `for-each-ref refs/original` (reading its leftovers) | read | Lists the backup refs |

## Options that matter (to read its footprint)

- `refs/original/` holds the pre-rewrite refs (`--original <namespace>` changes it); a second
  run refuses while it exists unless `-f`/`--force` `[doc]`.
- `-d <directory>` temporary tree, default `.git-rewrite/` `[doc]`.
- `--state-branch <branch>` stores mapping state in a branch for incremental runs `[doc]`.
- `--tag-name-filter cat` is required to rewrite tags; annotated tags lose signatures.
- `FILTER_BRANCH_SQUELCH_WARNING=1` silences the warning; seeing it in scripts is a finding.

## Verified recipes

```sh
git --no-pager for-each-ref --format='%(refname) %(objectname:short)' 'refs/original' | head -n 50
ls -d "$(git rev-parse --git-dir)/../.git-rewrite" .git-rewrite 2>/dev/null
git --no-pager grep -n -I -E 'filter-branch|FILTER_BRANCH_SQUELCH_WARNING' | head -n 20
```

`[observed]` on the fixture: `refs/original/refs/heads/main` pointed at an old commit and
kept it reachable.

## Footprint it leaves when interrupted or misused

- `refs/original/*`: backups that keep the old history (and any secret it held) alive and
  reachable until deleted.
- `.git-rewrite/` after an interrupted run.
- Rewritten tags without `--tag-name-filter cat` still point at old commits.

## Gotchas

- The backup in `refs/original/` is not a full backup (only refs, not other clones) `[doc]`.
- Removing `refs/original` is an approved item after the ref snapshot and, for secrets, after
  rotation; see `areas/refs-reflogs-recovery.md` and `areas/history-and-secrets.md`.
