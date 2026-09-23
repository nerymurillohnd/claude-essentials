# Branches, remotes and tags

Areas: G5, G6, G7. `routine` runs the Routine checks; `deep` runs Routine and Deep.

Every recipe was run on Git 2.55.0 against the planted fixture unless it is tagged `[doc]`.
Write `<evidence>` as the evidence-package directory from `audit-contract.md` section 10.
`--no-replace-objects` is a **global** option: it goes before the subcommand
(`git --no-replace-objects rev-list …`). After the subcommand it fails: `git log
--no-replace-objects` → `fatal: unrecognized argument`, and `git for-each-ref
--no-replace-objects` → `unknown option` `[observed]`.

## Contents

1. What can go wrong
2. Routine checks (G5 1–7, G6 8–13, G7 14–17)
3. Deep checks
4. The integration ladder
5. Recommendations and recovery
6. False positives in this area
7. Version floors
8. Sources

## What can go wrong

- **G5 local branches.** A branch was merged by squash or rebase, so Git does not call it
  merged, and it lingers. A branch's upstream was deleted on the server (`[gone]`), and the
  local branch holds commits nobody pushed. A branch is checked out in another worktree or
  is being bisected or rebased, so deleting it fails or strands that checkout. Two names
  differ only by case or punctuation (`feat/merged`, `Feat/MERGED`). `branch.<b>.remote`
  names a remote that no longer exists. Counts are wrong because a replace ref is active.
- **G6 remotes.** A URL embeds a credential. `pushurl` sends pushes somewhere other than the
  fetch URL. Two remotes point at one repository. A remote is dead. Remote-tracking refs
  still show branches the server deleted. A custom refspec fetches a ref that is gone. A
  global `fetch.prune` + `fetch.pruneTags` deletes local-only tags on the next fetch.
- **G7 tags.** A lightweight tag was meant to be a release. A tag exists only locally, only
  remotely, or with a different target on each side (moved). A tag points at a commit that
  no branch contains (rewritten history). A tag is unsigned where the project signs.
  Provider releases are checked in `provider.md` (P6).

## Routine checks

Run each command as written. All are reads, except where a step says it touches the
network (`ls-remote` is a read by the contract, section 1).

### G5 — Local branches

1. **Branch inventory.** One line per branch with its upstream, tracking state, age and the
   worktree holding it:

   ```sh
   git --no-optional-locks --no-pager for-each-ref \
     --format='%(refname:short)|%(objectname:short)|%(upstream:short)|%(upstream:track)|%(committerdate:iso-strict)|%(worktreepath)' \
     refs/heads
   ```

   Look for `[gone]` in the fourth field, an empty upstream, old dates, and a path in the
   last field. `[observed]` `feat/merged|c3544d8|origin/feat/merged|[gone]|…`.
   `%(worktreepath)` also fills for the main worktree `[observed]`, although the official
   page says "linked worktree". It is **empty** for a branch being bisected or rebased,
   because HEAD is detached; step 5 covers that case.
   Plain words: the *upstream* is the server branch this local branch follows; `[gone]`
   means Git remembers following one, but it no longer exists in the local copy of the
   server's branch list.

2. **Ahead and behind the base, with replace refs off.** First pin the base (ladder step 1),
   then:

   ```sh
   git --no-replace-objects --no-pager for-each-ref \
     --format='%(refname:short) %(ahead-behind:origin/main)' refs/heads
   ```

   Git < 2.41 has no `%(ahead-behind:)`. Use, per branch:

   ```sh
   git --no-replace-objects rev-list --left-right --count origin/main...feat/squashed
   ```

   (left = only in `origin/main`, right = only in the branch). `[observed]`: with a replace
   ref active, both forms reported `main` 4 ahead; with `--no-replace-objects` it is 5.
   `%(ahead-behind:)` honors replace refs just like `rev-list`.

