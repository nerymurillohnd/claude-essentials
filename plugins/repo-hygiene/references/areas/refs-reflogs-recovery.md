# Ref namespaces, reflogs and recovery

Areas: G15, G16. `routine` runs the Routine checks; `deep` runs Routine and Deep.

Every recipe was run on Git 2.55.0 against the planted fixture unless it is tagged `[doc]`.
Write `<evidence>` as the evidence-package directory (`audit-contract.md` section 10).
`--no-replace-objects` is a global option and goes before the subcommand. In `deep`, run
this area **before** anything that writes objects (`merge-tree --write-tree`, `fsck
--lost-found`, `fetch`): the census must see the repository as the user left it.

## Contents

1. What can go wrong
2. Routine checks (G15 1–4, G16 5–8)
3. Deep checks (G15 9–11, G16 12–18)
4. Recommendations and recovery
5. Pro Git 10.7, corrected
6. False positives in this area
7. Version floors
8. Sources

## What can go wrong

- **G15.** Refs outside `refs/heads`, `refs/tags` and `refs/remotes` change what Git shows or
  keeps: `refs/replace/*` silently swaps one commit for another in `log`, `rev-list`,
  `cat-file` and `%(ahead-behind)`; `refs/original/*` is a `filter-branch` leftover that pins
  the pre-rewrite history (and any secret in it); tool refs (`refs/codex/*`, `refs/imerge/*`,
  `refs/branchless/*`, `refs/git-svn`, `refs/remotes/p4/*`) keep objects alive and may point
  at trees or blobs, not commits; `refs/bisect/*` is an abandoned bisect;
  `refs/prefetch/*` comes from scheduled maintenance; `refs/notes/*` carries notes;
  `refs/namespaces/*` is server-side namespacing; `info/grafts` is the obsolete ancestor of
  replace refs.
- **G16.** Work survives only in reflogs: a commit lost to `reset --hard`, stash entries
  below the top (a stash list **is** the reflog of `refs/stash`), a deleted branch's last
  tip. Reflog entries expire (defaults 90 days reachable, 30 days unreachable), and then
  `gc` removes the objects. A dropped stash is already unreachable. `.git/lost-found/` holds
  residue from an earlier `fsck --lost-found` that nobody inventoried.

Plain words for the report: a **ref** is a name for an object; a **reflog** is the local
history of where one ref pointed; a **dangling** or **unreachable** object is one no ref
reaches any more (not the same as garbage); a **replace ref** tells Git "whenever you read
commit A, show commit B instead".

## Routine checks

### G15 — Ref namespaces

1. **Namespace census with counts.**

   ```sh
   git --no-pager for-each-ref --format='%(refname)' \
     | awk -F/ '{ns=$1"/"$2; if ($2=="remotes") ns=ns"/"$3; print ns}' | sort | uniq -c
   ```

   `[observed]` fixture: `refs/bisect` 2, `refs/codex` 1, `refs/heads` 8, `refs/notes` 1,
   `refs/original` 1, `refs/remotes/origin` 3, `refs/replace` 1, `refs/stash` 1,
   `refs/tags` 4. Anything outside heads, tags, remotes and stash is a tripwire for `deep`.

2. **Refs that point at something other than a commit.**

   ```sh
   git --no-pager for-each-ref --format='%(objecttype) %(refname)' \
     | awk '$1!="commit" && !($1=="tag" && $2 ~ /^refs\/tags\//)'
   ```

   `[observed]` `tree refs/codex/snapshot-1`; a blob ref printed `blob refs/tool/blobref`.
   A tree or blob ref is a tool snapshot, not a branch: it cannot be checked out or merged.

3. **Pseudo-refs and root refs.**

   ```sh
   git --no-pager for-each-ref --include-root-refs --format='%(refname)' | grep -v '^refs/'
   ```

   `[observed]` `BISECT_EXPECTED_REV`, `HEAD`, `ORIG_HEAD` (Git ≥ 2.45). `FETCH_HEAD` and
   `MERGE_HEAD` are not refs and are not listed; G2 (interrupted operations) checks them as
   files. Replace refs: `git --no-pager replace -l --format=long` → `[observed]`
   `21a4d8d… (commit) -> 0b5d6e5… (commit)`.

