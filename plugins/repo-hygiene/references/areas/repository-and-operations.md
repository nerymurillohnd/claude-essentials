# Repository identity and interrupted operations

Areas: G1, G2. `routine` runs the Routine checks; `deep` runs Routine and Deep.

Every command below is a read unless its row says otherwise. Facts are tagged `[observed]`
(run on Git 2.55.0, macOS, on a fixture) or `[doc]` (official page, listed under Sources).

## Contents

1. What can go wrong
2. Routine checks (G1: 1-8, G2: 9-15)
3. Deep checks
4. Recommendations and recovery
5. False positives in this area
6. Version floors
7. Sources

## What can go wrong

G1, identity and format:

- The audit runs from the wrong place: a subdirectory, a submodule, a linked worktree, or a
  repository that wraps the home directory.
- The repository is bare, shallow (history cut off), or a partial clone (objects missing
  locally and fetched on demand from a "promisor" remote).
- A sparse checkout hides part of the tree, so "not on disk" does not mean "not tracked".
- The object format is `sha256` or the ref storage is `reftable`: tools that assume SHA-1
  or loose ref files break.
- `extensions.worktreeConfig` is on, so some settings live in `config.worktree` per worktree.
- The index uses version 4, a split index (`sharedindex.*`), an untracked cache, a sparse
  index, or FSMonitor: faster, but less compatible with other tools.
- The repository is owned by another user, or `safe.directory` opts out of the ownership
  check (`*` disables it everywhere).
- HEAD is detached: new commits belong to no branch.

G2, interrupted operations and leftovers:

- A merge, rebase, cherry-pick, revert, `am` or bisect was started and never finished.
- A stale `*.lock` file blocks every write (`index.lock`, `refs/heads/<b>.lock`).
- `ORIG_HEAD`, `FETCH_HEAD`, `AUTO_MERGE`, `MERGE_MSG` are old or orphaned.
- `refs/bisect/*` refs pin old commits and keep HEAD detached.
- Tool leftovers in the working tree: `*.orig` (mergetool backup, other tools),
  `*.rej` (`git apply --reject`), `*.patch` / `*.mbox` (`format-patch`, `am`),
  `*_BASE_*`, `*_LOCAL_*`, `*_REMOTE_*`, `*_BACKUP_*` (mergetool temporaries).
- `rr-cache/` holds recorded conflict resolutions that can be replayed silently later.

## Routine checks

### G1

1. **Top level, git dir, common dir, format.**

   ```sh
   git --no-optional-locks --no-pager rev-parse --show-toplevel --show-prefix \
     --git-dir --git-common-dir --absolute-git-dir --is-bare-repository \
     --is-shallow-repository --show-object-format --show-ref-format \
     --show-superproject-working-tree
   ```

   Look for: `--show-prefix` not empty (you are in a subdirectory); `--git-dir` different from
   `--git-common-dir` (a linked worktree: `.git/worktrees/<id>`); a superproject path (you
   are inside a submodule: audit the superproject too); `true` for bare or shallow; `sha256`;
   `reftable`. Outside any repository the command exits 128 with
   `fatal: not a git repository` `[observed]`. In a submodule, `--git-dir` is
   `<super>/.git/modules/<name>` and `--show-superproject-working-tree` prints the
   superproject `[observed]`.
   Explain: "Git sees this folder as part of a larger project at X" or "this checkout is a
   second working folder of the repository at Y".

2. **Extensions and format keys.**

   ```sh
   git --no-optional-locks --no-pager config --show-scope --get-regexp \
     '^(extensions\.|core\.(repositoryformatversion|bare|worktree|sparsecheckout|sparsecheckoutcone|splitindex|untrackedcache|fsmonitor)$|index\.|feature\.|remote\.[^.]*\.(promisor|partialclonefilter)$)'
   ```

   `[observed]` values: a partial clone shows `remote.origin.promisor true`,
   `remote.origin.partialclonefilter blob:none` and `core.repositoryformatversion 1`; a
   sha256 repository shows `extensions.objectformat sha256`; a reftable repository shows
   `extensions.refstorage reftable`; `git sparse-checkout set` added
   `extensions.worktreeconfig true` and put `core.sparsecheckout` in scope `worktree`.
   A key with scope `worktree` lives in `config.worktree`, not in `.git/config`.
   Finding: "format/extension in use" with the tools it may break (see Deep 2).