3. **Upstream config pointing nowhere.** `%(upstream)` is empty when `branch.<b>.remote`
   names a missing remote `[observed]`, so read the config:

   ```sh
   git --no-pager remote | sort > <evidence>/remotes.txt
   git --no-pager config --get-regexp '^branch\..*\.remote$' | awk '{print $2}' | sort -u \
     | comm -23 - <evidence>/remotes.txt | grep -v -x '\.'
   git --no-pager config --get-regexp '^branch\..*\.(remote|merge)$'
   ```

   `[observed]` the first pipeline printed `ghost` for `branch.wip/unique.remote=ghost`.
   `.` is a legal value (the upstream is a local branch), so it is excluded. A
   `branch.<b>.merge` whose ref is absent from `git ls-remote --branches <remote>` points
   nowhere on the server even when the remote exists.

4. **Case-only and near-duplicate names.**

   ```sh
   git --no-pager for-each-ref --format='%(refname:short)' refs/heads | tr 'A-Z' 'a-z' \
     | sort | uniq -d
   git --no-pager for-each-ref --format='%(refname:short)' refs/heads | sed -E 's#[-_/.]##g' \
     | tr 'A-Z' 'a-z' | sort | uniq -d
   ```

   `[observed]` on macOS (case-insensitive APFS, files ref backend): after
   `git branch Feat/Merged-copy`, the command `git branch feat/MERGED` created a ref that
   Git lists as `Feat/MERGED`, because the loose ref file landed in the existing `Feat/`
   directory. Case-only names are not portable: a clone on another OS can see a different
   set of branches.

5. **Branches that must never be deleted right now.** Beyond `%(worktreepath)`, read the
   small state files that name a branch under operation, in every worktree:

   ```sh
   git --no-optional-locks --no-pager worktree list --porcelain
   git rev-parse --git-common-dir
   find <common-dir> -maxdepth 3 \( -name BISECT_START -o -name head-name \) -print
   ```

   Then read each found file with `head -c 200 <file>` (they hold a branch name, never
   content). `[observed]` `git branch -D main` failed with "cannot delete branch 'main' used
   by worktree" while `BISECT_START` named `main` and `%(worktreepath)` was empty.

6. **Age and activity.** `--sort=-committerdate` on the inventory lists the newest first.
   Committer date is the last rewrite, not the last push; say so in the finding.

7. **Integration verdict.** Run the ladder (section 4) for every branch that is not the
   default branch. `routine` stops at the first proof per branch.

### G6 — Remotes and remote-tracking refs

8. **Remotes, redacted in the same command.**

   ```sh
   git --no-pager remote -v | sed -E 's#(://)[^/@[:space:]]+@#\1***@#g'
   git --no-pager config --get-regexp '^remote\.' | sed -E 's#(://)[^/@[:space:]]+@#\1***@#g'
   git --no-pager config --get-regexp '^remote\..*\.(url|pushurl)$' \
     | grep -c -E '://[^/@[:space:]]+@'
   ```

   A count above 0 is an **embedded credential** finding: report the remote name and
   "credential in URL", never the value. `[observed]` the fixture's `backup` remote printed
   as `https://***@example.com/r.git`. Also flag `scp`-style `user@host:` only as an
   identity, not a secret.

9. **`pushurl` different from `url`, duplicates, fork layout.**

   ```sh
   git --no-pager config --get-regexp '^remote\.[^.]+\.(url|pushurl)$' \
     | sed -E 's#(://)[^/@[:space:]]+@#\1***@#g' | sort -k 2
   git --no-pager config --get-regexp '^remote\.[^.]+\.url$' \
     | sed -E 's#(://)[^/@[:space:]]+@#\1#' | awk '{print $2}' | sort | uniq -d
   git --no-pager config --show-scope --get-regexp \
     '^(remote\.pushdefault|push\.default|branch\..*\.pushremote|remote\..*\.(tagopt|mirror|skipfetchall|prune|prunetags))$'
   ```

   `[observed]` the second command printed `../origin.git` when `origin` and `dup` shared a
   URL. A `pushurl` is legitimate in a triangular fork layout (fetch from `upstream`, push to
   your fork); it is a finding when nothing documents it or it points at a third host.
   `remote.<n>.mirror=true` makes a plain `git push` mirror every ref, deletions included.

