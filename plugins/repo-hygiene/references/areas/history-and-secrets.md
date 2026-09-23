# History content: secrets and size

Areas: G14. `routine` runs the Routine checks; `deep` runs Routine and Deep.

Every command below is a read unless its row says otherwise. Facts are tagged `[observed]`
(run on Git 2.55.0, macOS, on a fixture) or `[doc]` (official page, listed under Sources).
Two rules apply to every history walk in this file:

- `--no-replace-objects` is a **global** option: write `git --no-replace-objects log …`.
  `git log --no-replace-objects` and `git rev-list … --no-replace-objects` fail with
  `fatal: unrecognized argument` `[observed]`.
- Add `--no-textconv` to every `git log` that uses `-S`, `-G`, `-L` or a patch: without it,
  `git log -S/-G` ran a configured `diff.<driver>.textconv` program `[observed]`.

Never print a secret. History searches print commit and path only; findings name the
pattern class, never the value (`audit-contract.md` section 4).

## Contents

1. What can go wrong
2. Routine checks (1-5)
3. Deep checks (6-13)
4. Recommendations and recovery, with the rewrite runbook
5. False positives in this area
6. Version floors
7. Sources

## What can go wrong

- A token, key or password was committed once. Deleting the file in a later commit leaves it
  in every clone, fork, cache and pull-request ref. The only real fix is to **rotate** it
  (revoke it at the issuer); rewriting history is optional and expensive `[doc]` GitHub.
- Large blobs (file contents stored by Git) sit in history: every clone downloads them.
  GitHub warns above 50 MiB per file, blocks above 100 MiB, and recommends repositories under
  1 GB, strongly under 5 GB `[doc]` GitHub.
- Binary churn: the same binary rewritten many times multiplies the size.
- Generated files (build output, minified bundles, `node_modules`, `__pycache__`) are
  committed and conflict on every build.
- Line-ending churn: a commit that only flips CRLF/LF on whole files hides real changes from
  `blame` and review.
- Huge commits and merge-direction anomalies ("foxtrot" merges: `main` merged into a feature
  branch and then fast-forwarded, so `main`'s first-parent history goes through the feature
  branch).

## Routine checks

1. **Secret-shaped paths anywhere in history.** Paths only:

   ```sh
   git --no-replace-objects --no-pager log --all --no-textconv --format= --name-only \
     | sort -u \
     | grep -E '(^|/)(\.env[^/]*|[^/]*\.(pem|key|p12|pfx|tfvars)|id_(rsa|dsa|ecdsa|ed25519)[^/]*|credentials[^/]*|\.npmrc|\.pypirc|\.netrc|\.dev\.vars)$' \
     | grep -v -E '\.(example|sample|template)$' | head -n 50
   ```

   For each path: first and last commit that touched it
   (`git --no-replace-objects --no-pager log --all --no-textconv --format='%h %ad' --date=short -- <path>`),
   and whether it is tracked now (`git ls-files -- <path>`). Explain: "this file was saved
   in the project's history; deleting it later does not remove the old copies".

