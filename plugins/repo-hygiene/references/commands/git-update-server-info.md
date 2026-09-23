# git update-server-info

Official: https://git-scm.com/docs/git-update-server-info · Areas: G18 · Floor: any

## Purpose in an audit

Understand the dumb-HTTP catalog files it writes (`info/refs`, `objects/info/packs`), decide
whether they are stale, and know that `gc` and `repack` write them too.

## Safety class

| Form | Class | Why |
| --- | --- | --- |
| `git update-server-info [-f \| --force]` | mutates | Rewrites `info/refs` and `objects/info/packs` |
| reading those two files | read | Plain text: object IDs and ref names |

## Options that matter

- `-f` / `--force`: rebuild from scratch `[doc]`.
- Also run by `git repack` unless `-n`, by the `post-update` sample hook, and on receive when
  `receive.updateServerInfo` is true `[doc]`.

## Verified recipes

```sh
wc -l "$(git rev-parse --git-common-dir)/info/refs" "$(git rev-parse --git-common-dir)/objects/info/packs"
git --no-pager for-each-ref --format='%(objectname)%09%(refname)' | sort > <evidence>/refs-now.txt
grep -v '\^{}' "$(git rev-parse --git-common-dir)/info/refs" | sort | diff - <evidence>/refs-now.txt | head -n 40
```

`[observed]`: after `update-server-info`, `info/refs` listed every ref, including
`refs/bisect/*`, `refs/codex/snapshot-1`, `refs/original/*` and `refs/notes/commits`; a
branch created afterwards appeared only in the live list. `git gc` and `git repack -a -d`
both created `info/refs` and `objects/info/packs` in a repository that never ran this command.

## Footprint it leaves when interrupted or misused

The two catalog files; once written they stay and drift from the real refs.

## Gotchas

- Presence of the files is not evidence of dumb-HTTP serving (see above) `[observed]`.
- On a served repository the stale catalog exposes hidden refs or misses new ones; on an
  unserved one it only reveals ref names to anyone who can read the folder.