10. **Custom or stale fetch refspecs.**

    ```sh
    git --no-pager config --get-regexp '^remote\..*\.fetch$' | awk '{n=$1;
      sub(/^remote\./,"",n); sub(/\.fetch$/,"",n);
      if ($2 != "+refs/heads/*:refs/remotes/" n "/*") print}'
    ```

    `[observed]` it printed `+refs/pull/*/head:refs/remotes/origin/pr/*` and a single-branch
    refspec. Avoid `grep -E` back-references here: some `grep` builds reject `\1` in ERE
    `[observed]`. A remote name containing a dot breaks this parse; read that one by hand.
    For each non-glob source ref, `git ls-remote <remote> <src>` returning nothing means the
    refspec is stale, and every fetch of that remote errors.

11. **Dead remotes.** Probe each remote without prompts:

    ```sh
    GIT_TERMINAL_PROMPT=0 git -c http.lowSpeedLimit=1 -c http.lowSpeedTime=15 --no-pager \
      ls-remote --branches backup 2>&1 | sed -E 's#(://)[^/@[:space:]]+@#\1***@#g' | head -n 5
    ```

    `[observed]` exit 128, "repository 'https://example.com/r.git/' not found" (Git itself
    stripped the credential from the message; keep the `sed` anyway). macOS ships no
    `timeout`; the `http.lowSpeed*` pair bounds HTTP, and for SSH remotes add
    `GIT_SSH_COMMAND='ssh -o BatchMode=yes -o ConnectTimeout=15'` only after checking that
    `core.sshCommand` is not set (it would be overridden, and it is a G12 finding). A 403,
    404 or auth failure is `blocked`, not "dead": it does not prove absence.
    `ls-remote` runs the configured credential helper and SSH command: in `deep`, only after
    the trust preflight.

12. **Stale remote-tracking refs, compared with the server.**

    ```sh
    git --no-pager ls-remote --branches origin | awk '{print "refs/remotes/origin/" substr($2, 12), $1}' \
      | sort > <evidence>/remote-branches.txt
    git --no-pager for-each-ref --format='%(refname) %(objectname)' refs/remotes/origin \
      | grep -v -x 'refs/remotes/origin/HEAD .*' | sort > <evidence>/tracking.txt
    join -a 1 -a 2 -e MISSING -o 0,1.2,2.2 <evidence>/tracking.txt <evidence>/remote-branches.txt \
      | awk '$2 != $3'
    ```

    A line `<ref> <sha> MISSING` is a stale tracking ref (deleted on the server); `MISSING
    <sha>` is a server branch never fetched; two different SHAs mean the local copy is
    behind. `--heads` still works on 2.55 but has been a deprecated synonym of `--branches`
    since Git 2.46 `[doc]`; on Git < 2.46 use `--heads`. `git remote prune --dry-run origin`
    and `git remote show origin` also list stale refs `[observed]` ("[would prune]",
    "stale (use 'git remote prune' to remove)"). Never use `git fetch --dry-run` for this:
    it downloaded the new objects into the object store `[observed]`.

13. **Prune policy in every scope.**

    ```sh
    git --no-pager config --show-scope --show-origin --get-all fetch.prune
    git --no-pager config --show-scope --show-origin --get-all fetch.pruneTags
    git --no-pager config --show-scope --get-regexp '^remote\..*\.(prune|prunetags)$'
    ```

    The dangerous combination is prune **and** pruneTags, in any scope, including
    **global**: the next `git fetch` deletes every local tag the remote does not have.
    `[observed]` on the maintainer's machine both were `global true`, and
    `git fetch --dry-run origin` announced `- [deleted] (none) -> local-only` for a local-only
    tag. With the global file masked, `fetch.pruneTags=true` alone deleted nothing; adding
    `fetch.prune=true` deleted the tracking ref only. Report it as a root cause that affects
    every repository of the user, and pair it with check 16 (local-only tags at risk).

### G7 — Tags

14. **Tag inventory with type and target.**

    ```sh
    git --no-pager for-each-ref \
      --format='%(refname:short) %(objecttype) %(objectname) %(*objecttype) %(*objectname) %(taggerdate:short)' \
      refs/tags
    ```

    `commit` in the second field is a **lightweight** tag (a bare name for a commit); `tag`
    is **annotated** (its own object with tagger, date and message) and the `*` fields give
    the peeled target. A `tree` or `blob` target is unusual and goes to G15.

