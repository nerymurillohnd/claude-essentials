# git fsck

Official: https://git-scm.com/docs/git-fsck · Areas: G15, G16, G17 · Floor: any

## Purpose in an audit

Integrity (corrupt or missing objects, broken refs) and the unreachable census: what exists
in the object store that no ref reaches, with and without reflogs as roots.

## Safety class

| Form | Class | Why |
| --- | --- | --- |
| `fsck [--unreachable] [--no-reflogs] [--dangling] [--full] [--strict] [--connectivity-only] [--name-objects]` | read | reads objects and refs |
| `--lost-found` | writes-local-state | writes `.git/lost-found/{commit,other}/` |
| `--progress` | read | stderr noise; use `--no-progress` |

## Options that matter

- Roots by default: the index, every ref, every reflog `[doc]`.
- `--unreachable`: every unreachable object; `--dangling` (default) only the tips.
- `--no-reflogs`: reflog-only commits count as unreachable ("used to be in a ref").
- `--full` (default): include packs and alternates. `--no-full` limits to loose objects.
- `--connectivity-only`: check that referenced objects exist, without reading blobs; blob
  corruption goes unseen `[doc]`.
- `--strict`: also flag g+w file modes from very old Git.
- `--name-objects`: show how a reachable object is reached (`HEAD@{…}~25^2:src/`).
- `--references` (default on in 2.55): run `git refs verify` on the ref database.
- `--cache`: treat index entries as roots. `--root`, `--tags`: report roots and tags.
- Config `fsck.<msg-id>` and `fsck.skipList` silence findings: read them first.

## Verified recipes

```sh
git --no-replace-objects fsck --unreachable --no-progress 2>/dev/null | awk '{print $2}' | sort | uniq -c
git --no-replace-objects fsck --unreachable --no-reflogs --no-progress 2>/dev/null | awk '{print $2}' | sort | uniq -c
git --no-replace-objects fsck --full --strict --no-progress 2>&1 | grep -v -E '^(dangling|unreachable) ' | head -n 100
git fsck --connectivity-only --no-dangling --no-progress
```

`[observed]` 2 blob / 1 commit / 4 tree with reflogs, 4 / 3 / 6 without; on a copy with one
loose blob deleted: `broken link from tree 9b92c13… to blob e77093f…` and `missing blob
e77093f…`.

## Footprint it leaves when interrupted or misused

`--lost-found` writes one file per dangling object. `[observed]` it wrote reflog-protected
stash entries too (it ignores reflogs as roots), `commit/<oid>` and tree entries in
`other/<oid>` contain only the OID and a newline (41 bytes), and only blobs get their
content. It is a mutation item, never an inspection.

## Gotchas

- `dangling`/`unreachable` is not "lost": `stash@{1}` and older are unreachable under
  `--no-reflogs` `[observed]`.
- Unreachable objects inside a cruft pack are still counted by fsck (and not by
  `count-objects`).
- On a huge repository `--full` reads every blob; start with `--connectivity-only`.
- The git-stash page's dropped-stash recipe filters with `--grep=WIP` and misses stashes
  made with `-m` `[observed]`; see `areas/refs-reflogs-recovery.md` step 15.