4. **Storage, grafts, per-worktree refs.**

   ```sh
   git rev-parse --show-ref-format
   git rev-parse --git-path info/grafts
   find <common-dir>/worktrees -path '*/refs/*' -type f
   ```

   `files` or `reftable` (Git ≥ 2.45). With `files`, `packed-refs` lines are storage, not
   extra branches (`[observed]` 16 packed + 6 loose on the fixture). A present `info/grafts`
   file is a finding (obsolete; `git replace --convert-graft-file` migrates it `[doc]`).
   **Per-worktree refs are invisible from other worktrees**: `[observed]` a bisect started
   in a linked worktree left `worktrees/wt-live/refs/bisect/*`, which `for-each-ref` in the
   main worktree did not list; `git rev-parse --verify -q worktrees/wt-live/refs/bisect/bad`
   resolves it. `refs/bisect/*`, `refs/rewritten/*` and `refs/worktree/*` are per-worktree.
   With `reftable`, run `for-each-ref` inside each worktree (`git -C <path> …`) instead of
   `find`.

### G16 — Reflogs and recovery (routine part)

5. **Current branch reflog, last 50 entries.**

   ```sh
   git --no-replace-objects --no-pager log -g --format='%h %gd %gs' -n 50 HEAD
   ```

   Look for `reset: moving to …`, `rebase (finish)`, `commit (amend)`, `checkout` away from
   a detached commit. `[observed]` `faafec8 HEAD@{11} commit: lost commit` followed by
   `HEAD@{10} reset: moving to HEAD~1`.

6. **Commits reachable only from reflogs.**

   ```sh
   git --no-replace-objects rev-list --count --reflog --not --all
   git --no-replace-objects --no-pager log --reflog --not --all --format='%h %ci %s' | head -n 50
   ```

   `[observed]` 2: `5e272dc On main: old experiment` (stash entry 1) and `faafec8 lost
   commit` (the reset). Expiry or a `reflog expire` makes these unreachable, and `gc` then
   deletes them.

7. **Stash entries live in a reflog.** `git --no-pager log -g --format='%gd %h %gs'
   refs/stash`. Only `stash@{0}` is what `refs/stash` points at; `stash@{1}` and older exist
   only as reflog entries. G8 (stashes) owns their content review.

8. **`lost-found` presence and size.**

   ```sh
   find <git-dir>/lost-found -type f 2>/dev/null | wc -l
   du -sk <git-dir>/lost-found 2>/dev/null
   ```

   Report the count and size only. The inventory is a `deep` step (16).

## Deep checks

### G15 — Classify every ref

9. **Replace refs.** For each: `git --no-replace-objects --no-pager log --no-walk
   --format='%h %s' <original> <replacement>`. State in plain words what the history shows
   instead of what exists. `[observed]` `git cat-file commit 21a4d8d` printed the
   replacement's subject; with `--no-replace-objects` it printed the real one.
10. **`refs/original`.** `git --no-replace-objects merge-base --is-ancestor
    refs/original/refs/heads/main main`. Exit 1 means the pre-rewrite history differs and is
    still pinned (G14 must scan it for secrets); exit 0 means the backup is a subset of the
    current branch and pins nothing extra (`[observed]` 0 on the fixture).
11. **Tree and blob refs.** Match a tree ref against commit trees:

    ```sh
    git --no-replace-objects --no-pager rev-list --all --no-commit-header --format='%T %H' \
      | grep '^434a172c9cc4579644dbbe30601aa54848516c92 ' | head -n 3
    ```

    `[observed]` the `refs/codex/snapshot-1` tree equals the tree of `aa2face` (and of two
    other commits): the snapshot holds nothing a branch does not. No match means unique
    content: list its paths with `git --no-pager ls-tree -r --name-only <tree> | head -n 50`
    (names only, never `cat-file -p` of blobs). Notes: `git --no-pager notes list | head`;
    `git notes prune --dry-run --verbose` lists notes on missing objects. Other bridges
    (`git-svn`, p4, imerge, branchless) are inventoried with their tool state directories in
    G12; never delete their refs while the tool is in use.

### G16 — Reflogs, census, lost-found

12. **Every reflog.** `git --no-pager reflog list` (Git ≥ 2.45; older: `find <git-dir>/logs
    -type f`). For each ref: entry count, oldest and newest date
    (`git --no-pager log -g --format='%gd %ci' <ref> | sed -n '1p;$p'`).