15. **Signature presence without running GPG.**

    ```sh
    git --no-pager for-each-ref \
      --format='%(refname:short) %(objecttype) sig=%(if)%(contents:signature)%(then)yes%(else)no%(end)' \
      refs/tags
    ```

    `git tag -v <tag>` verifies, but it runs `gpg.program` (config-executing); use it in
    `deep` after the trust preflight. `[observed]` unsigned annotated tag: exit 1, "error: no
    signature found"; lightweight tag: "cannot verify a non-tag object of type commit".

16. **Local-only, remote-only and moved tags.**

    ```sh
    git --no-pager for-each-ref --format='%(refname) %(objectname)' refs/tags \
      | sort > <evidence>/tags-local.txt
    git --no-pager ls-remote --tags --refs origin | awk '{print $2, $1}' \
      | sort > <evidence>/tags-remote.txt
    join -a 1 -a 2 -e MISSING -o 0,1.2,2.2 <evidence>/tags-local.txt <evidence>/tags-remote.txt \
      | awk '$2 != $3'
    ```

    `--refs` drops the peeled `^{}` lines. `[observed]` output: `refs/tags/local-only <sha>
    MISSING` (local only), `refs/tags/remote-only MISSING <sha>` (remote only),
    `refs/tags/v0.3 <sha-a> <sha-b>` (moved). A moved tag means two people see different
    code under one release name.

17. **Tags on commits no branch contains.**

    ```sh
    git --no-replace-objects --no-pager log --tags --not --branches --remotes \
      --format='%h %D %s' | head -n 50
    ```

    `[observed]` a tag on a reset-away commit printed `faafec8 tag: orphan-tag lost commit`.
    Such a tag is the only thing keeping that history; it is evidence, not residue.

## Deep checks

1. **Merged-set propagation.** After the ladder, every branch whose tip is an ancestor of a
   branch already proven `MERGED` (any rung) inherits that verdict with the same rung:

   ```sh
   git --no-replace-objects --no-pager branch --format='%(refname:short)' --merged feat/squashed
   ```

   Record the chain ("`x` ⊂ `feat/squashed`, MERGED (content)").
2. **Recreated branches and rewritten tips.** Read each branch reflog:
   `git --no-pager reflog show --format='%h %gd %gs' <branch> | head -n 50`. A
   `branch: Created from …` entry that is newer than older entries of the same name, or a
   `reset:`/`rebase (finish)` entry, means the tip was rewritten; the older tips are
   recovery candidates for `refs-reflogs-recovery.md`.
3. **Remote refs nobody fetches.** Count the server's namespaces:

   ```sh
   git --no-pager ls-remote origin | awk '{print $2}' | awk -F/ '{print $1"/"$2}' | sort | uniq -c
   ```

   `refs/pull/*` (GitHub) and `refs/merge-requests/*` (GitLab) pin objects server-side;
   they are provider-owned and never deletable by the user. Report the count.
4. **Every tag against full history and releases.** Step 17 covers containment. For the
   release comparison use `provider.md` P6.
5. **Rewritten tags.** For each moved tag (step 16), compare the two targets with
   `git --no-replace-objects merge-base --is-ancestor <local> <remote>` in both directions;
   neither being an ancestor means one side was rewritten.

## The integration ladder

Git documents no squash detection (`[doc]` gitfaq: squash merges leave no merge commit), so
rungs 4 and 5 are heuristics and are labelled so. Stop at the first proof. Anything else is
`NEEDS REVIEW` and is never deleted.

1. **Pin the base.** `git rev-parse --verify --end-of-options 'origin/main^{commit}'` and
   compare with `git ls-remote --branches origin main`. `[observed]` the fixture's
   `origin/main` was `ffde723` while the server had `aa2face`: every verdict against a stale
   base can be wrong. Propose `git fetch origin` as an item, or run the ladder against the
   server SHA if its objects are present (`git cat-file -e <sha>`).
2. **Ancestor.** `git --no-replace-objects merge-base --is-ancestor feat/merged origin/main`
   → exit 0 = `MERGED`, 1 = not an ancestor, 128 = error `[doc]`. `[observed]` 0 for the
   `--no-ff` merged branch, 1 for the squashed one.
