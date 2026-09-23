# git for-each-ref

Official: https://git-scm.com/docs/git-for-each-ref · Areas: G5, G7, G15 · Floor: any
(atoms have their own floors below)

## Purpose in an audit

The stable, parseable way to inventory refs: every namespace, object type, upstream state,
worktree, dates, ahead/behind. Every ref census in this corpus starts here.

## Safety class

| Form | Class | Why |
| --- | --- | --- |
| any `--format`, `--sort`, `--count`, pattern, `--merged`, `--contains`, `--points-at` | read | lists refs |
| `--include-root-refs` | read | adds `HEAD`, `ORIG_HEAD`, `BISECT_*` … |
| `--shell`/`--perl`/`--python`/`--tcl` | read | quoting only; output meant for `eval` — never eval it |

## Options that matter

Atoms (in `--format='…'`):

| Atom | Use |
| --- | --- |
| `%(refname)`, `%(refname:short)`, `%(refname:lstrip=2)` | name |
| `%(objecttype)`, `%(objectname)`, `%(objectname:short)` | what the ref points at (`commit`, `tag`, `tree`, `blob`) |
| `%(*objecttype)`, `%(*objectname)` | peeled target of an annotated tag |
| `%(upstream)`, `%(upstream:short)`, `%(upstream:remotename)`, `%(upstream:track)`, `%(upstream:track,nobracket)` | tracking; `[gone]` when the tracking ref is missing |
| `%(push:short)`, `%(push:track)` | where `git push` would go |
| `%(ahead-behind:<ref>)` | "ahead behind" counts vs `<ref>` (Git ≥ 2.41) |
| `%(worktreepath)` | worktree holding the branch; empty otherwise |
| `%(HEAD)` | `*` for the current branch |
| `%(committerdate:iso-strict)`, `%(creatordate)`, `%(taggerdate:short)` | age |
| `%(contents:signature)`, `%(contents:subject)` | tag signature block / subject |
| `%(if)…%(then)…%(else)…%(end)` | conditionals |
| `%(is-base:<ref>)` | heuristic "branch this was started from" (Git ≥ 2.47) |

Filters: `--merged`, `--no-merged`, `--contains`, `--no-contains`, `--points-at`,
`--exclude=<pattern>`, `--omit-empty` (2.41), `--count=<n>`, `--sort=<key>`
(repeatable; last is primary).

## Verified recipes

```sh
git --no-optional-locks --no-pager for-each-ref \
  --format='%(refname:short)|%(objectname:short)|%(upstream:short)|%(upstream:track)|%(committerdate:iso-strict)|%(worktreepath)' \
  refs/heads
git --no-replace-objects --no-pager for-each-ref --format='%(refname:short) %(ahead-behind:origin/main)' refs/heads
git --no-pager for-each-ref --format='%(refname)' | awk -F/ '{print $1"/"$2}' | sort | uniq -c
git --no-pager for-each-ref --format='%(objecttype) %(refname)' | awk '$1!="commit"'
git --no-pager for-each-ref --include-root-refs --format='%(refname)' | grep -v '^refs/'
```

`[observed]`: `feat/merged|…|origin/feat/merged|[gone]|…`; `tree refs/codex/snapshot-1`;
root refs `BISECT_EXPECTED_REV HEAD ORIG_HEAD` (no `FETCH_HEAD`).

## Footprint it leaves when interrupted or misused

None: it never writes.

## Gotchas

- `--no-replace-objects` is a global option: `git --no-replace-objects for-each-ref …`.
  After the subcommand it fails with `unknown option` `[observed]`.
- `%(ahead-behind:)` honors replace refs: `main` showed 4 ahead with a replace ref, 5
  without `[observed]`.
- `%(upstream)` is empty (not `[gone]`) when `branch.<b>.remote` names a missing remote
  `[observed]`; read `branch.*` config for that case.
- `%(worktreepath)` fills for the main worktree too `[observed]` (the page says "linked
  worktree"), and is empty for a branch whose worktree is on a detached HEAD because of a
  bisect or rebase.
- It lists only the current worktree's per-worktree refs: a linked worktree's
  `refs/bisect/*` is invisible from the main one `[observed]`.
- The `--shell` family exists for `eval`; never eval ref names from an untrusted
  repository.
