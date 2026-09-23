# git multi-pack-index

Official: https://git-scm.com/docs/git-multi-pack-index · Areas: G17 · Floor: 2.20
(`verify` 2.22, bitmaps 2.34)

## Purpose in an audit

Verify the MIDX (one index over many packs) and, as an item, rebuild it. Maintenance's
`incremental-repack` task uses `expire` and `repack` from here.

## Safety class

| Form | Class | Why |
| --- | --- | --- |
| `verify` | read | checks the MIDX against the packs |
| `write [--bitmap] [--preferred-pack=…] [--stdin-packs] [--incremental]` | writes-local-state | rewrites derived files |
| `expire` | mutates | **deletes pack files** the MIDX references but no longer needs (keeps `.keep` and cruft packs) |
| `repack [--batch-size=<n>]` | writes-local-state | writes a new pack from small ones |

## Options that matter

- `--object-dir=<dir>`: operate on an alternate's object directory.
- `--[no-]progress`.
- `expire` is incompatible with incremental MIDX files `[doc]`.
- Config `core.multiPackIndex` (default true) makes Git read it.

## Verified recipes

```sh
git multi-pack-index verify --no-progress; echo "exit=$?"
ls -la <git-dir>/objects/pack/multi-pack-index* 2>/dev/null
```

`[observed]` exit 0 on a store without a MIDX and after `git multi-pack-index write
--bitmap` (which created `multi-pack-index` and `multi-pack-index-<hash>.bitmap`).

## Footprint it leaves when interrupted or misused

`multi-pack-index.lock`; a MIDX pointing at packs removed by hand makes reads fail until it
is rewritten.

## Gotchas

- Never delete packs by hand in a repository with a MIDX; `expire` exists for that.
- A missing MIDX is normal: it is optional.
- Repair: `git multi-pack-index write` (add `--bitmap` if a bitmap existed).