3. **Shallow and partial clone.** Shallow: `--is-shallow-repository` is `true`; count the
   graft points with `wc -l < "$(git rev-parse --git-path shallow)"` (`1` on a
   `--depth 1` clone `[observed]`). Partial: `ls "$(git rev-parse --git-path objects/pack)"
   | grep -c '\.promisor$'` counts promisor packs (3 on the fixture `[observed]`).
   Missing objects: `git --no-lazy-fetch rev-list --objects --missing=print --all |
   grep -c '^?'` (3 missing blobs `[observed]`).
   Explain: "this copy does not hold the full history (shallow) / all file contents
   (partial); some checks will be incomplete, and some Git commands would download
   data".
   **Rule for the whole audit:** in a partial clone, add `--no-lazy-fetch` to every
   `git` read (Git 2.45+). `[observed]`: a plain `git ls-tree -r -l origin/topic`
   silently downloaded two missing blobs from the promisor remote (missing count 3 → 1);
   `git --no-lazy-fetch ls-tree -r -l origin/topic` printed `BAD` as their size instead.

4. **Sparse checkout.** `git config --get core.sparseCheckout` prints `true` or exits 1.
   Do not use `git sparse-checkout list` as the probe: it exits 128 with
   `fatal: this worktree is not sparse` when sparse checkout is off `[observed]`. When it
   is on, `git sparse-checkout list` prints the cone directories (`sub` `[observed]`) and
   `git config --get index.sparse` says whether the index is sparse.
   Explain: "only part of the project is on disk; the rest is tracked but hidden".

5. **Index format and caches.**

   ```sh
   git update-index --show-index-version
   git --no-optional-locks rev-parse --shared-index-path
   ```

   `--show-index-version` is a read: the index checksum and mtime did not change
   `[observed]`. Version 3 appears when entries use extended flags (skip-worktree,
   intent-to-add); 4 is path-compressed `[observed]`, `[doc]`.
   `--shared-index-path` prints `.git/sharedindex.<hash>` in split-index mode and nothing
   otherwise `[observed]`. Untracked cache: `core.untrackedCache` in config, or, when the
   extension was enabled with `update-index`, the `UNTR` signature:
   `LC_ALL=C grep -c -a -F UNTR "$(git rev-parse --git-path index)"` (heuristic: a path
   name containing `UNTR` also matches).
   Finding: informational unless another tool in use cannot read it (Deep 2).

6. **Ownership and `safe.directory`.**

   ```sh
   stat -f %Su "$(git rev-parse --git-common-dir)" 2>/dev/null \
     || stat -c %U "$(git rev-parse --git-common-dir)"
   id -un
   git --no-pager config --show-origin --show-scope --get-all safe.directory
   ```

   Owner ≠ current user: the repository is someone else's; config and hooks there run as
   you (`[doc]` git SECURITY). `safe.directory` is honored only in protected configuration
   (system, global, command line) `[doc]`; the value `*` opts out of the check for every
   repository `[doc]`. Exit 1 means none is set `[observed]`. Never add
   `-c safe.directory=…` yourself (contract section 2).

7. **Detached HEAD.**

   ```sh
   git symbolic-ref -q HEAD
   ```

   Exit 1 with no output means detached `[observed]`; `git --no-optional-locks status
   --porcelain=v2 --branch` shows `# branch.head (detached)` `[observed]`. Before calling
   it a finding, check G2: a bisect or rebase in progress detaches HEAD on purpose.
   Explain: "you are not on any branch; new commits would be easy to lose".

8. **Environment that relocates the repository.** `git rev-parse --local-env-vars` lists
   the variable *names* Git treats as repository-local (`GIT_DIR`, `GIT_WORK_TREE`,
   `GIT_CONFIG`, `GIT_ALTERNATE_OBJECT_DIRECTORIES`, …) `[doc]`, `[observed]`. Report which
   of them are set with `env | cut -d= -f1 | grep '^GIT_'` (names only; values can hold
   credentials). Details of each variable belong to `areas/config-links-identity.md`.

### G2

Run checks 9-13 in **every** worktree: state files are per worktree. `[observed]`: in a
linked worktree, `--git-path MERGE_HEAD` and `--git-path refs/bisect` resolve to
`.git/worktrees/<id>/…`, while `--git-path rr-cache` resolves to the common `.git/`.

