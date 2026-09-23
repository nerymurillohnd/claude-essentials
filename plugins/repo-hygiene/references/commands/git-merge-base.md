# git merge-base

Official: https://git-scm.com/docs/git-merge-base · Areas: G5, G7, G15 · Floor: any
(`--is-ancestor` 1.8.0, `--fork-point` 1.9)

## Purpose in an audit

Rung 2 of the integration ladder (`--is-ancestor`), the base for ahead/behind reasoning,
and the check that a backup ref (`refs/original/*`, a moved tag) is or is not contained in
current history.

## Safety class

| Form | Class | Why |
| --- | --- | --- |
| every form | read | computes from the commit graph |

## Options that matter

- `--is-ancestor <A> <B>`: exit 0 if A is an ancestor of B (or equal), 1 if not, 128 on
  error (for example an unknown name) `[doc]` (tests added in 2.56 RelNotes). Prints
  nothing; read `$?`.
- `-a`/`--all`: every best common ancestor (criss-cross merges have more than one).
- `--octopus`: base for more than two commits.
- `--independent`: the minimal subset of the given commits none of which is reachable from
  another (find the real tips of a set).
- `--fork-point <ref> [<commit>]`: uses the **reflog** of `<ref>` to find where
  `<commit>` forked, even after `<ref>` was rewritten. No reflog history → no answer.

## Verified recipes

```sh
git --no-replace-objects merge-base --is-ancestor feat/merged origin/main; echo "exit=$?"
git --no-replace-objects merge-base --is-ancestor refs/original/refs/heads/main main; echo "exit=$?"
git --no-replace-objects merge-base --all main wip/unique
```

`[observed]` 0 for the `--no-ff` merged branch, 1 for the squashed branch, 0 for the
`refs/original` backup; `--all` printed `ffde723…`.

## Footprint it leaves when interrupted or misused

None.

## Gotchas

- Replace refs change the graph it walks; run it as `git --no-replace-objects
  merge-base …`.
- A stale remote-tracking base gives a wrong verdict; pin the base against `git ls-remote`
  first (`areas/branches-remotes-tags.md`, ladder rung 1).
- Exit 1 is "not an ancestor", not "unmerged content": squash and rebase merges fail this
  test.
- `[observed]` `--fork-point origin/main feat/squashed` printed nothing and exited 1: the
  tracking ref's reflog held a single entry, so there was nothing to search.
