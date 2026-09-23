# git patch-id

Official: https://git-scm.com/docs/git-patch-id · Areas: G5, G16 (D14 X3) · Floor: any
(`--verbatim` is recent; its first release was not verified)

## Purpose in an audit

Fingerprint a change independently of its commit (author, date, parent). D14 uses it to
decide whether an unreachable or unmerged commit's patch already exists in reachable
history.

## Safety class

| Form | Class | Why |
| --- | --- | --- |
| `git patch-id [--stable \| --unstable \| --verbatim] < patch` | read | hashes stdin |

## Options that matter

- `--stable`: the ID does not depend on file order in the diff; use it always, so IDs from
  different producers compare.
- `--unstable`: legacy, order-sensitive (default unless `patchid.stable` is set).
- `--verbatim`: do not strip whitespace; stricter.
- Output: `<patch-id> <commit-id>` per commit in the input.

## Verified recipes

```sh
git --no-replace-objects --no-pager diff-tree -p ffde723 | git patch-id --stable
git --no-replace-objects --no-pager log -p --no-color --no-textconv --no-ext-diff feat/squashed ^origin/main | git patch-id --stable
```

`[observed]` the squash commit `ffde723` has patch-id `d64e4be…`; the branch's two commits
have `f5d5d32…` and `f0e26ea…`: no match, although the combined change is identical.
Compare a candidate against reachable history in the same date window:

```sh
git --no-replace-objects --no-pager log -p --no-color --no-textconv --no-ext-diff --since=2026-09-01 --until=2026-09-30 main \
  | git patch-id --stable | sort > <evidence>/patch-ids-main.txt
```

## Footprint it leaves when interrupted or misused

None.

## Gotchas

- Feed it `--no-color` output; color codes change the hash. Never pass `--ext-diff` or
  `--textconv` (they run configured programs and change the patch).
- Merges produce no patch-id with plain `log -p`.
- A squash of several commits has a different ID than each part `[observed]`; compare the
  tree (`^{tree}`) or use `merge-tree` for squashes.
- It reads patch lines: never print them; pipe straight into `git patch-id`.