13. **Which reflog holds a commit.**

    ```sh
    git --no-replace-objects --no-pager log -g --all --format='%gd %h %gs' \
      | grep -E 'faafec8|5e272dc'
    ```

    `[observed]` `stash@{1} 5e272dc …`, `main@{6} faafec8 …`, `HEAD@{11} faafec8 …`.
    Pruning a remote-tracking ref deletes its reflog too `[observed]`.
14. **Unreachable census with and without reflog roots.** Snapshot refs first (contract
    order), then:

    ```sh
    git --no-replace-objects fsck --unreachable --no-progress 2>/dev/null \
      | sort > <evidence>/unreachable-with-reflogs.txt
    git --no-replace-objects fsck --unreachable --no-reflogs --no-progress 2>/dev/null \
      | sort > <evidence>/unreachable-no-reflogs.txt
    awk '{print $2}' <evidence>/unreachable-with-reflogs.txt | sort | uniq -c
    awk '{print $2}' <evidence>/unreachable-no-reflogs.txt | sort | uniq -c
    comm -13 <evidence>/unreachable-with-reflogs.txt <evidence>/unreachable-no-reflogs.txt \
      | awk '{print $2}' | sort | uniq -c
    ```

    The last line is **what reflogs protect**: it becomes unreachable when those entries
    expire. `[observed]` with reflogs 2 blob, 1 commit, 4 tree; without 4 blob, 3 commit,
    6 tree; protected only by reflogs 2 blob, 2 commit, 2 tree. Add the date range of the
    commits (`git --no-replace-objects --no-pager log --no-walk --format='%ci' <shas> | sort
    | sed -n '1p;$p'`). A cruft pack (`*.mtimes`, G17) holds unreachable objects too; `fsck`
    counts them, `count-objects` does not.
15. **Dropped stashes.** Stash commits are merges whose second parent is `index on …`:

    ```sh
    git --no-replace-objects fsck --unreachable --no-progress 2>/dev/null \
      | awk '$2=="commit"{print $3}' \
      | xargs git --no-replace-objects --no-pager log --merges --no-walk \
        --format='%H %ci parents=%p %s' | head -n 50
    ```

    `[observed]` `a2ef75e … On main: dropped`. The official git-stash recipe adds
    `--grep=WIP`, which **misses every stash pushed with `-m`** (subject `On <branch>: <msg>`)
    `[observed]`: it printed nothing here. Confirm the shape with `git --no-pager log
    --no-walk --format=%s <second-parent>` → `index on main: …`. A `WIP on` subject is not
    proof of which tool made the commit.
16. **`lost-found` inventory by name and size, never read.** For each file:

    ```sh
    find <git-dir>/lost-found -type f | head -n 200 > <evidence>/lost-found-files.txt
    git cat-file -e 0000000000000000000000000000000000000001; echo "exit=$?"
    wc -c < <git-dir>/lost-found/other/0000000000000000000000000000000000000001
    file -b <git-dir>/lost-found/other/0000000000000000000000000000000000000001
    git hash-object --stdin < <git-dir>/lost-found/other/0000000000000000000000000000000000000001
    printf '%s\n' 3655aabe14b904d965f4414ee7445c7d1d09d520 \
      | cmp -s - <git-dir>/lost-found/other/3655aabe14b904d965f4414ee7445c7d1d09d520; echo "cmp=$?"
    ```

    What `fsck --lost-found` writes `[observed]`: under `commit/` and for trees and tags under
    `other/`, the file holds only the object name plus a newline (41 bytes for SHA-1, 65 for
    SHA-256); only blobs under `other/` hold content. Classify each name:

    | Test | Verdict |
    | --- | --- |
    | `cat-file -e <name>` exit 0 | object present (the file adds nothing) |
    | exit ≠ 0, name file (`cmp` exit 0) | absent, file is only a pointer: not recoverable from it |
    | exit ≠ 0, `hash-object --stdin` equals the name | absent, file intact: recoverable blob |
    | exit ≠ 0, neither | absent, file corrupt or foreign |

    `[observed]` the planted `0000…0001`: absent, 7 bytes, `ASCII text`, hash `029e05d…` ≠
    name → foreign. Never `cat` these files: a blob may be a secret.
