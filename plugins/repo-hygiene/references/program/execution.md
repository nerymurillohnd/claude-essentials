# Program execution

`/repo-hygiene:deep execute <S-IDs>` runs approved operations from a plan package, and
`/repo-hygiene:deep resume` continues an open program. Mutations are sequential in the main
conversation. Read-only analysis may fan out to the plugin's agents.

## Contents

1. Authorization boundary
2. Execution records
3. Evidence package
4. Backup and restore test
5. Disposition ledger
6. Integrating preserved histories
7. Fixing defects that reproduce
8. Resume
9. Single writer

## 1. Authorization boundary

- Quote the user's approval **verbatim** at the top of the first execution record, with the
  operation IDs, scope and retention choice.
- Execute only the approved IDs and their prerequisites. Anything new found during
  execution is recorded and planned. It is never done on the spot.
- The project's own rules still apply in full: CLAUDE.md, AGENTS.md, protected paths, hooks,
  required checks, and PR and merge policy. When one of them conflicts with an operation,
  stop and ask. Never weaken it.

## 2. Execution records

Write one dated record per session or batch, in the plan's location:

```markdown
> **Execution amendment — <date>:** <only when a later fact changes this record>

# <Program name> — execution record <n>

**Status:** active | implemented-local | done
**Current authority:** <approved IDs quoted from the user; current Git and provider state>
**Verification:** <what was run in this batch>
**Open risks:** <what remains, one line each>

## Authorization and boundary
## <One section per operation run: preconditions re-checked, commands, outputs, results>
## Receipts
<provider mutations: ID, URL, re-read value>
## Counters
<e.g. "review threads closed: 57 of 319 starting; 262 unresolved at the last full refresh">
## Completion status
<what is done, what is not; never "complete" for a partial program>
```

Records never contain secret values. Raw logs stay in the evidence package; records cite
them by file name.

## 3. Evidence package

- Location: the user's named backup location, or `${TMPDIR:-/tmp}/repo-hygiene/<repo>-<UTC>/`.
  Create it with `mkdir -m 700`.
- It holds command outputs with their exit codes, provider receipts as JSON, test logs,
  patches kept before cleanup, and before/after captures.
- List its contents at the end of each execution record.

## 4. Backup and restore test

Before any destructive operation, take a backup and prove it restores. A checksum alone is
not recovery.

1. Quiesce: no active Git operation, and no other writer (section 9).
2. Take the before snapshot:

   ```sh
   git for-each-ref --format='%(refname) %(objectname)' > <pkg>/refs-before.txt
   git --no-replace-objects fsck --full --strict --unreachable > <pkg>/fsck-before.txt 2>&1
   git --no-replace-objects fsck --full --strict --unreachable --no-reflogs > <pkg>/fsck-before-noreflogs.txt 2>&1
   ```

3. Archive, from the repository root:

   ```sh
   (umask 077; tar -czf <pkg>/git-before.tar.gz .git)
   ```

   Archive untracked authored files separately, by an explicit path list; never secret files.
4. Record the hash: `shasum -a 256 <pkg>/git-before.tar.gz` (or `sha256sum`).
5. Restore into an isolated temporary directory. Run no hooks and no checkout:

   ```sh
   mkdir -m 700 <pkg>/restore-test && tar -xzf <pkg>/git-before.tar.gz -C <pkg>/restore-test
   git --git-dir=<pkg>/restore-test/.git for-each-ref --format='%(refname) %(objectname)' > <pkg>/refs-restored.txt
   git --git-dir=<pkg>/restore-test/.git --no-replace-objects fsck --full --strict --unreachable > <pkg>/fsck-restored.txt 2>&1
   cmp <pkg>/refs-before.txt <pkg>/refs-restored.txt
   cmp <pkg>/fsck-before.txt <pkg>/fsck-restored.txt
   ```

6. Compare the authored files byte for byte (`cmp`).
7. Check again that the source refs did not drift during the capture.
8. Remove the restore-test directory only after every comparison passes. Keep the archive.

A `git bundle` holds named refs only, not unreachable objects. It does not replace this
backup when unreachable objects will be reclaimed.

## 5. Disposition ledger

Every candidate in `02-registers.md` ends with exactly one disposition:

| Disposition | Evidence |
| --- | --- |
| incorporated | the commit or blob in the final tree |
| already present | exact blob or tree identity |
| superseded | the governing decision (PR, ADR, record) and its location |
| discarded by owner | the owner's words and date |
| retained | the reason and the exit condition |
| blocked | the reason and what would unblock it |

Update the row, with its evidence, as each item is decided. The count of open rows is part of
every execution record.

## 6. Integrating preserved histories

When branches must disappear but their history should stay reachable:

- Merge them into one temporary branch with normal merges, one at a time. Stop before each
  merge commit, inspect the result, and resolve each conflict against the ledger.
- When the content already landed, keep the first parent's tree exactly. Show it with
  `git diff --stat HEAD^1 HEAD`, which must be empty.
- Never use `-s ours` to hide content that was not examined.
- Land through the project's normal PR lifecycle with a merge commit, so the old tips stay
  ancestors and `git branch -d` works later. If the repository allows only squash or rebase,
  revise the deletion plan instead of forcing a method.

## 7. Fixing defects that reproduce

When a review thread, stash or recovered object shows a defect that still reproduces:

1. Reproduce it with the project's own runner (red), and save the log.
2. Add a focused regression test in the owning suite.
3. Make the smallest fix, then run the test and the affected boundary (green).
4. Add a negative control: show that the test fails when the fix is reverted or the input is
   mutated. A test that cannot fail proves nothing.
5. Run the project's formatter and linter for each changed file family.
6. Commit with the project's hooks intact, and land through the normal PR lifecycle.
7. Keep the review thread open until the fix has landed.

Never change a threshold, timeout, retry count, ignore list or hook to get a pass.

## 8. Resume

`/repo-hygiene:deep resume`:

1. Find the plan package and the latest execution record: the recorded location, or search
   the project's audit and plan folders for `00-plan.md`.
2. Re-run the S01 inventory and compare it with `01-targets.md`. Report every drift: new
   refs, moved tips, new threads, changed stash.
3. Refresh the provider counts (full pagination).
4. Continue from the first open register row of the next approved operation.
5. Start a new execution record.

## 9. Single writer

Before a destructive operation, confirm no other process writes to this repository: another
agent session, an editor with Git integration, a watcher, a CI runner on the same checkout.
Stopping or pausing any of them is the user's call.

`[doc]` git-gc warns that pruning while another process writes can corrupt the repository.
This is why reclamation (S11) needs an exclusive window. If new refs appear during the window,
abort and re-plan; never retry a deletion in a race.
