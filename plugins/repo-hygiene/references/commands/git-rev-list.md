# git rev-list

Official: https://git-scm.com/docs/git-rev-list · Areas: G5, G14, G15, G16, G17 · Floor:
any (`--disk-usage` 2.31, `--no-commit-header` 2.33)

## Purpose in an audit

The plumbing walker behind every count: ahead/behind, commits only in reflogs, objects
reachable from a set of refs, disk use of history, missing objects.

## Safety class

| Form | Class | Why |
| --- | --- | --- |
| every walk and count | read | walks the graph |
| `--objects` over a partial clone | possibly network | lazy fetch of promisor objects is not verified here; pass `--missing=print` or `--missing=allow-promisor` to keep the walk offline-safe |

## Options that matter

- Global `git --no-replace-objects rev-list …`: mandatory for counts `[observed]`.
- `--count`, `--left-right --count A...B` (prints "left right").
- `--all` (every ref in `refs/` plus HEAD), `--branches`, `--tags`, `--remotes`,
  `--reflog` (every reflog entry as a tip), `--indexed-objects`, `--not`, `--no-walk`.
- `--objects`: list every reachable object with a path; `--objects-edge`, `--filter=…`.
- `--missing=print`: list missing objects with a `?` prefix instead of dying.
- `--disk-usage[=human]` with `--objects`: on-disk bytes of what the walk reaches (2.31).
- `--format='%T %H'` with `--no-commit-header` (2.33): one line per commit, for tree
  matching.
- `--first-parent`, `--ancestry-path`, `--since`, `--until`, `--max-count`.

## Verified recipes

```sh
git --no-replace-objects rev-list --left-right --count origin/main...main
git --no-replace-objects rev-list --count --reflog --not --all
git --no-replace-objects --no-pager rev-list --all --no-commit-header --format='%T %H' \
  | grep '^434a172c9cc4579644dbbe30601aa54848516c92 ' | head -n 3
git --no-replace-objects rev-list --disk-usage=human --objects --all
git --no-replace-objects rev-list --objects --missing=print --all | grep '^?' | head -n 20
```

`[observed]`: `0 5` (and `0 4` without `--no-replace-objects`); 2 reflog-only commits;
three commits sharing the tree of the tool ref; `2.02 MiB`; `?e77093f…` for a deleted
blob.

## Footprint it leaves when interrupted or misused

None in a normal repository. In a partial clone, treat an `--objects` walk without
`--missing=…` as possibly fetching (not verified).

## Gotchas

- `git rev-list --no-replace-objects --count main` is rejected (it prints the usage text):
  the option is global `[observed]`.
- `--all` includes `refs/stash` (top only), `refs/notes`, `refs/original`, `refs/replace`
  and tool refs: history "reachable from --all" is wider than "on a branch".
- `--missing=` is documented as a debug option for partial clone development `[doc]`; its
  `print` form is still the simplest missing-object listing.
- `--missing=print` output is `?<oid>`, no space.
