# Object store and maintenance

Areas: G17. `routine` runs the Routine checks; `deep` runs Routine and Deep.

Every recipe was run on Git 2.55.0 against a copy of the planted fixture that was packed and
then seeded with store defects (a `tmp_pack_*`, a pack without `.idx`, a `.keep`, a
`gc.log`, a corrupted commit-graph, a missing blob), unless it is tagged `[doc]`. Write
`<git-dir>` as the output of `git rev-parse --git-common-dir`.

## Contents

1. What can go wrong
2. Routine checks
3. Deep checks
4. Reclamation runbook (deep, on request only)
5. Recommendations and recovery
6. False positives in this area
7. Version floors
8. Sources

## What can go wrong

- Loose objects pile up because automatic maintenance is off or keeps failing; a `gc.log`
  left by a failed background `gc --auto` makes every later `gc --auto` print the old error
  and skip its work for `gc.logExpiry` (default 1 day) `[doc]`.
- An interrupted `repack`, `fetch` or `index-pack` leaves `tmp_pack_*` or `tmp_idx_*`, or a
  `.pack` without its `.idx` (unusable, just disk).
- `.keep` files freeze packs forever; many small packs slow every command.
- `objects/info/alternates` borrows objects from another repository: if that one is pruned
  or moved, this one is corrupt.
- A stale or corrupt commit-graph or multi-pack-index gives wrong or failing history walks.
- A partial clone (promisor packs) cannot be fully verified offline.
- Maintenance is registered globally for a repository that no longer exists, or scheduled
  maintenance runs `prefetch` and writes `refs/prefetch/*`.
- `gc.*` or `maintenance.*` settings drift from defaults (for example
  `gc.pruneExpire=now`, `gc.reflogExpireUnreachable=now`) and silently destroy recovery
  windows.

Plain words: **loose** objects are one file each; **packs** are compressed bundles of
objects with an index (`.idx`); **garbage** here means files in the object directory that
Git cannot use; a **cruft pack** is a pack that holds unreachable objects until they
expire.

## Routine checks

1. **Counts and sizes.**

   ```sh
   git --no-optional-locks count-objects -v -H
   ```

   Fields `[doc]`: `count` loose objects, `size` their disk use, `in-pack`, `packs`,
   `size-pack`, `prune-packable` (loose objects also in a pack), `garbage` and
   `size-garbage` (files that are neither valid loose objects nor valid packs),
   `alternate` (one line per alternate). The warnings on stderr name each garbage file:
   `[observed]` `garbage found: …/tmp_pack_ABC123` and `no corresponding .idx: …/pack-….pack`
   with `garbage: 3`. It does **not** see a stray file at the top of `objects/` or in a
   non-hex directory `[observed]` (two such plants were not counted); the file listing in
   check 2 does.

2. **File-level listing.**

   ```sh
   ls -la <git-dir>/objects/pack <git-dir>/objects/info
   find <git-dir>/objects -maxdepth 2 \( -name 'tmp_*' -o -name '*.tmp' \) -print | head -n 50
   find <git-dir>/objects -maxdepth 1 -type f -print | head -n 20
   ```

   Read the pack directory by suffix: `.pack` + `.idx` (+ `.rev`) is a normal pack;
   `.mtimes` marks a **cruft pack** `[observed]` (gc on 2.55 wrote one holding the 7
   unreachable objects); `.keep` pins a pack; `.promisor` marks a partial-clone pack;
   `.bitmap` next to a pack or `multi-pack-index-*.bitmap` is a reachability bitmap;
   `multi-pack-index` is the MIDX; `info/commit-graphs/commit-graph-chain` is a split
   commit-graph; `info/alternates` lists borrowed object stores; `info/packs` is dumb-HTTP
   server info (G18). Report `.pack` without `.idx`, every `tmp_*`, every `.keep` with its
   age (`ls -la`), and the pack count against `gc.autoPackLimit` (default 50).

3. **Alternates.** `git rev-parse --git-path objects/info/alternates`, then, if the file
   exists, `wc -l` it and check each listed path exists (`test -d <path>`). An alternate that
   points into a directory that can be garbage-collected independently (another clone, a
   `/tmp` path) is a corruption risk.

