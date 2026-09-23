# Stashes, worktrees, submodules and nested repositories

Areas: G8, G9, G10. `routine` runs the Routine checks; `deep` runs Routine and Deep.

Every command below is a read unless its row says otherwise. Facts are tagged `[observed]`
(run on Git 2.55.0, macOS, on a fixture) or `[doc]` (official page, listed under Sources).
Run walks with `--no-replace-objects` (contract section 2). In a partial clone add
`--no-lazy-fetch` after `git`.

## Contents

1. What can go wrong
2. Routine checks (G8: 1-5, G9: 6-9, G10: 10-15)
3. Deep checks
4. Recommendations and recovery
5. False positives in this area
6. Version floors
7. Sources

## What can go wrong

G8, stashes (a stash is a set of changes put aside without a commit on any branch):

- Old stashes nobody remembers, with work that exists nowhere else.
- Stashes with an untracked part (`-u`, `-a`) that may hold large or secret files.
- Stashes whose base commit belongs to a deleted branch.
- Stashes that are already fully in the default branch (safe to drop) mixed with ones that
  are not.
- Dropped or cleared stashes still recoverable from unreachable commits, until `gc`.

G9, worktrees (extra working folders attached to the same repository):

- A worktree folder deleted by hand: its admin files stay (`prunable`) and its branch
  stays "checked out" elsewhere.
- Locked worktrees whose reason is stale.
- Detached or dirty worktrees with uncommitted work the user forgot.
- Admin directories under `.git/worktrees/` that no registration lists.
- Per-worktree config (`config.worktree`) that differs from what the user expects.

G10, submodules, subtrees, nested repositories:

- `.gitmodules` URL, `.git/config` URL and the recorded commit disagree.
- Submodules not initialized, checked out at another commit, or with local changes.
- Removed submodules whose repository still sits in `.git/modules/<name>`.
- Subtree merges whose source remote is unknown.
- Untracked repositories inside the tree: `git status` shows them as one untracked
  directory, and `git clean` skips them unless given `-f` twice.
- A `.git` file that points to a missing or foreign repository; `git status` does not
  show the directory at all.

## Routine checks

### G8

1. **Inventory.**

   ```sh
   git --no-replace-objects --no-pager stash list \
     --format='%gd%x09%H%x09%P%x09%ci%x09%s'
   git --no-replace-objects rev-list --count --walk-reflogs refs/stash
   ```

   Use `%gd` without `--date`: with `--date=iso` the selector becomes
   `stash@{2026-09-22 21:49:27 -0600}` and the index is lost `[observed]`. `%P` gives the
   parents: base commit (`^1`), saved index (`^2`), and, only for `-u`/`-a` stashes, the
   untracked part (`^3`) `[doc]` (DISCUSSION), `[observed]` (three parents on the `-u`
   stash, two on the others). The subject is `On <branch>: <message>` or
   `WIP on <branch>: <sha> <subject>`; the branch name is where the stash was made, not
   proof of which tool made it (contract section 9).
   Explain: "a stash is work set aside on <date> while on <branch>; it is not on any
   branch and it is easy to forget or delete by accident".

2. **Files in each stash, including the untracked part.**

   ```sh
   git --no-optional-locks --no-pager stash show --no-ext-diff --no-textconv \
     --name-status --include-untracked 'stash@{1}'
   git --no-replace-objects --no-pager ls-tree -r -l 'stash@{0}^3'
   ```

   Always pass an explicit format: with `stash.showPatch=true` a bare `git stash show`
   prints the patch (file contents) `[doc]`. `--include-untracked` adds the `^3` files as
   `A` lines `[observed]`: `A big.bin`, `A new.txt`. `ls-tree -l` gives sizes
   (`3072000 big.bin` `[observed]`). A missing `^3` makes
   `git rev-parse --verify --quiet 'stash@{1}^3'` exit 1 `[observed]`. Apply the
   secret-shaped filter from `areas/worktree-index-rules.md` (check 12) to these names;
   report path and size, never content.

3. **Size of saved changes.** `git --no-replace-objects --no-pager ls-tree -r -l
   'stash@{1}' -- <path>` for each path from check 2 (`12 s.txt` `[observed]`). Report the
   largest and the total per stash.