9. **Operation in progress.**

   ```sh
   git rev-parse --git-path MERGE_HEAD --git-path rebase-merge --git-path rebase-apply \
     --git-path CHERRY_PICK_HEAD --git-path REVERT_HEAD --git-path BISECT_LOG \
     --git-path sequencer --git-path AUTO_MERGE --git-path MERGE_MSG
   ```

   Then test which of the printed paths exist (`ls -d <path> 2>/dev/null` on each; `ls`
   exits 1 when some are missing, which is expected). Mapping `[observed]` on fixtures:

   | Present | Operation |
   | --- | --- |
   | `MERGE_HEAD` | merge stopped (conflict or `--no-commit`) |
   | `rebase-merge/` | rebase (merge backend, the default) |
   | `rebase-apply/` with `applying` inside | `git am` |
   | `rebase-apply/` without `applying` | rebase with the apply backend |
   | `CHERRY_PICK_HEAD` (+ `sequencer/` for a range) | cherry-pick |
   | `REVERT_HEAD` (+ `sequencer/` for a range) | revert |
   | `BISECT_LOG`, `BISECT_START`, `refs/bisect/*` | bisect |
   | `AUTO_MERGE`, `MERGE_MSG` alone, tree clean | leftover of an earlier stop |

   `git status --porcelain=v2` does **not** report the operation; the long format does
   ("You are currently reverting commit f90c32b.") `[observed]`. Use the long format only
   to explain, never to parse. The conflict itself appears as `u` lines in porcelain v2.
   Explain: "a Y was started on <date> and left half done; until it is finished or
   cancelled, Git keeps asking about it and some commands refuse to run".

10. **Bisect.** `git --no-pager bisect log` is a read (prints the start command and every
    good/bad mark) `[observed]`. `cat "$(git rev-parse --git-path BISECT_START)"` holds the
    branch to return to (`main` `[observed]`). `git --no-pager for-each-ref
    --format='%(refname) %(objectname:short)' refs/bisect` lists the pins
    (`refs/bisect/bad`, `refs/bisect/good-<sha>` `[observed]`). Never run
    `git bisect visualize` (starts gitk or a pager) or `git bisect run` while auditing.

11. **Stale lock files.**

    ```sh
    find "$(git rev-parse --git-common-dir)" -name '*.lock' -type f \
      -exec stat -f '%Sm %z %N' -t '%Y-%m-%dT%H:%M' {} + 2>/dev/null
    pgrep -lx git
    ```

    (Linux: `stat -c '%y %s %n'`.) `[observed]`: an `index.lock` and a
    `refs/heads/main.lock` were found with their ages; a commit then failed with
    `Unable to create '…/index.lock': File exists`, while `git status` still exited 0. A
    lock is stale only when it is old **and** no Git process is running; `pgrep` cannot tell
    which repository a process works in, so a running `git` means "ask the user".
    Explain: "a crashed Git command left a 'do not touch' marker; every change is blocked
    until it is removed".

12. **Age of `ORIG_HEAD`, `FETCH_HEAD`, `AUTO_MERGE`.**

    ```sh
    stat -f '%Sm %N' -t '%Y-%m-%dT%H:%M' "$(git rev-parse --git-path ORIG_HEAD)" \
      "$(git rev-parse --git-path FETCH_HEAD)" 2>&1
    head -n 5 "$(git rev-parse --git-path FETCH_HEAD)" \
      | sed -E 's#(://)[^/@[:space:]]+@#\1***@#g' | cut -c1-160
    ```

    `FETCH_HEAD` age is the last fetch; lines hold the SHA, `not-for-merge`, the branch
    and the remote URL (redact it) `[observed]`. `ORIG_HEAD` is written by reset, merge,
    rebase and am; it is not a reflog and has no history `[doc]` (`git-reset`). A missing
    file prints `No such file or directory` `[observed]`, which is not a finding.

13. **Leftover files in the tree.**

    ```sh
    git --no-optional-locks --no-pager ls-files -o --exclude-standard -- '*.orig' '*.rej' \
      '*.patch' '*.mbox' '*.diff' '*_BACKUP_*' '*_BASE_*' '*_LOCAL_*' '*_REMOTE_*' | head -n 50
    ```

    `[observed]`: listed `app.txt.orig` and `s.txt.rej`. Run it also with `-i` (ignored
    leftovers) and against `git ls-files -c` (tracked leftovers, committed by mistake).
    Fingerprint, never read, a leftover whose name matches a secret shape. `*.orig` is the
    mergetool backup with the conflict markers (`[doc]` `mergetool.keepBackup`, default
    true); `*.rej` holds hunks `git apply --reject` could not apply `[doc]`.