2. **Token formats in history (pickaxe).** One pass, commit and path only:

   ```sh
   git --no-replace-objects --no-pager log --all --no-textconv --extended-regexp \
     --format='%h %ad' --date=short --name-only \
     -G'(gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|(AKIA|ASIA)[A-Z0-9]{16}|AIza[0-9A-Za-z_-]{35}|xox[abposr]-[A-Za-z0-9-]{10,}|hooks\.slack\.com/services/|(sk|rk)_(live|test)_[A-Za-z0-9]{10,}|-----BEGIN [A-Z ]*PRIVATE KEY|sk-ant-[A-Za-z0-9_-]{20,}|sk-(proj-)?[A-Za-z0-9_-]{20,}|npm_[A-Za-z0-9]{36}|pypi-AgEIcHlwaS5vcmc|glpat-[A-Za-z0-9_-]{20}|SG\.[A-Za-z0-9_-]{22}\.|eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.|://[^/@[:space:]:]+:[^/@[:space:]]+@)' \
     | grep -v '^$' | head -n 60
   ```

   `[observed]` on the fixture: the planted GitHub-token-shaped string was found in two
   commits (the one that added `config.ini` and the one that removed it), path
   `config.ini`, with no line content printed. The pattern classes, loosened from the
   gitleaks default rules so near-misses still match `[doc]` gitleaks:

   | Class | Pattern (POSIX ERE) |
   | --- | --- |
   | GitHub token (classic, OAuth, app, refresh) | `gh[pousr]_[A-Za-z0-9]{20,}` |
   | GitHub fine-grained token | `github_pat_[A-Za-z0-9_]{20,}` |
   | AWS access key ID | `(AKIA\|ASIA)[A-Z0-9]{16}` |
   | Google API key | `AIza[0-9A-Za-z_-]{35}` |
   | Slack token / webhook | `xox[abposr]-…`, `hooks\.slack\.com/services/` |
   | Stripe secret / restricted key | `(sk\|rk)_(live\|test)_…` |
   | Private key block | `-----BEGIN [A-Z ]*PRIVATE KEY` |
   | Anthropic / OpenAI key | `sk-ant-…`, `sk-(proj-)?…` |
   | npm / PyPI / GitLab / SendGrid | `npm_…`, `pypi-AgEIcHlwaS5vcmc`, `glpat-…`, `SG\.…\.` |
   | JWT | `eyJ….eyJ….` |
   | Credentials in a URL | `://user:pass@` |

   `-G` matched ERE syntax (`{20,}`) with or without `--extended-regexp`, and the BRE form
   `\{20,\}` matched nothing `[observed]`; keep `--extended-regexp` explicit. `-G` skips
   binary files unless `--text` is given; `-S` searches binary files too `[doc]`. `--all`
   covers branches, tags, notes and `refs/stash` but not older stash entries, reflog-only
   commits or unreachable objects: `deep` adds `--reflog` and the unreachable census.

3. **Which hits are still in the current tree.**

   ```sh
   git --no-pager grep -l -I --extended-regexp -e '<same pattern as check 2>' HEAD --
   git ls-files -- config.ini | wc -l
   ```

   `[observed]`: no hit in `HEAD` and `0` tracked copies, so the fixture secret lives only in
   history. Report per hit: commit, path, pattern class, `in current tree: yes/no`, and
   which refs contain the commit:

   ```sh
   git --no-pager for-each-ref --contains <commit> --format='%(refname)' | head -n 30
   ```

   `[observed]`: the fixture commit was contained in `refs/heads/main`, `refs/tags/v0.2`,
   `refs/stash`, `refs/bisect/*` and `refs/replace/*`: every one of them keeps it alive.

4. **Large blobs reachable from branches and tags.**

   ```sh
   git --no-replace-objects rev-list --objects --branches --tags \
     | git --no-replace-objects cat-file \
         --batch-check='%(objecttype) %(objectname) %(objectsize) %(objectsize:disk) %(rest)' \
     | awk '$1=="blob" && $3>=1048576' | sort -k3,3nr | head -n 20
   ```

   `[observed]`: `blob d71cf43… 2097152 2097811 blob.dat`. Use `%(objectname)`:
   `%(objectname:short)` fails with `fatal: bad cat-file format` `[observed]`. `%(rest)` is
   the first path the walk met for that blob, not every path. Thresholds to report: over
   50 MiB (GitHub warns), over 100 MiB (GitHub blocks), and anything over 1 MiB that is not
   source.

5. **Total history size.**

   ```sh
   git --no-replace-objects rev-list --disk-usage=human --objects --all
   git --no-replace-objects rev-list --disk-usage=human --objects --branches --tags
   git count-objects -v -H
   ```

   `[observed]`: `2.02 MiB` for `--all` vs `2.00 MiB` for branches and tags: the difference
   is what stashes, notes and other refs keep. Compare with GitHub's 1 GB / 5 GB guidance.

## Deep checks

6. **Largest blobs across all history, including stashes and reflogs.**

   ```sh
   git --no-replace-objects rev-list --objects --all --reflog \
     | git --no-replace-objects cat-file \
         --batch-check='%(objecttype) %(objectname) %(objectsize) %(objectsize:disk) %(rest)' \
     | awk '$1=="blob" && $3>=1048576' | sort -k3,3nr | head -n 50
   ```

   `[observed]`: `big.bin` (3 072 000 bytes, 13 433 on disk) appeared only through
   `refs/stash`, `blob.dat` (2 097 152 bytes) through `main`. For each large blob, find the
   commits that added and removed it:

   ```sh
   git --no-replace-objects --no-pager log --all --no-textconv \
     --find-object=d71cf43961df814dc010963df1d3489f95850b12 \
     --format='%h %ad %s' --date=short --name-status
   ```

   `[observed]`: `A blob.dat` in `a9f3391 big blob`, `D blob.dat` in `c987a3d rm blob`.
   Unreachable large blobs come from the census in `areas/refs-reflogs-recovery.md`.

