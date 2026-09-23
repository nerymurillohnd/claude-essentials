# git show

Official: https://git-scm.com/docs/git-show · Areas: G14, G16, G21 · Floor: any

## Purpose in an audit

Inspect one object: a commit's metadata and changed paths, a tag, a tree listing, or a
non-secret blob. Most audit uses need only metadata and paths.

## Safety class

| Form | Class | Why |
| --- | --- | --- |
| `git show --no-patch --format=… <commit>` | read | Metadata only |
| `git show --name-only` / `--name-status` / `--stat` `<commit>` | read | Paths, no conversion `[observed]` |
| `git show <commit>` (patch) | executes-config | Runs `diff.<driver>.textconv` `[observed]` |
| `git show --no-textconv <commit>` | read | Driver not run `[observed]` |
| `git show <commit>:<path>` (blob) | read | Raw content, no textconv `[observed]`; **forbidden for secret-shaped paths and unknown payloads** |
| `git show --textconv <commit>:<path>` | executes-config | Runs the driver on the blob `[observed]` |
| `--show-signature` | read + executes-config | Runs the signing program |

## Options that matter

- `--no-patch` (`-s`), `--format=<fmt>`, `--name-only`, `--name-status`, `--stat`.
- `--no-textconv`, `--no-ext-diff`.
- `<tree>` shows a listing like `ls-tree`; `<tag>` shows the tag message and target.
- `--first-parent` / `-m` / `--diff-merges=` control merge diffs.

## Verified recipes

```sh
git --no-replace-objects --no-pager show --no-patch --format='%H %an %ad %s' <commit>
git --no-replace-objects --no-pager show --no-textconv --name-status --format='%h %s' <commit>
```

`[observed]` on a repository with a textconv driver: `show <commit>` ran it;
`show --no-textconv <commit>`, `--stat`, `--name-only` and `show <commit>:<path>` did not.

## Footprint it leaves when interrupted or misused

None; a pager runs without `--no-pager`.

## Gotchas

- Printing a blob that holds a secret puts it into the transcript: fingerprint instead
  (`git cat-file -s`, `git cat-file -t`, or `git hash-object --stdin --no-filters` on a
  file) per `audit-contract.md` section 4.
- `--no-replace-objects` is a global option: `git --no-replace-objects show …`.
