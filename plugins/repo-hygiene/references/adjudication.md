# Adjudication methods

`deep` resolves what it finds; it does not only count it. Apply a fixed, read-only method to
each class of evidence, and give every item one verdict with its confidence. Report how many
items were adjudicated out of the total. Unadjudicated items stay listed with the reason.

Large classes go to the read-only agents in batches:

- `thread-adjudicator` takes review threads.
- `candidate-classifier` takes objects, stash paths, branches and lost-found entries.

The main thread reviews every verdict before it enters a recommendation.

Every walk and count here uses `--no-replace-objects` (`audit-contract.md`, section 2).
Methods that write objects (`merge-tree --write-tree`, `commit-tree`) run only after the
unreachable census has been saved.

## Contents

1. Review threads
2. Unreachable commits
3. lost-found entries
4. Stash divergence
5. Branches and PR heads
6. Budgets

## 1. Review threads

Input comes from the provider (`provider.md`, P3): the thread ID, `path`, `line` or
`originalLine`, the first comment's `originalCommit.oid`, and every comment body.

1. Read every comment of the thread. The claim is what the reviewer asked for, not the
   thread's title or its `isOutdated` flag.
2. Find the governing decision, if any: a later merged PR, an ADR, a decision record, or the
   PR's own reply that states an owner choice. A later decision can supersede a comment.
3. Follow the code:

   ```sh
   git --no-replace-objects log --format='%h %ad %s' --date=short \
     -L<start>,<end>:<path> <originalCommit>..HEAD --
   ```

   - If the file moved: `git --no-replace-objects log --follow -M --format='%h %s' -- <path>`.
   - If `log -L` cannot follow, run
     `git --no-pager blame -C -C -M --ignore-revs-file=<file-if-present> -- <current-path>`
     on the current file.
   - If the path no longer exists at `HEAD`, state that plainly. A removed path is not by
     itself a disposition.
4. Reproduce the claim with the project's own runners when it is behavioral. Find them in
   CLAUDE.md, AGENTS.md, `package.json` scripts, `Makefile`, `pyproject.toml` or
   `justfile`. When the claim is textual (a comment, a doc, a citation), exact-file evidence
   is enough. Never read a secret-shaped file or a path the project protects.
5. Give one verdict:

   | Verdict | Meaning | Evidence required |
   | --- | --- | --- |
   | fixed previously | Current code no longer has the defect | Commit that changed it, plus a passing check or exact file lines |
   | fixed in this work | The program fixed it (see `program/execution.md`) | Red run, fix commit, green run, negative control |
   | superseded | A later decision replaced the request | The decision and its location |
   | false positive | The claim was wrong when made | The contradicting file lines or run |
   | accepted trade-off | The owner chose to keep it | The owner's recorded choice |
   | still present | The defect reproduces now | The failing run or exact lines |
   | blocked | Cannot be decided | The reason: protected path, missing runner, missing authority |

6. Write the reply draft. It states the verdict, the evidence and the commit. It never
   claims a fix that did not happen.

Confidence levels:

- `proven`: reproduced, or exact lines.
- `likely`: code changed after the thread, but nothing was run.
- `unknown`.

## 2. Unreachable commits

Input is the census `git fsck --full --strict --unreachable --no-reflogs`, commits only,
saved to the evidence package.

1. Group commits by tree. `git rev-parse <c>^{tree}` for each, and count the distinct
   trees.
2. **Tree identical to a reachable commit.** Build the set of trees on reachable history
   once:

   ```sh
   git --no-replace-objects rev-list --all --format=%T | grep -v '^commit' | sort -u > reachable-trees.txt
   ```

   A commit whose tree is in the set is *tree identical to a reachable commit*. Name one such
   commit (`git --no-replace-objects log --all --format='%H %T' | grep <tree> | head -1`).
3. **Patch already in a reachable branch.**
   `git --no-pager show <c> | git patch-id --stable` gives the patch ID. Compare it with
   the patch IDs of reachable commits in the same date window
   (`git --no-replace-objects log --all --since=<c-date-minus-30d> --until=<c-date-plus-90d> -p | git patch-id --stable`).
