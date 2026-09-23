# git pack-refs

Official: https://git-scm.com/docs/git-pack-refs · Areas: G15, G17 · Floor: any
(`--auto` 2.45)

## Purpose in an audit

Explain `packed-refs` (loose vs packed refs are storage, not extra branches) and, rarely,
pack refs as an item. `gc` and the `pack-refs` maintenance task run it.

## Safety class

| Form | Class | Why |
| --- | --- | --- |
| `pack-refs [--all] [--auto] [--include/--exclude <pattern>]` | writes-local-state | moves loose ref files into `packed-refs` (or compacts reftable tables) |
| `pack-refs --no-prune` | writes-local-state | packs without deleting the loose files |

## Options that matter

- Default: pack tags and already-packed refs; `--all` also branches (not hidden, broken or
  symbolic refs) `[doc]`.
- `--auto`: pack only when the ratio of loose refs warrants it; for reftable, geometric
  compaction `[doc]`.
- `--include`, `--exclude`: glob filters; exclude wins.

## Verified recipes

Reads that explain the storage:

```sh
git rev-parse --show-ref-format
grep -c -v '^[#^]' <git-dir>/packed-refs
find <git-dir>/refs -type f | wc -l
```

`[observed]` fixture: `files`, 16 packed refs, 6 loose files. In `packed-refs`, a line
starting with `^` is the peeled commit of the annotated tag on the line above `[doc]` Pro Git
10.7.

## Footprint it leaves when interrupted or misused

`packed-refs.lock`; loose files left beside their packed copy (`--no-prune`), which is
harmless (the loose file wins).

## Gotchas

- A ref may be both loose and packed; the loose value is authoritative.
- Deleting a packed ref rewrites `packed-refs`; a stale `packed-refs.lock` blocks every ref
  deletion.
- Never edit `packed-refs` by hand; use `git update-ref`.
- With the reftable backend there is no `packed-refs` file; use `for-each-ref`.
