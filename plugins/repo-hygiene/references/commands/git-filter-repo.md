# git filter-repo (third-party)

Official: https://github.com/newren/git-filter-repo · Areas: G14, G18 · Floor: git-filter-repo
2.47 for `--sensitive-data-removal`; filter-repo needs Git ≥ 2.36.0 and Python ≥ 3.6 `[doc]`
README. Latest release checked: v2.47.0 (2026-09-22).

Detect and use only when installed (`command -v git-filter-repo`); never install it. Not
installed on the verification machine: every fact here is `[doc]`.

## Purpose in an audit

Analyze history size (`--analyze`), recognize a past rewrite (`.git/filter-repo/`), and run
the approved secret or size rewrite in a fresh clone (`areas/history-and-secrets.md`
runbook).

## Safety class

| Form | Class | Why |
| --- | --- | --- |
| `-h`, `--help` | read | Usage |
| `--version` | read | Prints a 12-hex hash of the script, not a release number (source) |
| `--analyze` | writes-local-state | Writes reports under `.git/filter-repo/analysis/`; does not modify history `[doc]` |
| `--dry-run` | writes-local-state | Saves original and filtered fast-export streams; no rewrite `[doc]` |
| any filter (`--path`, `--invert-paths`, `--replace-text`, `--strip-blobs-bigger-than`, `--strip-blobs-with-ids`, `--mailmap`, callbacks) | mutates | Rewrites all refs, removes `origin`, expires reflogs and runs gc by default `[doc]` |
| `--sensitive-data-removal` / `--sdr` | mutates + network | Also fetches all refs first `[doc]` |
| `--force` / `-f` | mutates | Skips the fresh-clone safety check; irreversible `[doc]` |

## Options that matter

- `--sensitive-data-removal`: fetch all refs, report First Changed Commit(s), track orphaned
  LFS objects, print cleanup instructions `[doc]`. `--no-fetch` skips the fetch (risk: refs
  you lack keep the data) `[doc]`.
- `--invert-paths --path <p>` (repeat for every old name; renames are not followed),
  `--replace-text <file>` (literal, `regex:`, `glob:`; default replacement
  `***REMOVED***`), `--strip-blobs-bigger-than <size>`, `--strip-blobs-with-ids <file>`
  `[doc]`.
- `--partial`, `--refs <refs>` (implies `--partial`: mixes old and new history, no reflog
  expiry or gc) `[doc]`.
- Output files in `.git/filter-repo/` `[doc]`: `commit-map`, `ref-map`, `changed-refs`,
  `first-changed-commits`, `already_ran` (later runs continue the rewrite and skip the
  fresh-clone check; older than one day prompts), `original_lfs_objects`,
  `orphaned_lfs_objects`.

## Verified recipes

```sh
command -v git-filter-repo
git filter-repo -h | grep -c -- '--sensitive-data-removal'
git filter-repo --analyze
grep -c '^refs/pull/.*/head$' .git/filter-repo/changed-refs
cat .git/filter-repo/first-changed-commits
```

Not run here (tool absent). The second line must print `1` before a sensitive-data rewrite.
The `grep` and `cat` read the rewrite's own output files (commit IDs and ref names only).

## Footprint it leaves when interrupted or misused

- `.git/filter-repo/` with the maps and `already_ran`; a later unrelated run inherits them.
- The `origin` remote removed on purpose (a safety measure); replace-refs for old IDs when
  configured.
- Run in a non-fresh clone with `--force`: local-only work rewritten or discarded.

## Gotchas

- Clone locally with `git clone --no-local`, not `--force` on filter-repo `[doc]`.
- Signatures on commits and tags in the rewritten range, and even before it, are removed
  `[doc]` GitHub.
- Collaborators must not re-run the same command on their clones; they re-clone or rebase
  `[doc]`.
