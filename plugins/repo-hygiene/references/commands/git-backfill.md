# git backfill

Official: https://git-scm.com/docs/git-backfill · Areas: G1, G17 · Floor: 2.49

## Purpose in an audit

In a partial clone, some objects were never downloaded. Several area checks read blob contents
or sizes: the large-blob census, the secret search and stash comparison. Any of them can
silently fetch objects, or come back incomplete. `git backfill` downloads the missing blobs in
batches, so a full-depth audit can then read everything with `--no-lazy-fetch` and nothing
left missing. Running it is an approved item, never part of the audit itself.

## Safety class

| Form | Class | Why |
| --- | --- | --- |
| `git backfill` | network + mutates | Downloads missing blobs into the object store |
| `git backfill --sparse` | network + mutates | Only blobs inside the sparse-checkout definition |
| `git rev-list --objects --all --missing=print` (to count before and after) | read | Lists missing objects prefixed with `?` and fetches nothing |

## Options that matter

- `<revision-range>`: which history to fill. Without it, the command fills from `HEAD`
  (`[observed]`: 3 of 4 missing blobs were downloaded; the fourth was reachable only from
  another ref).
- `--min-batch-size=<n>`: the minimum number of objects per request.
- `--[no-]sparse`: limit the download to the current sparse-checkout.
- `--[no-]include-edges`: include the blobs of the boundary commits.

## Verified recipes

```sh
git config --get remote.origin.promisor                                  # "true" in a partial clone
git rev-list --objects --all --missing=print | grep -c '^?'              # missing objects, read-only
```

`[observed]` on Git 2.55, in a `--filter=blob:none` clone: 4 objects missing before
`git backfill` and 1 after.

## Footprint it leaves when interrupted or misused

New packs in `.git/objects/pack/`, and a larger repository on disk. An interrupted run leaves
the objects it already fetched. It cannot be undone except by re-cloning with the same filter.

## Gotchas

- It needs network access to the promisor remote, and the server must allow filters.
- It fills one history. To cover every ref, give it a range, or report the count of
  still-missing objects after it runs.
- The size of the download is unknown in advance. State that in the approval request.
