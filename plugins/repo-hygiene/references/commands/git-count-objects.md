# git count-objects

Official: https://git-scm.com/docs/git-count-objects · Areas: G17 · Floor: any

## Purpose in an audit

The first, cheap look at the object store: loose count and size, packs, garbage files,
alternates.

## Safety class

| Form | Class | Why |
| --- | --- | --- |
| `count-objects [-v] [-H]` | read | stats the object directory |

## Options that matter

- `-v`: `count`, `size`, `in-pack`, `packs`, `size-pack`, `prune-packable`, `garbage`,
  `size-garbage`, `alternate` (one line per alternate) `[doc]`.
- `-H`: human-readable sizes (otherwise KiB).
- Warnings on stderr name each garbage file (`garbage found: …`, `no corresponding .idx:
  …`).

## Verified recipes

```sh
git --no-optional-locks count-objects -v -H
```

`[observed]` fresh fixture: `count: 63`, `packs: 0`, `garbage: 0`. After `gc` and seeded
defects: `count: 0`, `in-pack: 63`, `packs: 2`, `garbage: 3` (a `tmp_pack_*`, a `.pack`
without `.idx`, its `.keep`), with one stderr warning per file.

## Footprint it leaves when interrupted or misused

None.

## Gotchas

- `count: 0` and `garbage: 0` do not mean nothing is unreachable: since Git 2.41 `gc`
  stores unreachable objects in a **cruft pack** (`*.mtimes`) `[observed]`.
- Stray files at the top of `objects/` or in non-hex subdirectories are not counted as
  garbage `[observed]`; list the directory too.
- `prune-packable` > 0 means loose duplicates of packed objects (`git prune-packed` or the
  maintenance `loose-objects` task removes them).
- `size-pack` includes cruft and `.keep` packs.
