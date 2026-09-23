# git repack

Official: https://git-scm.com/docs/git-repack · Areas: G17 · Floor: any (`--cruft` 2.37;
`--geometric` first release not verified)

## Purpose in an audit

Understand the packs you see (cruft, kept, geometric, filtered) and know which repack
options delete data. It runs only as an approved item; `gc` and maintenance call it.

## Safety class

| Form | Class | Why |
| --- | --- | --- |
| `repack` (no `-d`) | writes-local-state | adds a pack of loose objects |
| `-a -d` | mutates | one pack of everything reachable; **unreachable objects in old packs are deleted immediately** |
| `-A -d` | mutates | as `-a -d`, but unreachable packed objects become loose (then pruned by normal expiry) |
| `--cruft -d` | mutates | unreachable objects go to a cruft pack; `--cruft-expiration` drops older ones |
| `-d` | mutates | removes redundant packs and runs `prune-packed` |
| `--geometric=<f> -d` | mutates | merges packs into a geometric progression |
| `--filter=<spec> --filter-to=<dir>` | mutates | moves objects to another store; without alternates the repo is corrupt `[doc]` |
| `-k`/`--keep-unreachable` | mutates | keeps unreachable objects in the new pack |

## Options that matter

- `-l`: pack only local objects (skip alternates). `-n`: skip `update-server-info`.
- `--keep-pack=<name>`, `--pack-kept-objects`: `.keep` handling.
- `-b`/`--write-bitmap-index`, `-m`/`--write-midx`.
- `--max-pack-size`, `--window`, `--depth`, `-f`/`-F` (recompute deltas).
- Promisor packs are repacked separately and keep their `.promisor` marker `[doc]`.

## Verified recipes

No read form exists. Inspect the result of past repacks through the pack directory:

```sh
ls -la <git-dir>/objects/pack
for i in <git-dir>/objects/pack/*.idx; do echo "$i $(git show-index < $i | wc -l)"; done
```

`[observed]` after `gc`: a 56-object pack plus a 7-object pack with `.mtimes` (the cruft
pack holding exactly the 7 unreachable objects of the census).

## Footprint it leaves when interrupted or misused

`tmp_pack_*`, `.tmp-*-pack-*` files; redundant packs if `-d` was not given; a MIDX that
references deleted packs if packs were removed by hand.

## Gotchas

- `git repack -a -d` without `-A` or `--cruft` destroys the unreachable objects that live in
  packs at once `[doc]`; never recommend it where recovery candidates exist.
- Repacking while another process writes has the same corruption risk as `gc`.
- `-l` in a repository with alternates leaves borrowed objects out on purpose.
