# git verify-pack

Official: https://git-scm.com/docs/git-verify-pack · Areas: G14, G17 · Floor: any

## Purpose in an audit

Validate a pack against its index, and list every object in it with type and size (the
Pro Git way to find the largest blobs).

## Safety class

| Form | Class | Why |
| --- | --- | --- |
| `verify-pack [-v] [-s] <pack>.idx` | read | reads pack and index |

## Options that matter

- `-v`: one line per object: `<oid> <type> <size> <size-in-pack> <offset> [<depth>
  <base-oid>]`, then a delta-chain histogram and `<pack>: ok`.
- `-s` / `--stat-only`: only the histogram.
- `--object-format=<sha1|sha256>` when run outside a repository.

## Verified recipes

```sh
git verify-pack <git-dir>/objects/pack/pack-<id>.idx; echo "exit=$?"
git verify-pack -v <git-dir>/objects/pack/pack-<id>.idx | tail -n 4
git verify-pack -v <git-dir>/objects/pack/pack-<id>.idx \
  | grep -E '^[0-9a-f]{40,64} (blob|tree|commit|tag)' | sort -k 3 -n -r | head -n 10
```

`[observed]` exit 0; tail `non delta: 39 objects`, `chain length = 1: 13 objects`, …,
`pack-f743….pack: ok`; the largest objects were two blobs of 3 072 000 and 2 097 152 bytes.
Map a blob to its path with `git --no-replace-objects rev-list --objects --all | grep
<oid-prefix>` (G14).

## Footprint it leaves when interrupted or misused

None.

## Gotchas

- Point it at the `.idx`. A `.pack` without an `.idx` cannot be verified in place: copy it
  outside the repository and run `git index-pack <outside>/pack-<id>.pack` on the copy (an
  item, since it writes an `.idx` next to the copy).
- It is per pack; a repository with many packs needs one call each (bound the loop).
- Cruft packs verify like normal packs; their objects are unreachable by definition.
