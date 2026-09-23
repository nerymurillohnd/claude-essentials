# git cherry

Official: https://git-scm.com/docs/git-cherry · Areas: G5, G16 · Floor: any

## Purpose in an audit

Rung 5 of the integration ladder (corroboration only): for each commit of a branch not in
the upstream, tell whether an equivalent patch (same `git patch-id`) already exists
upstream.

## Safety class

| Form | Class | Why |
| --- | --- | --- |
| `git cherry [-v] <upstream> [<head> [<limit>]]` | read | compares patch-ids |

## Options that matter

- `<upstream>`: the base (defaults to the branch's upstream). `<head>`: defaults to HEAD.
- `<limit>`: ignore commits up to and including `<limit>` (restrict to a range).
- `-v`: add the subject.
- Output: `-` = an equivalent patch is upstream; `+` = no equivalent single patch.

## Verified recipes

```sh
git --no-replace-objects --no-pager cherry -v origin/main feat/squashed
git --no-replace-objects --no-pager cherry origin/main feat/squashed | cut -c1 | sort | uniq -c
```

`[observed]` `+ 52612d7 s1`, `+ 65bacac s2` for a branch whose two commits were squashed
into one upstream commit; `+ f35123d unique` for a truly unique commit. Both look the same.

## Footprint it leaves when interrupted or misused

None.

## Gotchas

- A squash of N > 1 commits never matches any single commit, so `+` appears although the
  content landed `[observed]`. Only an all-`-` result corroborates; `+` proves nothing.
- A patch amended during review (conflict resolution, typo) changes its patch-id.
- Merge commits are ignored (patch-id is empty for merges).
- Honors replace refs; run it as `git --no-replace-objects cherry …`.