7. **Binary churn.** Paths Git treats as binary, by number of commits that changed them:

   ```sh
   git --no-replace-objects --no-pager log --all --no-textconv --numstat --format= \
     | grep -E '^-[[:blank:]]+-[[:blank:]]' | cut -f3 | sort | uniq -c | sort -rn | head -n 20
   ```

   `[observed]`: `2 blob.dat`, `1 big.bin`. Recommend Git LFS or release assets for paths
   with many versions.

8. **Generated files tracked now, and marked generated.**

   ```sh
   git --no-pager ls-files \
     | grep -c -E '(^|/)(dist|build|out|target|coverage|node_modules|vendor|__pycache__|\.next|\.nuxt|\.venv)/|\.(min\.js|min\.css|map|pyc|class|o|so|dylib|dll|exe|jar|war)$'
   git --no-pager ls-files -z | git check-attr --stdin -z linguist-generated \
     | tr '\0' '\n' | paste - - - | awk -F'\t' '$3=="set" || $3=="true"' | head -n 20
   ```

   Then list up to 20 paths with the first command's pattern and `head -n 20`. A vendored
   directory can be intentional: check README, CI and `.gitattributes` before calling it
   junk. History of when they entered: `git --no-replace-objects --no-pager log --all
   --no-textconv --diff-filter=A --format='%h %ad' --date=short --name-only -- 'dist/*'`.

9. **Line-ending churn.** Commits whose changes vanish when CR at end of line is ignored
   (two passes, compared by `comm`; files go to the evidence package):

   ```sh
   git --no-replace-objects --no-pager log --all --no-textconv --format='@%h' --numstat \
     | awk '/^@/{c=$0;next} NF==3{print c" "$3}' | sort > <evidence>/eol-all.txt
   git --no-replace-objects --no-pager log --all --no-textconv --ignore-cr-at-eol \
     --format='@%h' --numstat \
     | awk '/^@/{c=$0;next} NF==3{print c" "$3}' | sort > <evidence>/eol-nocr.txt
   comm -23 <evidence>/eol-all.txt <evidence>/eol-nocr.txt | head -n 20
   ```

   `[observed]`: an "eol only" commit showed `2 2 crlf.txt` normally and no entry with
   `--ignore-cr-at-eol`, so `comm` printed `@34958e3 crlf.txt`. Root cause is usually a
   missing `* text=auto` in `.gitattributes` or mixed `core.autocrlf` (see
   `areas/worktree-index-rules.md`). Suggest listing such commits in `.git-blame-ignore-revs`
   (`areas/tracing.md`).

10. **Huge commits.**

    ```sh
    git --no-replace-objects --no-pager log --all --no-textconv --format='@%h %s' --shortstat \
      | awk '/^@/{c=$0} /changed/{print $1, c}' | sort -rn | head -n 20
    ```

    `[observed]` prints `<files changed> @<sha> <subject>`, largest first.

11. **Merge-direction anomalies.**

    ```sh
    git --no-replace-objects --no-pager log --first-parent --merges --format='%h %s' main \
      | grep -E "Merge (remote-tracking )?branch '(origin/)?(main|master)'" | head -n 20
    ```

    `[observed]`: after merging `main` into `feat2` and fast-forwarding `main` to it,
    `main`'s first-parent log showed `Merge branch 'main' into feat2`: the old `main` commit
    became a second parent. Explain: "the main line of history now runs through a feature
    branch, so `--first-parent` views and bisects on `main` are misleading".