17. **Subjects of unreachable commits.** `git --no-replace-objects --no-pager log --no-walk
    --format='%h %ci %p %s' <shas>`; classify with D14 (patch-id, tree equality) in
    `commands/git-patch-id.md`. `[observed]` `faafec8 … lost commit`, `a2ef75e … On main:
    dropped`, `5e272dc … On main: old experiment`.
18. **Residue of earlier recoveries.** `refs/recovered/*`, `recover-*` branches, and
    `lost-found/` files older than the newest reflog entry are leftovers of a past recovery:
    report them with their dates and whether their objects are also reachable from a branch.

## Recommendations and recovery

Preservation first: pin, then back up, then (only if the user asks for reclamation) expire
and prune. Every row is an approved item with a literal command.

| Finding | Action (literal command) | Undo | Approval scope |
| --- | --- | --- | --- |
| Commit reachable only from a reflog | `git update-ref -m 'repo-hygiene R1' refs/recovered/2026-09-22/lost-commit faafec8f8fd4a95b9040be2fc2cc36f07c41a1a8 ''` | `git update-ref -d refs/recovered/2026-09-22/lost-commit faafec8f8fd4a95b9040be2fc2cc36f07c41a1a8` | that ref only |
| Stash entry below the top | `git update-ref -m 'repo-hygiene R2' refs/recovered/2026-09-22/stash-old-experiment 5e272dc99402e2589d8308170c93694abd5101dc ''` | `git update-ref -d refs/recovered/2026-09-22/stash-old-experiment 5e272dc99402e2589d8308170c93694abd5101dc` | the pin; no `stash pop/apply/drop` |
| Dropped stash | `git update-ref -m 'repo-hygiene R3' refs/recovered/2026-09-22/stash-dropped a2ef75e201393ea2805d8118effd2f68961416d8 ''` | `git update-ref -d refs/recovered/2026-09-22/stash-dropped a2ef75e201393ea2805d8118effd2f68961416d8` | the pin |
| Backup before any destructive item | `git bundle create /Users/<user>/repo-hygiene-backup/<repo>-20260922.bundle --all` then `git bundle verify <same-path>` | delete the file | writes outside the repo only |
| Recoverable blob in lost-found | `git hash-object -w <git-dir>/lost-found/other/<name>` then pin it | `git update-ref -d <pin>` | that object |
| Replace ref no one wants | `git replace -d 21a4d8dfeaeb702fe8644b81b2cabfe6f44f896e` | `git replace 21a4d8dfeaeb702fe8644b81b2cabfe6f44f896e 0b5d6e58937c6e0e036f6264f646538f4c55474d` | that replace ref |
| `refs/original` backup, proven subset | `git update-ref -d refs/original/refs/heads/main ffde723590f64a1f0f1cfa5bf5693f110d4c3836` | `git update-ref refs/original/refs/heads/main ffde723590f64a1f0f1cfa5bf5693f110d4c3836` | that ref |
| Tool ref whose tree matches a commit | `git update-ref -d refs/codex/snapshot-1 434a172c9cc4579644dbbe30601aa54848516c92` | `git update-ref refs/codex/snapshot-1 434a172c9cc4579644dbbe30601aa54848516c92` | that ref; tool not running |
| Abandoned bisect | `git bisect reset` (G2 owns it) | irreversible for the bisect state; refs are recorded first | bisect state of that worktree |
| lost-found residue fully inventoried | `rm -r <git-dir>/lost-found` | irreversible | the directory, after step 16 is saved |

Pins:

- The trailing `''` makes `update-ref` refuse to overwrite an existing ref: `[observed]`
  a second run failed with "reference already exists", exit 128.
- A pin under `refs/recovered/` gets no reflog by default (`core.logAllRefUpdates` covers
  heads, remotes, notes and HEAD) `[observed]`; add `--create-reflog` to keep one.
- A pinned object is reachable: `fsck --no-reflogs` no longer lists it `[observed]`.

**Bundle limit.** `git bundle create <outside> --all` records every ref (`[observed]` it also
listed `worktrees/<id>/HEAD` and the tree ref), but **not reflogs and not unreachable
objects**. `[observed]` restored with `git fetch <bundle> 'refs/*:refs/*'` into an empty bare
repository: the top stash was present; `stash@{1}`, the reset-away commit and the dropped
stash were absent, and there were no reflogs. Pin first, then bundle. A copy of `.git` made
with `cp -R` keeps absolute worktree paths that still point at the original checkouts
`[observed]`; the restore test must say which it used.

