# git show-ref

Official: https://git-scm.com/docs/git-show-ref · Areas: G5, G7, G15 · Floor: any
(`--exists` 2.43, `--branches` 2.46)

## Purpose in an audit

Quick existence tests and plain `<oid> <ref>` listings. For inventories with types,
upstreams and dates use `commands/git-for-each-ref.md`.

## Safety class

| Form | Class | Why |
| --- | --- | --- |
| list, `--verify`, `--exists`, `-d`, `--hash` | read | reads refs |
| `--exclude-existing` | read | filters stdin |

## Options that matter

- `--exists <ref>`: exit 0 exists, 2 missing `[observed]` (2.43). It does not check that the
  ref resolves to an object `[doc]`.
- `--verify <ref>`: requires a full ref name; `-q` silences.
- `--branches` (2.46; formerly `--heads`, now deprecated) and `--tags`.
- `-d`/`--dereference`: also print `<ref>^{}` lines for annotated tags.
- `--head`: include HEAD.

## Verified recipes

```sh
git show-ref --exists refs/heads/main; echo "exit=$?"
git show-ref --exists refs/heads/nope; echo "exit=$?"
git --no-pager show-ref --verify refs/heads/main
git --no-pager show-ref -d --tags | head -n 10
```

`[observed]` exit 0; "error: reference does not exist", exit 2; `2794b6f… refs/heads/main`.

## Footprint it leaves when interrupted or misused

None.

## Gotchas

- Patterns match the tail of the ref name (`main` matches `refs/heads/main` and
  `refs/remotes/origin/main`).
- `--exists` is absent before 2.43: use `git rev-parse --verify -q --end-of-options
  'refs/heads/<b>'`.
- It lists only the current worktree's per-worktree refs.