14. **Leftover patch still relevant?** For a `*.patch` or `*.mbox` file (headers only):
    `git apply --stat --summary <file>` (read). Then `git apply --check <file>` (exit 0:
    still applies) and `git apply --check -R <file>` (exit 0: already applied)
    `[observed]`: a patch whose file already existed failed `--check` and passed
    `--check -R`. Explain: "this saved change is already in the code" or "not yet".

15. **Recorded resolutions (`rr-cache`).**

    ```sh
    find "$(git rev-parse --git-path rr-cache)" -mindepth 1 -maxdepth 1 -type d | wc -l
    find "$(git rev-parse --git-path rr-cache)" -name postimage | wc -l
    git config --show-origin --get rerere.enabled
    git rerere status
    ```

    Directories without a `postimage` are unresolved records; `gc` prunes resolved ones
    after 60 days and unresolved after 15 by default `[doc]`. `git rerere status` and
    `remaining` are reads (exit 0) `[observed]`. Never `cat` a `preimage` (contract 4); never
    run `git rerere diff` (it runs the `diff` found in PATH and prints file contents `[doc]`).
    `rerere.enabled` may come from the global config `[observed]`: report its origin.

## Deep checks

1. **Index internals.** `git ls-files --debug -- <path>` prints ctime, mtime, dev, ino,
   uid, size and flags per entry; the format "may change at any time" `[doc]`, so read it,
   never parse it. Use it to explain a path that `status` keeps reporting as changed.
   `git update-index --test-untracked-cache` checks whether the filesystem supports the
   untracked cache; it briefly creates and removes directories in the working tree and
   prints `Testing mtime in '<path>' ...... OK` `[observed]`: class writes-local-state, run
   it only in `deep` and say so.

2. **Compatibility with the tools in use.** Cross the formats found in G1 with the tools
   the repository uses (CI images, IDE Git integrations, libgit2- or JGit-based tools, the
   hosting provider, older Git on other machines). `[doc]`: index v4 is supported since Git
   1.8.0, libgit2 since 2016, JGit since 2020 (`git-update-index`); "Older versions of Git
   will not understand the sparse directory entries index extension" (`git-sparse-checkout`);
   "Older Git versions will refuse to access repositories with this extension"
   (`extensions.worktreeConfig`, `git-worktree`). Report what you verified and what you
   could not.

3. **Reconstruct an interrupted operation.** Rebase (`rebase-merge/`): `head-name`
   (branch being rebased), `onto`, `orig-head`, `done`, `git-rebase-todo`, `msgnum`/`end`
   (progress) `[observed]`: `refs/heads/topic`, 1 of 2 done, one `pick` left. Read the todo
   with `grep -v '^#' <file> | head -n 20`. Cherry-pick or revert range: `sequencer/todo`
   and `sequencer/head` (the HEAD before it started) `[observed]`. `am`: `rebase-apply/next`
   and `last` (patch counter) `[observed]`; list the current patch with
   `git apply --stat "$(git rev-parse --git-path rebase-apply/patch)"`, not with
   `git am --show-current-patch` (prints the whole patch, which may contain secrets).
   Then match the reflog: `git --no-replace-objects --no-pager reflog -n 20
   --format='%gd %h %gs'` shows `rebase (start): checkout main` `[observed]`. Report what
   was in flight, since when, and which commits are not yet on any branch.

4. **Worktrees admin state for G2.** For each entry of `git worktree list --porcelain`,
   rerun Routine 9-11 with `git -C <worktree-path> …`. A worktree whose directory is gone
   cannot finish its operation: note it for G9 (`areas/stashes-worktrees-submodules.md`).

## Recommendations and recovery

Every row is an approval item. Re-check the precondition right before running it.