**Reclamation (deep, only on request).** `git reflog expire --expire=now
--expire-unreachable=now --all` followed by `git gc --prune=now` is irreversible and runs
only as approved items after a restore-tested backup, with no other Git process running.
`[observed]` the expire alone emptied `git stash list` (0 entries) although `refs/stash`
still existed, and made both lower stash entries unreachable. Preview first:
`git reflog expire --dry-run --verbose --expire=now --expire-unreachable=now --all` prints
`would prune …` per entry `[observed]` (without `--verbose` it prints nothing). The runbook
and the concurrency warning are in `areas/object-store.md`.

## Pro Git 10.7, corrected

The book's recovery procedure
(https://git-scm.com/book/en/v2/Git-Internals-Maintenance-and-Data-Recovery):

1. `git reflog` / `git log -g` to find the lost SHA. Correct; add `--no-replace-objects`.
2. `git branch recover-branch <sha>`. Prefer a pin under `refs/recovered/` (step above): it
   does not show up as a branch, cannot be pushed by `push --all`, and is create-only.
3. Not in the reflog: `git fsck --full`, read `dangling commit <sha>`. Correct, but
   `dangling` shows only tips; use `--unreachable` for the census, with and without
   `--no-reflogs`.
4. The book simulates loss with `rm -Rf .git/logs/`. Never do that in an audit.
5. The removal procedure (`filter-branch`, `rm -Rf .git/refs/original`, `rm -Rf .git/logs/`,
   `gc`) is superseded: git-filter-branch "is not recommended" `[doc]`; use `git
   filter-repo` (G14). Remove `refs/original` through Git:
   `git for-each-ref --format='delete %(refname)' refs/original | git update-ref --stdin`,
   never with `rm`.

## False positives in this area

| It looks like | It is not proof of |
| --- | --- |
| `dangling`/`unreachable` in `fsck --no-reflogs` | Lost: stash entries below the top show up here `[observed]` |
| Unreachable object | Garbage |
| A `lost-found` file name | A recoverable object |
| Empty `git stash list` | No stash commits (`refs/stash` may exist; entries may be unreachable) |
| `garbage: 0`, `count: 0` in `count-objects` | Nothing unreachable (cruft packs) |
| No `refs/replace` in `for-each-ref` of this worktree | No per-worktree refs elsewhere |
| A bundle of `--all` | A full backup (no reflogs, no unreachable objects) |
| `WIP on …` subject | Proof of the tool that made it |

## Version floors

| Feature | Floor | Fallback |
| --- | --- | --- |
| `for-each-ref --include-root-refs` | 2.45 `[doc]` RelNotes | `ls <git-dir>` for `*_HEAD` files |
| `git reflog list` | 2.45 `[doc]` RelNotes | `find <git-dir>/logs -type f` |
| `git reflog drop` | 2.50 `[doc]` RelNotes | `git reflog delete` per entry |
| `rev-parse --show-ref-format` | 2.45 | assume `files` if `refs/` and `packed-refs` exist |
| `rev-list --no-commit-header` | 2.33 | filter `^commit ` lines |
| `fsck --references` (runs `git refs verify`) | on by default in 2.55 `[doc]`; first release not verified | none |

## Sources

- `commands/git-reflog.md`, `commands/git-fsck.md`, `commands/git-cat-file.md`,
  `commands/git-update-ref.md`, `commands/git-replace.md`, `commands/git-notes.md`,
  `commands/git-bundle.md`, `commands/git-rev-list.md`, `commands/git-for-each-ref.md`,
  `commands/git-show-ref.md`, `commands/git-symbolic-ref.md`, `areas/object-store.md`.
- https://git-scm.com/docs/git-fsck, https://git-scm.com/docs/git-reflog,
  https://git-scm.com/docs/git-stash#_examples, https://git-scm.com/docs/git-bundle,
  https://git-scm.com/docs/git-replace, https://git-scm.com/docs/gitrepository-layout,
  https://git-scm.com/book/en/v2/Git-Internals-Maintenance-and-Data-Recovery
