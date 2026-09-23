# git commit-graph

Official: https://git-scm.com/docs/git-commit-graph · Areas: G17 · Floor: 2.18

## Purpose in an audit

Verify the commit-graph cache that speeds history walks, and rebuild it when it is
corrupt. It is derived data: rebuilding loses nothing.

## Safety class

| Form | Class | Why |
| --- | --- | --- |
| `verify [--shallow]` | read | checks the graph against the object store |
| `write [--reachable \| --stdin-packs \| --stdin-commits] [--split[=…]] [--changed-paths]` | writes-local-state | writes `objects/info/commit-graph` or `commit-graphs/` |

## Options that matter

- `--shallow`: verify only the tip file of a split chain `[doc]`.
- `--split=no-merge|replace`: `replace` overwrites the whole chain with a new one.
- `--changed-paths`: Bloom filters for path-limited log.
- Config: `core.commitGraph` (read it or not), `gc.writeCommitGraph`,
  `fetch.writeCommitGraph`.

## Verified recipes

```sh
git commit-graph verify --no-progress; echo "exit=$?"
git -c core.commitGraph=false --no-pager log --oneline -1
```

`[observed]` exit 0 on a healthy split chain; after 4 bytes were overwritten at offset 200
of the graph file: "commit-graph fanout values out of order", "required OID fanout chunk
missing or corrupted", exit 1; the second command still worked. Repair item, literal:

```sh
git commit-graph write --reachable --split=replace
```

`[observed]` it warned about the old file while reading it, exited 0, and `verify` then
passed.

## Footprint it leaves when interrupted or misused

`commit-graph.lock` or a `commit-graph-chain` that names a missing `graph-*.graph` ("unable
to find all commit-graph files").

## Gotchas

- A corrupt graph can make `log`/`merge-base` fail or give wrong answers; confirm a
  suspicious ancestry result with `git -c core.commitGraph=false …`.
- Verification cost grows with history; `--shallow` for a quick check of a split chain.
- `[doc]` CAVEATS: "The existence of replace objects or commit grafts turns off reading or
  writing to the commit-graph." A repository with a replace ref gets no graph speed-up;
  counts still need `--no-replace-objects`.
