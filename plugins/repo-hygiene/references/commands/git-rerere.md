# git rerere

Official: https://git-scm.com/docs/git-rerere · Areas: G2, G12 · Floor: any

## Purpose in an audit

"Reuse recorded resolution": when enabled, Git records how you resolved a conflict and
replays it the next time the same conflict appears. The audit inventories `rr-cache/`, says
whether it is enabled and from which config file, and warns when old recorded resolutions
could be replayed silently.

## Safety class

| Form | Class | Why |
| --- | --- | --- |
| `git rerere status` | read | Paths whose resolution will be recorded `[doc]`; exit 0 with none `[observed]` |
| `git rerere remaining` | read | Conflicted paths not auto-resolved `[doc]`; exit 0 `[observed]` |
| `git rerere diff` | executes an external program, prints contents | "Additional arguments are passed directly to the system diff command installed in PATH" `[doc]` |
| `git rerere` (no subcommand) | mutates | Records preimages/postimages |
| `git rerere forget <pathspec>` | mutates | Deletes recorded resolutions for current conflicts `[doc]` |
| `git rerere clear` | mutates | Resets metadata; run automatically by `am`/`rebase` `--skip`/`--abort` `[doc]` |
| `git rerere gc` | mutates | Prunes old records `[doc]` |

## Options that matter

- `rerere.enabled`: required for the feature `[doc]`; it can be set globally.
- `rerere.autoUpdate`: stage the replayed resolution automatically (`[doc]` `git-config`).
- `gc.rerereResolved` (default 60 days), `gc.rerereUnresolved` (default 15 days) `[doc]`.

## Verified recipes

```sh
git config --show-origin --get rerere.enabled
```

`[observed]`: `true`, coming from the user's global config, not the repository.

```sh
find "$(git rev-parse --git-path rr-cache)" -mindepth 1 -maxdepth 1 -type d | wc -l
find "$(git rev-parse --git-path rr-cache)" -name postimage | wc -l
```

`[observed]`: 1 record directory with a `preimage` and no `postimage` (unresolved).

```sh
git rerere status
git rerere remaining
```

`[observed]`: no output, exit 0, outside a conflict.

## Footprint it leaves when interrupted or misused

- `$GIT_COMMON_DIR/rr-cache/<conflict-id>/preimage` (contents with conflict markers) and
  `postimage` (the recorded resolution), plus a temporary `thisimage` (names from
  `rerere.c` in git/git; `preimage` `[observed]`). The directory is shared by all
  worktrees: `--git-path rr-cache` resolved to the common dir in a linked worktree
  `[observed]`.
- Preimages hold conflicted file contents: never `cat` them (contract section 4);
  fingerprint with `wc -c` and `git hash-object --stdin < <file>` (no `-w`).

## Gotchas

- A recorded resolution can be replayed into a new merge without review, especially with
  `rerere.autoUpdate=true`.
- The record ID is a hash of the conflict, not a commit; it does not resolve in the object
  store.
- `rr-cache` present with `rerere.enabled` unset means it was enabled once (or copied);
  report both facts.