4. **Base commit and its branch.**

   ```sh
   git --no-replace-objects --no-pager for-each-ref --count=3 --contains 'stash@{1}^1' \
     --format='%(refname:short)' refs/heads refs/remotes
   git show-ref --verify --quiet refs/heads/<branch-from-subject>
   ```

   No output from `for-each-ref`: the base is reachable from no branch (it was rebased or
   deleted); `show-ref` exit 1: the branch named in the subject no longer exists
   (`[observed]` 0 for `main`, 1 for a missing name). Explain: "this stash was made on a
   branch that no longer exists; the stash is the only copy of that work".

5. **Saved index vs base.** `git --no-replace-objects --no-pager diff-tree -r
   --no-ext-diff --no-textconv --name-status 'stash@{1}^1' 'stash@{1}^2'` lists what was
   staged at stash time; empty means nothing was staged `[observed]`.

### G9

6. **Registered worktrees.**

   ```sh
   git --no-pager worktree list --porcelain -z | tr '\0' '\n'
   ```

   Records start with `worktree <path>`, then `HEAD <sha>`, then `branch <ref>` or
   `detached`, and optional `bare`, `locked [<reason>]`, `prunable <reason>` `[doc]`.
   `[observed]`: `prunable gitdir file points to non-existent location` for a folder
   deleted by hand; `locked on usb disk` after `git worktree lock --reason`; `detached`
   for the main worktree during a bisect. Use `-z` when paths may hold newlines `[doc]`.
   `git worktree list -v` shows the same annotations in a human layout `[observed]`.
   Explain "prunable": "the folder is gone, but Git still reserves its branch for it".

7. **What prune would remove.**

   ```sh
   git --no-pager worktree prune --dry-run --verbose
   ```

   `[observed]`: printed `Removing worktrees/wt-gone: gitdir file points to non-existent
   location` and `Removing worktrees/orphan: gitdir file does not exist`, yet removed
   nothing (the dry-run output uses the same verb). Without `--dry-run` it deletes (contract
   section 1).

8. **Dirty or detached worktrees.** For each registered path that exists:
   `git -C <path> --no-optional-locks --no-pager status --porcelain=v2 --branch
   --untracked-files=normal` (`? dirty.txt` `[observed]`), then run G2 checks there
   (`areas/repository-and-operations.md`).

9. **Branch checked out elsewhere and per-worktree config.** Collect every `branch` line
   from check 6: a branch listed there cannot be deleted or checked out in another
   worktree. Per-worktree config exists when `extensions.worktreeConfig` is true; list it
   with `git -C <path> --no-pager config --worktree --list` (keys and values; redact as for
   any config) `[doc]`.

### G10

10. **Declared vs configured vs recorded.**

    ```sh
    git --no-pager config --file .gitmodules --get-regexp '^submodule\.' \
      | sed -E 's#(://)[^/@[:space:]]+@#\1***@#g'
    git --no-pager config --get-regexp '^submodule\.' \
      | sed -E 's#(://)[^/@[:space:]]+@#\1***@#g'
    git --no-optional-locks --no-pager ls-files --stage | awk '$1=="160000"'
    ```

    `[observed]`: `.gitmodules` had the original URL for `libs/a`, `.git/config` had
    `https://changed.example.com/a.git`; two gitlinks (mode `160000`) recorded commit
    `29c050a`. A gitlink with no `.gitmodules` entry, or an entry with no gitlink, is a
    finding. `submodule.<name>.update=!<command>` in `.git/config` runs a program on
    update `[doc]`: report it for G12.

11. **Submodule state.**

    ```sh
    git --no-optional-locks submodule status
    git --no-optional-locks --no-pager status --porcelain=v2 --ignore-submodules=none
    ```

    Prefix `-` not initialized, `+` checked-out commit differs from the recorded one, `U`
    conflict `[doc]`. `[observed]`: `+99676cf… libs/a (99676cf)` (moved) and
    `-29c050a… libs/b` (after `deinit`). Porcelain v2 shows `1 .M SC.. 160000 …` for the
    moved one: `S` submodule, `C` commit changed, `M` tracked changes, `U` untracked
    `[doc]`. `--no-optional-locks` sets `GIT_OPTIONAL_LOCKS=0`, which the child Git
    processes inherit `[doc]` (`git`, the environment variable). Never run
    `git submodule foreach`: it evaluates an arbitrary shell command in each submodule
    `[doc]`.

12. **Absorbed or embedded git directory.** `test -f <path>/.git` means the submodule's
    repository lives in the superproject (`gitdir: ../../.git/modules/libs/a`
    `[observed]`); `test -d <path>/.git` means an embedded repository that
    `git submodule absorbgitdirs` would move `[doc]`. `git rev-parse --resolve-git-dir
    <path>/.git` prints where it really points `[doc]`, `[observed]`.

