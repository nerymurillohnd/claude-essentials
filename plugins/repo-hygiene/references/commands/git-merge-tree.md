# git merge-tree

Official: https://git-scm.com/docs/git-merge-tree · Areas: G5 · Floor: 2.38 for
`--write-tree` (`--merge-base` 2.40, `--stdin` 2.39)

## Purpose in an audit

Rung 4 of the integration ladder: compute the merge of a branch into the base without
touching the index, working tree or refs, and compare the result tree with the base tree.
Equal trees mean the branch adds nothing: `MERGED (content)`, a heuristic for squash and
rebase merges.

## Safety class

| Form | Class | Why |
| --- | --- | --- |
| `--write-tree <base> <branch>` | writes-local-state | writes tree (and merged blob) objects to the object store; no ref |
| `--write-tree --stdin` | writes-local-state | same, batched |
| `--trivial-merge <base> <b1> <b2>` (deprecated form) | read | prints a diff-like result, writes nothing |

Contract rule: it writes objects, so in `deep` it runs only after the unreachable census.

## Options that matter

- `--write-tree`: prints the result tree OID on the first line; with conflicts, the tree
  holds conflict markers and the exit status is 1.
- `--name-only`: conflicted paths only. `--messages` / `--no-messages`: informational
  messages ("Auto-merging", "CONFLICT (content)").
- `-z`: NUL-separated output for parsing.
- `--merge-base=<commit>`: use a given base instead of computing one (2.40).
- `-X<option>` / `--strategy-option`: merge-ort options; keep the defaults for a verdict.
- Exit status: 0 clean, 1 conflicts, other = error `[doc]`.

## Verified recipes

```sh
git --no-replace-objects merge-tree --write-tree origin/main feat/squashed
git rev-parse 'origin/main^{tree}'
git --no-replace-objects merge-tree --write-tree --name-only origin/main tmp/conf; echo "exit=$?"
```

`[observed]`: the squashed branch produced `434a172…`, equal to the base tree → `MERGED
(content)`. A conflicting branch printed a tree OID, `app.txt`, `CONFLICT (content): Merge
conflict in app.txt`, exit 1. A merge whose result was new raised the loose-object count
57 → 58 and added one unreachable tree; a merge whose result tree already existed (a branch
that only fast-forwards) wrote nothing.

## Footprint it leaves when interrupted or misused

Unreachable tree and blob objects, collected by `gc` after `gc.pruneExpire`. They inflate
an unreachable census taken afterwards, which is why the census runs first.

## Gotchas

- It is a heuristic: equal trees prove the content is present, not that it came from this
  branch (another commit may have made the same change). Say "MERGED (content)".
- Replace refs change the commits it reads; run `git --no-replace-objects merge-tree …`.
- Git < 2.38 has only the old trivial-merge mode; skip rung 4 and say so.
- Conflicting output (exit 1) is never `MERGED`, even if the conflict is trivial.