4. **`gc.log`.** `test -f <git-dir>/gc.log && ls -la <git-dir>/gc.log && head -c 400
   <git-dir>/gc.log`. It holds Git's own warning text, not repository content.
   `[observed]` the seeded file read "There are too many unreachable loose objects; run git
   prune". While it is younger than `gc.logExpiry`, automatic gc does nothing `[doc]`.

5. **Maintenance registration and schedule.**

   ```sh
   git --no-pager config --global --get-all maintenance.repo
   git --no-pager config --show-scope --show-origin --get-regexp '^maintenance\.'
   ls ~/Library/LaunchAgents/org.git-scm.git* 2>/dev/null
   crontab -l 2>/dev/null | grep -c 'for-each-repo'
   systemctl --user list-timers 2>/dev/null | grep -c git-maintenance
   ```

   `[doc]` `git maintenance register` adds the repository to the **global**
   `maintenance.repo`, sets `maintenance.strategy=incremental` if unset, and sets
   `maintenance.auto=false` in the repository (it stays after `unregister`). The incremental
   schedule runs `prefetch` and `commit-graph` hourly, `loose-objects` and
   `incremental-repack` daily, `pack-refs` weekly, and never `gc`. Findings: a registered
   path that no longer exists; this repository registered while `maintenance.auto=false`
   but no scheduler entry exists (nothing maintains it); `refs/prefetch/*` present (G15).
   Since Git 2.54 the default strategy for manual maintenance is `geometric` `[doc]`
   RelNotes. `[observed]` the maintainer machine had no `maintenance.repo` entries.

6. **Setting drift, every scope.**

   ```sh
   git --no-pager config --show-scope --show-origin --get-regexp \
     '^(gc|maintenance|pack|repack|fsck|fetch\.writecommitgraph|core\.(commitgraph|multipackindex|repositoryformatversion)|feature\.)'
   ```

   Compare with the defaults `[doc]` git-gc: `gc.auto` 6700 (0 disables every automatic
   heuristic), `gc.autoPackLimit` 50, `gc.pruneExpire` `2.weeks.ago`, `gc.reflogExpire`
   90 days, `gc.reflogExpireUnreachable` 30 days, `gc.worktreePruneExpire` 3 months,
   `gc.logExpiry` 1 day, `gc.cruftPacks` true, `gc.writeCommitGraph` true. Values `now`
   remove the safety window; `never` keeps everything forever. `gc.recentObjectsHook` runs
   a shell command during gc (config-executing, G12). A `gc.<pattern>.reflogExpire…` entry
   (for example on `refs/stash`) overrides per ref.

## Deep checks

Run with `-c core.fsmonitor=false -c gc.auto=0 -c maintenance.auto=false` and after the
unreachable census (`areas/refs-reflogs-recovery.md`).

1. **Integrity.** On a normal repository:

   ```sh
   git --no-replace-objects fsck --full --strict --no-progress 2>&1 \
     | grep -v -E '^(dangling|unreachable) ' | head -n 100
   ```

   `--full` is the default `[doc]`; `--strict` adds the old g+w file-mode check, which old
   imported histories legitimately trip. Also runs `git refs verify` (ref database) by
   default `[doc]`. Save the full output to the evidence package. `[observed]` a deleted
   loose blob gave `broken link from tree 9b92c13… to blob e77093f…` and `missing blob
   e77093f…`. `fsck.skipList` or `fsck.<msg-id>=ignore` in config hides problems: list them
   in check 6. On a large repository (many GB or millions of objects) start with
   `git fsck --connectivity-only --no-dangling --no-progress`: it checks that every
   referenced object exists but never reads blobs, so blob corruption goes unseen `[doc]`.

2. **Packs.** For each `.idx`:

   ```sh
   git verify-pack <git-dir>/objects/pack/pack-<id>.idx; echo "exit=$?"
   git verify-pack -v <git-dir>/objects/pack/pack-<id>.idx | tail -n 4
   git verify-pack -v <git-dir>/objects/pack/pack-<id>.idx \
     | grep -E '^[0-9a-f]{40,64} (blob|tree|commit|tag)' | sort -k 3 -n -r | head -n 10
   ```

   `[observed]` exit 0 and `…pack: ok`; the third field is the object size, so the last
   pipeline lists the largest objects (3 000 000- and 2 097 152-byte blobs on the fixture);
   hand them to G14. Object overlap between two packs (a redundant pack):

   ```sh
   git show-index < <git-dir>/objects/pack/pack-<a>.idx | awk '{print $2}' \
     | sort > <evidence>/pack-a.txt
   git show-index < <git-dir>/objects/pack/pack-<b>.idx | awk '{print $2}' \
     | sort > <evidence>/pack-b.txt
   comm -12 <evidence>/pack-a.txt <evidence>/pack-b.txt | wc -l
   ```

   `git pack-redundant` is nominated for removal and prints a notice; with
   `--i-still-use-this --all` it did not finish within 120 s on the fixture `[observed]`.
   Do not use it.

