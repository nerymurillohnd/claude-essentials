# git bundle

Official: https://git-scm.com/docs/git-bundle · Areas: G16, G17 · Floor: any

## Purpose in an audit

The backup item before any destructive deep step: one file, outside the repository, with
every ref and the objects they reach, and a restore test that proves it.

## Safety class

| Form | Class | Why |
| --- | --- | --- |
| `bundle create <file> <rev-list-args>` | writes-local-state | writes `<file>` (outside the repo); reads the store |
| `bundle verify <file>` | read | checks the bundle against the current repository |
| `bundle list-heads <file>` | read | lists the refs it carries |
| `bundle unbundle <file>` | writes-local-state | writes a pack into the current repository |
| `fetch <file> 'refs/*:refs/*'` into a scratch repo | mutates (scratch only) | restore test |

## Options that matter

- `--all`: every ref under `refs/` plus HEAD; `--branches`, `--tags`, ranges.
- `--version=2|3`: v3 is needed for SHA-256 repositories.
- `-q`/`--progress`.

## Verified recipes

```sh
git bundle create <outside>/repo.bundle --all
git bundle verify <outside>/repo.bundle
git bundle list-heads <outside>/repo.bundle | awk '{print $2}' | sort | head -n 100
git init --bare <outside>/restore-test
git -C <outside>/restore-test fetch <outside>/repo.bundle 'refs/*:refs/*'
git -C <outside>/restore-test for-each-ref --format='%(refname) %(objectname)' | sort
```

`[observed]`: "The bundle records a complete history", hash algorithm sha1; the heads
included `HEAD`, `refs/bisect/*`, the tree ref `refs/codex/snapshot-1`, `refs/stash`,
`refs/replace/*`, `refs/original/*` and `worktrees/<id>/HEAD`. After the restore, 22 refs
existed; the top stash commit was present, but `stash@{1}`, the reset-away commit and the
dropped stash were absent, and there were no reflogs. `git bundle unbundle` into an empty
bare repository wrote the objects and printed the ref list, but created no refs (0 from
`for-each-ref`); use the `fetch` form for a ref-by-ref comparison.

## Footprint it leaves when interrupted or misused

A partial bundle file; a bundle saved inside the working tree becomes an untracked (maybe
committed) multi-megabyte file. Always write outside the repository.

## Gotchas

- **Limit:** only objects reachable from the bundled refs. Reflog-only commits, older stash
  entries and unreachable objects are not in it `[observed]`; pin them under
  `refs/recovered/` first.
- `worktrees/<id>/HEAD` entries are listed but not fetched by `refs/*:refs/*`.
- A bundle contains every secret in history; store it with mode 600 in a mode-700
  directory, and say where in the report.
- Compare ref lists byte for byte between the original (`for-each-ref`) and the restore; a
  checksum of the file alone is not a restore test.