3. **Provider.** A merged PR whose head SHA contains the local tip → `MERGED (provider)`.
   Local commits past the PR head are unmerged (`provider.md` P3).
4. **Trial merge (heuristic, Git ≥ 2.38).**

   ```sh
   git --no-replace-objects merge-tree --write-tree origin/main feat/squashed
   git rev-parse 'origin/main^{tree}'
   ```

   Equal → `MERGED (content)`: merging would change nothing. Exit 1 means conflicts, which
   is never `MERGED`. `[observed]` the squashed branch gave the base tree `434a172…`; the
   unique branch gave a different tree; a conflicting branch exited 1 and listed
   `CONFLICT (content)`. **It writes objects**: `[observed]` a merge with a new result
   raised the loose count 57 → 58 and added one unreachable tree. When the result tree
   already exists, nothing is written. Run it only after the unreachable census
   (`refs-reflogs-recovery.md`), as the contract orders.
5. **Patch equivalence (corroboration only).** `git --no-replace-objects cherry origin/main
   feat/squashed`: only `-` lines corroborate. `[observed]` a two-commit branch squashed into
   one commit still shows `+ s1` and `+ s2`: `+` is not proof of missing content.
6. **`[gone]` upstream.** Proves nothing by itself. It is safe to delete only when the
   local tip equals the last known upstream tip, which proves the server had every local
   commit before the deletion. Where to find that tip:
   - the remote-tracking reflog, **while the tracking ref still exists** (the upstream is
     deleted on the server but not yet pruned): `git --no-pager reflog show --format='%H %gs'
     refs/remotes/origin/<b> | head -n 1`;
   - the provider: the head SHA of the PR for that branch;
   - nothing else. `[observed]` pruning deletes the tracking ref **and its reflog**
     (`.git/logs/refs/remotes/origin/feat/merged` was gone; `reflog show` failed with
     "unknown revision"), and the local branch's own reflog never records pushes.

   No source → `NEEDS REVIEW (gone, last upstream tip unknown)`.

Exclusions before any delete: the current branch and the default branch; branches checked
out in any worktree (check 1) or under bisect or rebase (check 5); branches with an open PR;
protected branches.

`git branch -d` vs `-D`: `-d` deletes when the branch is merged into **its upstream, or HEAD
when it has none** (`[doc]` git-branch). It is therefore not a "merged into main" check.
`[observed]` `git branch -d loc/abandoned` succeeded with "deleting branch … that has been
merged to 'refs/remotes/origin/feat/abandoned', but not yet merged to HEAD" while that
tracking ref was already stale: the next prune would have removed the last copy. Use `-d`
after rung 2, and `-D` only for `MERGED (provider|content)` with the SHA recorded.

## Recommendations and recovery

| Finding | Action (literal command) | Undo | Approval scope |
| --- | --- | --- | --- |
| Branch `MERGED` (ancestor) | `git branch -d feat/merged` | `git branch feat/merged c3544d81b8424934efec3cbbbac2402b8ff0b2a5` | that branch only |
| Branch `MERGED (content)` or `(provider)` | `git branch -D feat/squashed` | `git branch feat/squashed 65bacac9cd862bcb4a697ade1b5749096ee0c294` | that branch only; SHA recorded first |
| `NEEDS REVIEW` branch to keep | `git tag archive/wip-unique f35123d1dcf5518d29f085532fd29528b733651d` | `git tag -d archive/wip-unique` | the tag only; the branch stays |
| Stale remote-tracking refs | `git remote prune origin` | re-fetch cannot restore a server-deleted branch; record `for-each-ref refs/remotes/origin` first. Irreversible for deleted server branches | tracking refs of `origin` only |
| Stale base for the ladder | `git fetch --no-prune origin` | `git update-ref refs/remotes/origin/main <old-sha>` (old SHA from the tracking reflog) | tracking refs; downloads objects; may start auto-maintenance |
| Upstream to a missing remote | `git branch --unset-upstream wip/unique` | `git branch --set-upstream-to=<remote>/<b> wip/unique` | config of that branch |
| Embedded credential in URL | `git remote set-url backup https://example.com/r.git` (user rotates the token at the provider) | `git remote set-url backup <old-url>` (not recommended) | that remote's URL; rotation is the user's action |
| Duplicate remote | `git remote remove dup` | `git remote add dup <url>` plus its refspecs (tracking refs are lost) | that remote and its `refs/remotes/dup/*` |
| Stale custom refspec | `git config --unset remote.dup.fetch '^\+refs/heads/gone-branch:'` | `git config --add remote.dup.fetch <old>` | that one refspec |
| Global prune + pruneTags | `git config --global --unset fetch.pruneTags` | `git config --global fetch.pruneTags true` | global config; affects every repository |
| Local-only tag to publish | `git push origin refs/tags/v0.1` | `git push origin --delete refs/tags/v0.1` (others may have fetched it) | that tag; outward-facing |
| Local-only tag to drop | `git tag -d local-only` | `git tag local-only e13d5701110373cb06adec8baa1d46d26ce421e5` | that tag |
| Moved tag, server wins | `git fetch --no-prune origin '+refs/tags/v0.3:refs/tags/v0.3'` | `git tag -f v0.3 aa2faced5e538f823b8ed86bdd74d759b02cf773` | that tag |