12. **Scanners, only when installed** (`command -v gitleaks trufflehog git-secrets`). Never
    install one. None was installed on the verification machine: this check is `[doc]` only.
    gitleaks and trufflehog read history through `git log -p` (not verified here), which runs
    textconv drivers: run them only after `areas/config-links-identity.md` check 7 shows no `diff.*.textconv`, or
    inside a `git clone --no-local` copy (config does not travel with a clone).
    - gitleaks ≥ 8.19 `[doc]`, then print only rule, commit, file and line. Exit code 1 means
      leaks or an error `[doc]`. A tracked `.gitleaks.toml` or `.gitleaksignore` in the
      target changes the rules: report its presence.

      ```sh
      gitleaks git --redact --no-banner --report-format=json \
        --report-path=<evidence>/gitleaks.json .
      jq -r '.[] | [.RuleID, .Commit[0:12], .File, .StartLine] | @tsv' \
        <evidence>/gitleaks.json | head -n 50
      ```

    - trufflehog has **no redaction flag**; its default output prints `Raw result` `[doc]`.
      Run it only as JSON piped straight into a filter that drops the secret; without `jq`,
      do not run it:

      ```sh
      trufflehog git file://. --no-verification --no-update --json 2>/dev/null \
        | jq -r '[.DetectorName, .SourceMetadata.Data.Git.commit[0:12],
                  .SourceMetadata.Data.Git.file, .SourceMetadata.Data.Git.line] | @tsv' \
        | head -n 50
      ```

    - git-secrets: `git secrets --scan-history` prints matching lines in `git grep` form
      (`<commit>:<path>:<line>:<text>`, not verified here); pipe it through
      `cut -d: -f1,2 | sort -u | head -n 50` in the same command so only commit and path
      remain.
    - git-sizer (`git-sizer --verbose`) and `git filter-repo --analyze` for size; `--analyze`
      writes `.git/filter-repo/analysis/` (writes-local-state; see
      `commands/git-filter-repo.md`).

13. **Signed history.** Before any rewrite, count signed commits and tags (they lose their
    signatures):

    ```sh
    git --no-replace-objects rev-list --all --header | tr '\0' '\n' | grep -c -E '^gpgsig'
    git --no-pager for-each-ref refs/tags --format='%(objecttype) %(contents:signature)' \
      | grep -c 'BEGIN'
    ```

## Recommendations and recovery

| Finding | Action (literal command) | Undo | Approval scope |
| --- | --- | --- | --- |
| Live secret in history | **Rotate or revoke it at the issuer first** (outside Git; the user does it) | irreversible (the old secret stops working) | Not a Git item; record who rotated and when |
| Secret still in the current tree | `git rm --cached -- config.ini`, add it to `.gitignore`, commit | `git revert <commit>` | Index, `.gitignore`, one commit; history untouched |
| Large file in the current tree | Move it to Git LFS or a release asset; `git rm --cached -- blob.dat` and commit | `git revert <commit>` | One path and one commit |
| Generated files tracked | `git rm -r --cached -- dist` plus an ignore rule, commit | `git revert <commit>` | Named paths and one commit |
| EOL churn commits | Add them to `.git-blame-ignore-revs` and commit | `git revert <commit>` | One tracked file |
| Secret or size in history after rotation | The rewrite runbook below, as separate items | irreversible once pushed | Each step is its own item |

### Rewrite runbook (secrets and size)

Each numbered step is its own approved item, in this order. A rejected step stops every
step after it. Destructive steps follow a verified backup (`audit-contract.md` section 8).

1. **Rotate first.** The user revokes or rotates every exposed credential. GitHub and
   git-filter-repo both say rotation may make the rewrite unnecessary `[doc]`. Stop here if
   the user chooses rotation only.
2. **Freeze and coordinate.** Ask collaborators to stop pushing; merge or close open pull
   requests (their diffs and comments are invalidated) `[doc]` GitHub.
3. **Backup** (mutates outside the repository):
   `git bundle create /absolute/outside/path/pre-rewrite.bundle --all`, then
   `git bundle verify /absolute/outside/path/pre-rewrite.bundle`. Record SHA-256 of the file.
4. **Fresh clone** for the rewrite, never the working repository:
   `git clone --no-local /absolute/path/to/repo /absolute/outside/path/rewrite` (or
   `git clone <url> /absolute/outside/path/rewrite` from the host). filter-repo refuses a
   non-fresh clone; `--force` overrides that check and is not used here `[doc]`.
5. **Tool check:** `git filter-repo -h | grep -c -- '--sensitive-data-removal'` must print
   `1` (filter-repo ≥ 2.47 `[doc]`). `git filter-repo --version` prints a 12-hex source hash,
   not a version number `[doc]` source.
6. **Rewrite** (in the fresh clone): for whole files
   `git filter-repo --sensitive-data-removal --invert-paths --path config.ini`
   (one `--path` per old name: renames are not followed `[doc]`); for strings
   `git filter-repo --sensitive-data-removal --replace-text /absolute/outside/path/expressions.txt`;
   for size `git filter-repo --strip-blobs-bigger-than 10M` or
   `--strip-blobs-with-ids /absolute/outside/path/blob-ids.txt`. `--sensitive-data-removal`
   fetches all refs first (local-only work in that clone can be discarded) and reports
   `NOTE: First Changed Commit(s)` `[doc]`.
