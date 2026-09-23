# git describe

Official: https://git-scm.com/docs/git-describe · Areas: G7, G21 · Floor: any

## Purpose in an audit

Name a commit relative to the nearest tag (`v0.1-1-gfaafec8`): which release a stray or
unreachable commit came after, and whether HEAD is exactly on a release tag.

## Safety class

| Form | Class | Why |
| --- | --- | --- |
| `describe [--tags] [--all] [--always] [--contains] <commit>` | read | walks history |
| `describe --dirty` | writes-local-state | refreshes and rewrites the index, even under `--no-optional-locks` `[observed]` |
| `describe --broken` | writes-local-state (assumed) | same dirty check; not tested |
| `describe <blob>` | read | searches history for the blob (slow) |

## Options that matter

- `--tags`: also use lightweight tags; `--all`: any ref (`heads/…`, `tags/…`).
- `--always`: fall back to an abbreviated OID. `--exact-match`: fail unless on a tag.
- `--contains`: describe by the first tag that contains the commit (uses `name-rev`).
- `--match`/`--exclude <glob>`, `--abbrev=<n>`, `--first-parent`, `--long`.

## Verified recipes

```sh
git --no-replace-objects describe --tags --always aa2face
git --no-replace-objects describe --all faafec8
```

`[observed]` `v0.2`; `tags/v0.1-1-gfaafec8` for the reset-away commit (one commit after
`v0.1`).

## Footprint it leaves when interrupted or misused

`--dirty` updates `.git/index` `[observed]`: the index mtime changed with and
without `--no-optional-locks`, while `git --no-optional-locks status --porcelain` left it
untouched.

## Gotchas

- Never use `--dirty` in an audit; check cleanliness with `git --no-optional-locks status
  --porcelain`.
- `--dirty` does not see changes hidden by `--assume-unchanged` (G3) `[observed]`: the
  fixture's hidden edit was not reported.
- Replace refs change the walk; use `git --no-replace-objects describe`.