4. **Stash-shaped pairs.** Subjects `WIP on <branch>: …` and `index on <branch>: …` are one
   stash. Compare them as a unit: the WIP commit's tree against the branch's later trees,
   per file. A subject never proves which tool made the commit.
5. Anything left is **unique content**. List its files and sizes
   (`git --no-pager show --stat --format='%h %ad %s' <c>`), never file contents.

| Verdict | Exit condition (safe to reclaim when) |
| --- | --- |
| tree identical to (commit) | The named commit stays reachable |
| patch in reachable branch (commit) | Same |
| WIP whose content landed | Every file's saved version equals a reachable version |
| unique content | The owner discards it, or it is recovered to a ref, **and** a restore-tested backup holds it |

## 3. lost-found entries

`.git/lost-found/` is left by an earlier `git fsck --lost-found`. Its file names are object
IDs.

1. `git cat-file -e <name>` answers whether the object is still in the store.
2. Only blobs keep content. `fsck --lost-found` writes a blob's content under `other/`, but
   writes just the object name and a newline (41 bytes) for trees under `other/` and for
   every file under `commit/` (`[observed]`). Check which kind a file is by size:
   `wc -c <file>`. For a 41-byte file, compare its first line with its name.
3. For a blob file, verify it read-only, without writing an object:

   ```sh
   git hash-object --no-filters --stdin < .git/lost-found/other/<name>
   ```

   A matching ID means *intact and recoverable*.
4. Fingerprint without printing: `wc -c`, `file -b`. Never `cat`.
5. A name-only file (a tree or commit marker) is recoverable only if the object itself and,
   for a commit, its tree and parents still exist (`git cat-file -e <name>^{tree}`).

| Verdict | Meaning |
| --- | --- |
| object present | The store still has it; the file is a duplicate record |
| absent, file intact and recoverable | `hash-object` matches; `git hash-object -w` would restore it (an approved item) |
| absent, file corrupt | Content does not hash to its name |
| marker without objects | A commit marker whose tree or parents are gone |

## 4. Stash divergence

For stash `S` with base `B = S^1`, the untracked part `S^3` (if it exists), and the default
branch `M`:

1. List the paths: `git --no-pager diff --name-only B S`, plus
   `git ls-tree -r --name-only S^3` when `S^3` exists.
2. For each path, compare blob IDs: `git rev-parse S:path`, `M:path`, `B:path`.

   | Result | Verdict |
   | --- | --- |
   | `S:path` = `M:path` | identical (already in `M`) |
   | `M:path` = `B:path`, `S` differs | never landed |
   | all three differ | diverged: continue with the next step |

3. For each diverging hunk
   (`git --no-pager diff B S -- path`, read by Claude, never printed for a secret-shaped
   path), search `M`'s history after `B` for the added and removed lines:

   ```sh
   git --no-replace-objects log --format='%h %s' -G'<escaped line>' B..M -- path
   ```

   A later commit that changed the same lines, plus a decision record, gives *superseded by
   (commit, decision)*. No such commit gives *never landed*.
4. Check the index part too: `S^2` against `B`. An index equal to `B` holds nothing extra.

## 5. Branches and PR heads

For each branch or PR head `H` against the default branch `M`:

1. Ancestor: `git merge-base --is-ancestor H M`.
2. Tree identical to a historical commit of `M` since the merge base:

   ```sh
   git --no-replace-objects rev-list --format=%T $(git merge-base H M)..M
   ```

   Compare against `git rev-parse H^{tree}`.
3. Three-dot against endpoint:
   - `git diff --stat M...H` shows what `H` added since the merge base.
   - `git diff --stat H M` shows the endpoint difference.

   An empty three-dot diff with a non-empty endpoint diff means `M` moved on. It is not
   missing work.
4. Then the ladder in `areas/branches-remotes-tags.md`.

Verdicts:

- `MERGED`;
- `MERGED (provider)`;
- `MERGED (content)`;
- `identical to historical base (commit)`;
- `NEEDS REVIEW`.

## 6. Budgets

- Set the budget before starting: a count, such as 50 threads per batch, or a time. Report
  the result as `adjudicated N of M`.
- When the budget runs out, the remaining items are listed with their IDs and carried to the
  next batch or session. `deep resume` picks them up from the register.
- Never sample and extrapolate. A verdict exists per item or not at all.
