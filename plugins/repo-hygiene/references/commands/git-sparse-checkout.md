# git sparse-checkout

Official: https://git-scm.com/docs/git-sparse-checkout · Areas: G1, G3 · Floor: any
(`clean` 2.52)

## Purpose in an audit

Tells whether only part of the tree is checked out and which part, so that "file missing
on disk" and `S` (skip-worktree) entries are read correctly.

## Safety class

| Form | Class | Why |
| --- | --- | --- |
| `list` | read | Prints the cone directories or patterns `[doc]` |
| `check-rules [--rules-file <file>]` | read | Filters paths from stdin against the rules `[doc]` |
| `clean --dry-run` | read | "list the directories that would be removed without deleting them" `[doc]` |
| `clean -f` | mutates | Deletes files outside the definition `[doc]` |
| `set`, `add`, `reapply`, `init`, `disable` | mutates | Change config (`core.sparseCheckout`, `core.sparseCheckoutCone`, `index.sparse`, `extensions.worktreeConfig`), the sparse-checkout file and the working tree `[doc]` |

## Options that matter

- Cone mode (default): directories; non-cone (`--no-cone`): patterns, not recommended
  `[doc]`.
- `--sparse-index` / `--no-sparse-index`: a smaller index that older Git and external
  tools may not understand `[doc]`.
- `set` upgrades the repository to worktree-specific config `[doc]`.
- `clean --verbose` lists every file in directories considered for removal `[doc]`.
- The rules file is `$GIT_DIR/info/sparse-checkout` (per worktree) `[observed]`.

## Verified recipes

```sh
git config --get core.sparseCheckout
```

`[observed]`: `true` in a sparse clone; exit 1 with no output in a normal repository. Use
this as the probe.

```sh
git sparse-checkout list
```

`[observed]`: `sub` in cone mode; in a non-sparse repository it prints
`fatal: this worktree is not sparse` and exits 128.

```sh
git --no-pager config --show-scope --get-regexp 'sparse'
```

`[observed]`: `worktree core.sparsecheckout true`, `worktree core.sparsecheckoutcone true`.

```sh
git ls-tree -r --name-only origin/topic | git sparse-checkout check-rules
git sparse-checkout clean --dry-run
```

`[observed]`: `check-rules` echoed `f` and `g` (top-level files are always in the cone);
`clean --dry-run` printed nothing, exit 0.

```sh
cat "$(git rev-parse --git-path info/sparse-checkout)"
```

`[observed]`: `/*`, `!/*/`, `/sub/` (the cone patterns).

## Footprint it leaves when interrupted or misused

- `extensions.worktreeConfig=true` and `config.worktree` files `[observed]`.
- Files materialized by a merge or rebase outside the cone stay until `reapply` `[doc]`.
- `init` (deprecated) followed by `set` could lose files in older versions `[doc]`.

## Gotchas

- Do not probe with `list`: exit 128 is normal when sparse checkout is off `[observed]`.
- In a sparse checkout, skip-worktree bits are expected and Git clears the bit when a file
  shows up on disk `[doc]` (`git-update-index`).
- The manual warns the command's behavior in the presence of sparse checkouts "will likely
  change in the future" `[doc]`: re-check the live page for version-specific behavior.