13. **Untracked nested repositories and `.git` files.**

    ```sh
    find . -path ./.git -prune -o -name .git -print | head -n 50
    git --no-optional-locks --no-pager ls-files -o --directory | head -n 50
    git clean -n -d
    git clean -n -d -f -f
    ```

    Compare the `find` list with the gitlinks from check 10: every other `.git` is a nested
    repository or a stray `.git` file. `[observed]` in a superproject: `status` showed
    `? nested/` but did **not** show `elsewhere/` (a directory whose `.git` file points to
    a missing path); `ls-files -o --directory` listed both; `git clean -n -d` said
    `Would remove elsewhere/` and omitted `nested/`; with `-f -f` it listed both. In
    another tree, `git clean -n -d` printed `Would skip repository vendor/other`
    `[observed]`. `git clean -n` is a dry run and never deletes `[doc]`. A `.git` file
    that fails `git rev-parse --resolve-git-dir <path>/.git` (exit 128, `fatal: not a git
    repository: /nonexistent/path/.git` `[observed]`) points to a missing repository.
    Bound `find` in large trees, and note that it also descends into ignored directories
    such as `node_modules` on purpose.
    Explain: "there is a separate project inside this one; Git ignores its contents, and
    a later clean-up with force would delete it with all its history".

14. **Subtree merges.**

    ```sh
    git --no-replace-objects --no-pager log --all --extended-regexp \
      --grep='^git-subtree-(dir|split|mainline):' \
      --format='%h %ci %(trailers:key=git-subtree-dir,valueonly,separator=%x2C)' | head -n 20
    ```

    `[observed]`: `e8d8f3c 2026-09-22 … vendor/lib`. `git subtree` writes these trailers;
    `git-subtree-split` is the upstream commit. Cross the directories with the remotes
    (`git remote -v`, redacted, `areas/branches-remotes-tags.md`): a subtree with no
    remote cannot be updated the same way.

15. **Leftover submodule repositories.**

    ```sh
    git --no-pager config --file .gitmodules --get-regexp '\.path$'
    find "$(git rev-parse --git-common-dir)/modules" -maxdepth 3 -name HEAD -type f
    du -sk "$(git rev-parse --git-common-dir)/modules/<name>"
    ```

    A directory under `.git/modules/` with no `.gitmodules` entry belongs to a removed
    submodule `[observed]`: after `git rm libs/b`, `.git/modules/libs/b` (120 KiB) stayed.
    Directories are named after the submodule **name**, not its path `[doc]`
    (`gitrepository-layout`). Nested names (`libs/a`) sit one level deeper, hence
    `-maxdepth 3`.

## Deep checks