`--no-prune` on every recommended fetch keeps a configured `fetch.prune` + `fetch.pruneTags`
from deleting refs the item did not name: `[observed]` with both set globally,
`git fetch --no-prune origin '+refs/tags/v0.3:refs/tags/v0.3'` moved `v0.3` and kept the
local-only tag. The stale-refspec row passes a value regex to `git config --unset`, which
removes only the matching line `[observed]`.

Each command above is the fixture's; write the audited repository's names and SHAs
literally. Deleting or moving a published tag affects everyone who fetched it; say so in the
risk line.

## False positives in this area

| It looks like | It is not proof of |
| --- | --- |
| `[gone]` upstream | Merged, or pushed |
| Not an ancestor of main | Unmerged (squash or rebase merge) |
| `git cherry` prints `+` | Content missing from main |
| `git branch -d` succeeded | Merged into main |
| Empty `%(worktreepath)` | Branch free to delete (bisect, rebase) |
| `%(ahead-behind)` / `rev-list --count` without `--no-replace-objects` | The real count |
| `git fetch --dry-run` | A read (it writes objects) |
| `ls-remote` 403/404/auth failure | Dead remote |
| Tag missing on the server | Unpublished on purpose; it may be a release never pushed |
| `pushurl` ≠ `url` | Misconfiguration (triangular forks use it) |
| A scaffold that "planted" a local-only tag | That the tag is local-only: a `git fetch` into the server auto-follows tags pointing into fetched history `[observed]` |

## Version floors

| Feature | Floor | Fallback |
| --- | --- | --- |
| `%(ahead-behind:<ref>)` | 2.41 | `rev-list --left-right --count A...B` |
| `merge-tree --write-tree` | 2.38 `[doc]` RelNotes | rungs 2, 3, 5 only |
| `ls-remote --branches` (`--heads` deprecated) | 2.46 `[doc]` RelNotes | `--heads` |
| `%(worktreepath)` | 2.23 era `[doc]`; exact release not verified | `git worktree list --porcelain` |
| `--end-of-options` | 2.24 | none; validate names first |
| `git show-ref --exists` | 2.43 | `git rev-parse --verify -q` |
| `--no-commit-header` (rev-list) | 2.33 | parse `commit` lines out |
| `fetch.pruneTags` | 2.17 `[doc]` RelNotes | — |

## Sources

- `commands/git-branch.md`, `commands/git-for-each-ref.md`, `commands/git-merge-base.md`,
  `commands/git-merge-tree.md`, `commands/git-cherry.md`, `commands/git-patch-id.md`,
  `commands/git-rev-list.md`, `commands/git-ls-remote.md`, `commands/git-fetch.md`,
  `commands/git-remote.md`, `commands/git-push.md`, `commands/git-tag.md`,
  `commands/git-reflog.md`, `provider.md` (P3, P6).
- https://git-scm.com/docs/git-branch, https://git-scm.com/docs/git-for-each-ref,
  https://git-scm.com/docs/git-merge-tree, https://git-scm.com/docs/git-fetch#_pruning,
  https://git-scm.com/docs/git-ls-remote, https://git-scm.com/docs/gitfaq