3. **Commit-graph and multi-pack-index.**

   ```sh
   git commit-graph verify --no-progress; echo "exit=$?"
   git multi-pack-index verify --no-progress; echo "exit=$?"
   ```

   `[observed]` both exit 0 on a clean store; after 4 bytes were overwritten in the graph
   file, `verify` printed "commit-graph fanout values out of order" and exited 1, while
   `git -c core.commitGraph=false log` still worked. `--shallow` verifies only the tip file
   of a split chain `[doc]`.

4. **Bitmaps and promisor packs.** Bitmaps are rebuilt by repack; their presence is
   informative. For a partial clone (`extensions.partialClone` set, `.promisor` files),
   `fsck` treats missing promisor objects as expected; say "partial clone: offline
   verification incomplete" instead of reporting missing blobs.

5. **Localizing damage in history** `[doc]` git-bisect "Locate a good region of the object
   graph in a damaged repository". This **writes** `refs/bisect/*` and `BISECT_*` files
   (no checkout with `--no-checkout`), so it is an approved item, and it runs only when
   `fsck` is too slow or the user needs the last intact commit. Write the probe to a file
   outside the repository:

   ```sh
   #!/bin/sh
   GOOD=$(git for-each-ref "--format=%(objectname)" refs/bisect/good-*) &&
   git rev-list --objects BISECT_HEAD --not $GOOD >/path/outside/tmp.list &&
   git pack-objects --stdout >/dev/null </path/outside/tmp.list
   rc=$?
   test $rc = 0
   ```

   ```sh
   git --no-replace-objects bisect start --no-checkout <bad-tip> <known-good>
   git --no-replace-objects bisect run /path/outside/probe.sh
   git --no-pager for-each-ref --format='%(refname) %(objectname)' refs/bisect
   git bisect reset
   ```

   `[observed]` with blob `e77093f` deleted, `refs/bisect/bad` ended at `21a4d8d` ("big
   blob"), the commit that introduced it. The final "first bad commit" display then failed
   with "unable to start 'show'" because showing the commit needs the missing blob: read
   `refs/bisect/bad` before `reset`. The `rc=$?; test $rc = 0` lines matter: without them
   `pack-objects` exits 128, which `bisect run` treats as "abort" `[observed]`. Pass
   `--no-replace-objects` to **both** `start` and `run`: `[observed]` a `run` without it
   walked the replaced history.

## Reclamation runbook (deep, on request only)

Reclaiming space destroys the recovery window. It runs only as approved deep items, in this
order, each literal:

1. **Backup with a restore test** (`areas/refs-reflogs-recovery.md`): pins under
   `refs/recovered/`, then `git bundle create <outside>/<repo>.bundle --all`, then restore
   into a scratch bare repository and compare every ref. A bundle carries no reflogs and no
   unreachable objects `[observed]`.
2. **Exclusive writer.** No IDE, agent, `git` process or scheduled maintenance may touch the
   repository: `git maintenance unregister` is not enough (it keeps the scheduler running
   `[doc]`); check with `ps -ax -o pid,command | grep -c '[g]it '` and pause the schedule.
   Why: `[doc]` git-gc NOTES — when gc runs concurrently with another process, "there is a
   risk of it deleting an object that the other process is using but hasn't created a
   reference to", which "may corrupt the repository"; the protection is the `--prune`
   grace period, and `now` removes it.
3. `git reflog expire --expire=now --expire-unreachable=now --all` — `[observed]` it also
   empties `git stash list` and makes lower stash entries unreachable. Preview with
   `--dry-run --verbose`.
4. `git gc --prune=now` — irreversible. On 2.55 unreachable objects go to a cruft pack first
   and `--prune=now` expires them.
5. Verify: `git count-objects -v -H`, `git --no-replace-objects fsck --unreachable
   --no-reflogs --no-progress | wc -l` (expect 0), `git fsck --connectivity-only`.
   `[observed]` steps 3–4 on the seeded copy: 0 unreachable, no cruft pack left, the
   `tmp_pack_*` removed, but the `.pack` without `.idx` and its `.keep` still reported as
   garbage: gc does not remove those.

Never delete files under `objects/` by hand except the proven garbage of check 1 (a
`tmp_pack_*` older than any running Git process, a `.pack` with no `.idx`).

## Recommendations and recovery

| Finding | Action (literal command) | Undo | Approval scope |
| --- | --- | --- | --- |
| `tmp_pack_*` left by a crash | `rm <git-dir>/objects/pack/tmp_pack_ABC123` | irreversible (the file was never usable) | that file; no Git process running |
| `.pack` without `.idx` | `mv <git-dir>/objects/pack/pack-dead….pack <outside>/` (quarantine) or `git index-pack <outside>/pack-dead….pack` to test it | move it back | that file |
| Stale `.keep` | `rm <git-dir>/objects/pack/pack-<id>.keep` | `touch` it again | that `.keep`; confirm no tool (e.g. a server) owns it |
| `gc.log` from a failed auto-gc | read it, fix its cause, then `rm <git-dir>/gc.log` | irreversible (content saved to evidence first) | that file |
| Corrupt commit-graph | `git commit-graph write --reachable --split=replace` | none needed (derived data) | commit-graph files |
| Corrupt MIDX | `git multi-pack-index write` (add `--bitmap` if one existed) | none needed (derived data) | MIDX files |
| Too many loose objects / packs | `git maintenance run --task=gc` or `git gc` (default grace periods) | objects younger than 2 weeks and reflog-held stay | object store; reversible only for kept objects |
| Maintenance registered for a missing path | `git config --global --unset maintenance.repo '^/old/path$'` | `git config --global --add maintenance.repo /old/path` | global config entry |
| Repo needs scheduled maintenance | `git maintenance start` | `git maintenance stop` and `git maintenance unregister` | global config + OS scheduler |
| Drifted `gc.pruneExpire=now` | `git config --unset gc.pruneExpire` | `git config gc.pruneExpire now` | that key, in its scope |
| Reclamation | runbook above | **irreversible** after step 4 | only the numbered steps approved |

## False positives in this area

| It looks like | It is not proof of |
| --- | --- |
| `count: 0`, `garbage: 0` | Nothing unreachable (a cruft pack holds it) `[observed]` |
| `garbage: 0` | A clean `objects/` (stray files outside hex dirs are not counted) `[observed]` |
| `.keep` file | Garbage (servers and tools keep packs on purpose) |
| `fsck --strict` mode warning | Corruption (old imports) |
| Missing blob in a partial clone | Corruption |
| `--connectivity-only` clean | Blobs intact |
| `git maintenance unregister` | Scheduler stopped |

## Version floors

| Feature | Floor | Fallback |
| --- | --- | --- |
| Cruft packs by default in gc | 2.41 `[doc]` RelNotes | unreachable objects stay loose |
| `maintenance` `geometric` strategy / default | 2.52 / 2.54 `[doc]` RelNotes | `incremental`, `gc` |
| `git maintenance is-needed` | 2.53 `[doc]` RelNotes | `count-objects -v` |
| `multi-pack-index verify` | 2.22 `[doc]` RelNotes | `verify-pack` per pack |
| MIDX bitmaps | 2.34 `[doc]` RelNotes | pack bitmaps |
| `commit-graph --split=replace` | present in 2.55 `[doc]`; first release not verified | delete the chain files as an item |

## Sources

- `commands/git-count-objects.md`, `commands/git-verify-pack.md`, `commands/git-fsck.md`,
  `commands/git-commit-graph.md`, `commands/git-multi-pack-index.md`, `commands/git-gc.md`,
  `commands/git-maintenance.md`, `commands/git-prune.md`, `commands/git-repack.md`,
  `commands/git-bundle.md`, `commands/git-reflog.md`, `commands/git-cat-file.md`.
- https://git-scm.com/docs/git-gc#_notes, https://git-scm.com/docs/git-maintenance,
  https://git-scm.com/docs/git-count-objects, https://git-scm.com/docs/git-fsck,
  https://git-scm.com/docs/git-bisect#_examples,
  https://git-scm.com/docs/gitrepository-layout,
  https://git-scm.com/book/en/v2/Git-Internals-Maintenance-and-Data-Recovery