7. **Verify** in the rewritten clone: re-run Routine checks 1-4 with `--all`, and
   `git --no-replace-objects --no-pager log --all --no-textconv --format=%h -- config.ini`
   must print nothing.
8. **Count affected pull requests** (GitHub):
   `grep -c '^refs/pull/.*/head$' .git/filter-repo/changed-refs` `[doc]`. If the number is
   larger than expected, discard the clone; after the push the rewrite is irreversible.
9. **Force-push the mirror** (network, irreversible): `git push --force --mirror origin`.
   Pushes to `refs/pull/*` fail because GitHub makes them read-only; any other failure is
   usually branch protection, which the owner lifts temporarily and restores `[doc]`.
10. **Host-side purge (GitHub):** the owner contacts GitHub Support with the repository name,
    the affected PR count and the First Changed Commit(s) (and orphaned LFS objects, if
    reported). Support removes cached views and PR refs and runs server GC, only when
    rotation cannot mitigate the risk `[doc]`.
11. **Other copies:** collaborators re-clone, or delete all tags, `git fetch --prune --tags`,
    **rebase (never merge)** their branches onto the new history, then
    `git reflog expire --expire=now --all` and `git gc --prune=now`, and confirm
    `git cat-file -t <first-changed-commit>` fails `[doc]`. Forks keep the data; the fork
    owners must act (GitHub cannot give their contacts) `[doc]`. Local copies found by G22
    (`areas/footprints-and-references.md`) are listed for the user.
12. **Afterwards:** every commit and tag signature from the rewritten range is gone
    (filter-repo strips them, including commits before the secret) `[doc]`; CI, deploy
    pins and links to old SHAs break. Add push protection or a pre-commit scanner.

## False positives in this area

| It looks like | It is not proof of |
| --- | --- |
| A pickaxe hit | A live secret: test fixtures, documentation examples and revoked tokens match too; the user confirms, Claude never tests a token |
| No pickaxe hit | No secret: `-G` skips binary files, `--all` misses reflog-only and unreachable commits, and formats outside the table exist |
| The file was deleted in a later commit | The secret is gone |
| `.env.example` in history | A secret file (it is excluded on purpose) |
| A large blob via `--all` | A large blob on a branch: it may be kept only by a stash (`big.bin`) `[observed]` |
| `%(rest)` path of a blob | Every path that blob had |
| A tracked `dist/` or `vendor/` | Junk: some projects publish from it on purpose |
| A foxtrot merge subject | A foxtrot merge: confirm with `--first-parent` that the merge is on the main line |

## Version floors

| Feature | Floor |
| --- | --- |
| `rev-list --disk-usage` | 2.31 `[doc]` RelNotes 2.31.0 |
| `log --find-object` | 2.17 `[doc]` RelNotes 2.17.0 |
| `--ignore-cr-at-eol`, `cat-file %(objectsize:disk)` | present in 2.55 `[observed]`; floor not verified |
| git-filter-repo `--sensitive-data-removal` | filter-repo 2.47 (latest release v2.47.0) `[doc]` |
| git-filter-repo itself | Git ≥ 2.36.0, Python ≥ 3.6 `[doc]` README |
| gitleaks `git` subcommand | gitleaks 8.19 (`detect`/`protect` deprecated) `[doc]` |

## Sources

- https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository
- https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github
- https://github.com/newren/git-filter-repo (README, INSTALL.md, `Documentation/git-filter-repo.txt`:
  sections Sensitive Data Removal, FRESH CLONE SAFETY CHECK, OUTPUT)
- https://git-scm.com/docs/git-log (`-S`, `-G`, `--find-object`, `--textconv`),
  https://git-scm.com/docs/gitdiffcore (pickaxe)
- https://git-scm.com/docs/git-rev-list (`--disk-usage`), https://git-scm.com/docs/git-cat-file
- https://github.com/gitleaks/gitleaks (README, `config/gitleaks.toml`)
- https://github.com/trufflesecurity/trufflehog (README: flags, exit codes)
- https://github.com/awslabs/git-secrets, https://github.com/github/git-sizer
- Corpus: `commands/git-log.md`, `commands/git-grep.md`, `commands/git-filter-repo.md`,
  `commands/git-filter-branch.md`, `commands/git-fast-export.md`, `commands/git-lfs.md`,
  `commands/git-hash-object.md`