| Finding | Recommended action (literal command) | Undo | Approval scope notes |
| --- | --- | --- | --- |
| Merge stopped, user wants to cancel | `git merge --abort` | Irreversible for conflict resolutions typed in the tree; the merge can be restarted with `git merge <branch>` | Only the merge; working-tree edits made during the conflict are lost. Precondition: `git status` reviewed with the user |
| Rebase stopped, cancel | `git rebase --abort` | `git reset --hard <orig-head from rebase-merge/orig-head>` returns to the state reached before the abort only if that SHA was recorded | Restores `head-name` to `orig-head`. Record both SHAs first |
| Rebase stopped, keep what is done and stop | `git rebase --quit` | Irreversible (state files removed); HEAD stays where it is | Leaves HEAD detached at the partial result: create a branch first (separate item) |
| Cherry-pick or revert stopped | `git cherry-pick --abort` / `git revert --abort` | Re-run the original command | Only that sequence |
| `am` stopped | `git am --abort` | Re-run `git am <mbox>` if the mbox still exists | Also clears rerere metadata `[doc]` |
| Bisect abandoned | `git bisect reset` | `git bisect replay <saved-log>` after saving `git bisect log > <file-outside-repo>` | Checks out the `BISECT_START` branch; deletes `refs/bisect/*` and `BISECT_*` files |
| Stale lock, no Git process | `rm <absolute-path-to>.lock` | Irreversible (file is empty or partial); harmless when stale | One path per item. Never while `pgrep -lx git` shows a process the user cannot explain |
| Orphan `AUTO_MERGE` / `MERGE_MSG`, no operation | `rm <absolute-path>` | Irreversible | Only when Routine 9 shows no operation in that worktree |
| Leftover `*.orig`, `*.rej`, `*_BASE_*` | `git clean -f -- <path>` (or `rm <path>`) | Irreversible (untracked) | One list of literal paths; never a glob; dry-run first with `git clean -n -- <path>` |
| Leftover tracked by mistake | `git rm --cached -- <path>` and commit | `git reset -q HEAD -- <path>` before the commit | Keeps the file on disk |
| Detached HEAD with commits no branch holds | `git branch <new-name> <sha>` | `git branch -d <new-name>` | Protect work first; switching away is a separate item |
| `rr-cache` unwanted | `git rerere forget <pathspec>` (during a conflict) or `git rerere gc` | Irreversible | `gc` uses `gc.rerereResolved`/`gc.rerereUnresolved` |
| Partial clone, audit needs every object | `git backfill` (Git 2.49+, downloads the missing blobs; see `commands/git-backfill.md`) | Irreversible download | Network; state the size risk first |
| Ownership mismatch | `git clone --no-local <path> <new-path>` and audit the copy | Delete the copy | Never add `safe.directory` for the user |

## False positives in this area

- Detached HEAD during bisect or rebase is expected, not a finding.
- `S` entries (skip-worktree) in a sparse checkout are how sparse checkout works.
- `AUTO_MERGE` and `MERGE_MSG` alone remained after a sequence of reverts on a clean tree
  `[observed]`: stale files, not an operation in progress.
- A lock file younger than a few minutes may belong to an IDE or a background fetch.
- `FETCH_HEAD` missing only means no fetch ever ran in this worktree.
- `git status` exiting 0 does not prove the index is writable (`index.lock` case
  `[observed]`).
- `*.patch` files can be intentional (a `patches/` directory used by a build).
- An empty `git sparse-checkout list` error does not mean the repository is broken; it
  means sparse checkout is off.

## Version floors

| Feature | Floor | Source |
| --- | --- | --- |
| `--no-optional-locks` | 2.15 | RelNotes 2.15.0 |
| `rev-parse --is-shallow-repository` | 2.15 | RelNotes 2.15.0 |
| `--end-of-options` | 2.24 | RelNotes 2.24.0 |
| `git backfill` | 2.49 | RelNotes 2.49.0 |
| `update-index --show-index-version` | 2.43 | RelNotes 2.43.0 |
| `git --no-lazy-fetch` | 2.45 | RelNotes 2.45.0 |
| `safe.directory` | 2.30.3 / 2.35.2 (security releases) | RelNotes |
| Everything else here | available in 2.55 `[observed]`; floor not verified | — |

## Sources

- https://git-scm.com/docs/git (options, SECURITY, `GIT_NO_LAZY_FETCH`)
- https://git-scm.com/docs/git-rev-parse
- https://git-scm.com/docs/git-update-index
- https://git-scm.com/docs/git-sparse-checkout
- https://git-scm.com/docs/git-worktree
- https://git-scm.com/docs/git-config (`safe.directory`)
- https://git-scm.com/docs/git-status
- https://git-scm.com/docs/git-bisect
- https://git-scm.com/docs/git-apply
- https://git-scm.com/docs/git-mergetool
- https://git-scm.com/docs/git-rerere
- https://git-scm.com/docs/git-reset
- https://git-scm.com/docs/gitrepository-layout
- https://github.com/git/git/tree/master/Documentation/RelNotes
- Corpus: `commands/git-rev-parse.md`, `commands/git-update-index.md`,
  `commands/git-sparse-checkout.md`, `commands/git-am.md`, `commands/git-apply.md`,
  `commands/git-mergetool.md`, `commands/git-rerere.md`, `commands/git-status.md`,
  `commands/git-bisect.md`, `commands/git-rebase.md`