1. **Per-file comparison of every stash against the default branch.** For each path a
   stash changed (and each file of its untracked part), compare the saved blob with the
   default branch and with the stash's base:

   | Class | Meaning |
   | --- | --- |
   | `identical` | the default branch already has exactly this version |
   | `base-only` | the default branch still has the base version: the change exists only in the stash |
   | `diverged` | both the stash and the default branch changed it differently |
   | `absent-on-<branch>` | the path does not exist on the default branch (new file, or deleted there) |
   | `deleted-in-stash` | the stash deletes a file that exists at its base |

   Read-only snippet; write it to a scratch file outside the repository and run
   `bash <file> 'stash@{1}' main` (the Bash tool's zsh does not support `read -d ''`):

   ```bash
   st=$1 def=$2
   cls() {
     local p=$1 saved=$2 base=$3 cur
     cur=$(git --no-replace-objects rev-parse --verify --quiet --end-of-options "${def}:${p}")
     if [ -z "$saved" ]; then printf '%s\t%s\n' "deleted-in-stash" "$p"
     elif [ "$saved" = "$cur" ]; then printf '%s\t%s\n' "identical" "$p"
     elif [ -z "$cur" ]; then printf '%s\t%s\n' "absent-on-${def}" "$p"
     elif [ "$cur" = "$base" ]; then printf '%s\t%s\n' "base-only" "$p"
     else printf '%s\t%s\n' "diverged" "$p"; fi
   }
   git --no-replace-objects diff-tree -r -z --no-ext-diff --no-textconv --name-only \
     "${st}^1" "${st}" | while IFS= read -r -d '' p; do
     cls "$p" "$(git --no-replace-objects rev-parse --verify --quiet --end-of-options "${st}:${p}")" \
       "$(git --no-replace-objects rev-parse --verify --quiet --end-of-options "${st}^1:${p}")"
   done
   if git rev-parse --verify --quiet --end-of-options "${st}^3" >/dev/null; then
     git --no-replace-objects ls-tree -r -z --name-only "${st}^3" | while IFS= read -r -d '' p; do
       printf 'untracked:'
       cls "$p" "$(git --no-replace-objects rev-parse --verify --quiet --end-of-options "${st}^3:${p}")" ""
     done
   fi
   ```

   `[observed]` on fixtures, every class but `deleted-in-stash`: `base-only s.txt`,
   `untracked:absent-on-main big.bin`, `diverged b`, `identical b` (against a branch that
   had landed the same change), `absent-on-main c` (file deleted on main). Give
   `rev-parse --verify` one argument per call: with three it exits 1 and prints nothing
   `[observed]`. A stash whose every path is `identical` is fully landed; any `base-only`,
   `diverged` or `absent-on-…` path is unique work.

2. **Saved index vs base, and the untracked part.** Check 5 for every stash; for the `^3`
   tree report "empty" or its file count and total size (`ls-tree -r -l`).

3. **Dropped stashes.** Run after the unreachable census order in contract section 2:

   ```sh
   git --no-replace-objects -c core.fsmonitor=false -c gc.auto=0 -c maintenance.auto=false \
     fsck --unreachable --no-reflogs --no-progress 2>/dev/null \
     | awk '$2=="commit"{print $3}' > "<evidence-dir>/unreachable-commits.txt"
   git --no-replace-objects --no-pager log --no-walk --merges --stdin \
     --format='%H %P | %ci | %s' < "<evidence-dir>/unreachable-commits.txt"
   git --no-replace-objects --no-pager stash list --format='%H'
   ```

   Stash commits are merge commits (two or three parents), so `--merges` narrows the list
   `[doc]` (EXAMPLES). Subtract the live stashes: `--no-reflogs` ignores the stash reflog,
   so live entries below `stash@{0}` appear as unreachable too `[observed]`: the list held
   both the dropped `322b286… On main: dropped` and the live `stash@{1}`. A plain
   `git fsck --dangling` (reflogs count as roots) printed only the dropped one
   `[observed]`. A subject like `On main:` or `WIP on` suggests a stash; confirm the shape
   with the parents (second parent's parent equals the first parent). Then classify it
   with deep check 1 (pass the SHA instead of `stash@{n}`) `[observed]`.

4. **Worktree admin directories without a registration.** Compare
   `ls "$(git rev-parse --git-common-dir)/worktrees"` with the records from check 6.
   `[observed]`: `worktrees/orphan` (no `gitdir` file) did not appear in
   `git worktree list` (3 records for 3 real entries) but did appear in
   `prune --dry-run --verbose`. For each admin directory, `locked` holds the lock reason
   and `gitdir` the path of the worktree's `.git` file `[doc]`.

5. **Submodule history and removed-submodule objects.** `git --no-replace-objects --no-pager
   log --format='%h %ci %s' -- .gitmodules` shows when submodules were added or removed
   (`remove b` `[observed]`). For each leftover `.git/modules/<name>` (check 15), count its
   refs and unique commits with `git --git-dir=<that-dir> for-each-ref --count=5` and
   `git --git-dir=<that-dir> rev-list --count --all`; unpushed commits there are work at
   risk.

## Recommendations and recovery

| Finding | Recommended action (literal command) | Undo | Approval scope notes |
| --- | --- | --- | --- |
| Stash with unique work (any path not `identical`) | Preserve first: `git branch archive/stash-2026-09-22 'stash@{1}'` | `git branch -D archive/stash-2026-09-22` | Only the branch; no `pop`, `apply` or `drop`. The branch points at the stash commit and keeps all its parents reachable `[observed]` |
| Stash fully landed (`identical` everywhere) | `git stash drop 'stash@{1}'` | `git stash store -m "<original subject>" <sha-recorded-before>`; it returns as `stash@{0}`, not at its old index `[observed]` | Record the SHA first (pre-state). Indexes shift after a drop: re-list before the next item |
| Stash to restore as a branch | `git stash branch <new-branch> 'stash@{1}'` | `git switch -`, `git branch -D <new-branch>`, then `git stash store -m "<original subject>" <sha-recorded-before>` (the stash is dropped on success) | Changes the checkout: working tree must be clean |
| Dropped stash worth keeping | `git stash store -m "recovered: dropped" 322b28699604a0ab4159ed62302a191b4b2a56ad` | `git stash drop 'stash@{0}'` | Writes `refs/stash` reflog only |
| Prunable worktree | `git worktree prune --verbose` | Irreversible for admin files; the branch is untouched and can be checked out again | Prunes **every** prunable entry: list them in the item. `--expire <time>` narrows it `[doc]` |
| Stale lock on a worktree | `git worktree unlock <path>` | `git worktree lock --reason "<reason>" <path>` | Only the lock |
| Worktree no longer needed, clean | `git worktree remove <path>` | `git worktree add <path> <branch>` | Refuses an unclean worktree without `--force` `[doc]`; never add `--force` without its own item |
| Worktree moved by hand | `git worktree repair <new-path>` | Irreversible (rewrites link files) | Only the named paths |
| `.git/config` URL ≠ `.gitmodules` | `git submodule sync -- libs/a` (use `.gitmodules`) or `git submodule set-url -- libs/a <url>` (change `.gitmodules`) | Re-set the previous URL with `git config submodule.libs/a.url <old-url>` | Decide which URL is right first; `set-url` changes a tracked file |
| Submodule at another commit | `git submodule update -- libs/a` (checkout recorded commit) or record the new one: `git add libs/a` | `git -C libs/a checkout <previous-sha>` | `update` detaches the submodule HEAD; unpushed commits there first need a branch |
| Uninitialized submodule wanted | `git submodule update --init -- libs/b` | `git submodule deinit -- libs/b` | Network |
| Leftover `.git/modules/<name>` | Back it up, then `rm -rf <absolute-path>/.git/modules/libs/b` | Irreversible without the backup | Only after deep check 5 shows nothing unpushed |
| Embedded submodule git dir | `git submodule absorbgitdirs -- <path>` | Irreversible layout change | Recursive by default `[doc]` |
| Untracked nested repository | Decide: make it a submodule, ignore it, or move it out | — | Never `git clean -f -f -d` for it without its own item: it deletes the nested history |
| Broken `.git` file | `rm <absolute-path>/.git` (file only) | Recreate it with the recorded `gitdir:` line | Record the line first (it is a path, not a secret) |

## False positives in this area

- A clean checkout does not mean no stash (contract section 9).
- `WIP on` in a subject is not proof of the tool that made it.
- An unreachable merge commit from `fsck --no-reflogs` can be a live stash below
  `stash@{0}` `[observed]`.
- `identical` against the default branch is not `identical` against every branch; run the
  comparison against the branch the user cares about.
- A `locked` worktree on removable media is expected; do not prune or unlock it without
  asking.
- `prune --dry-run --verbose` prints "Removing" for entries it does not remove
  `[observed]`.
- A `.git/modules/<name>` for a submodule present in another branch is not a leftover:
  check `git log --all -- .gitmodules` first.
- `git status` showing a clean tree does not mean there is no nested repository
  (`elsewhere/` case `[observed]`).

## Version floors

| Feature | Floor | Source |
| --- | --- | --- |
| `worktree list` annotates `prunable` | 2.31 | RelNotes 2.31.0 |
| `stash show --include-untracked` / `--only-untracked` | 2.32 | RelNotes 2.32.0 |
| `worktree list --porcelain -z` | 2.36 | RelNotes 2.36.0 |
| `stash export` / `import` | 2.51 | RelNotes 2.51.0 |
| Everything else here | available in 2.55 `[observed]`; floor not verified | — |

## Sources

- https://git-scm.com/docs/git-stash
- https://git-scm.com/docs/git-worktree
- https://git-scm.com/docs/git-submodule
- https://git-scm.com/docs/gitmodules
- https://git-scm.com/docs/gitrepository-layout
- https://git-scm.com/docs/git-clean
- https://git-scm.com/docs/git-fsck
- https://git-scm.com/docs/git-rev-parse
- https://git-scm.com/docs/git (`GIT_OPTIONAL_LOCKS`)
- https://github.com/git/git/tree/master/Documentation/RelNotes
- Corpus: `commands/git-stash.md`, `commands/git-worktree.md`, `commands/git-submodule.md`,
  `commands/git-clean.md`, `commands/git-rev-parse.md`, `commands/git-fsck.md`,
  `commands/git-for-each-ref.md`, `areas/repository-and-operations.md`,
  `areas/worktree-index-rules.md`, `areas/branches-remotes-tags.md`
