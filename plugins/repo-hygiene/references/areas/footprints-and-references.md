# Footprints, third-party references and copies elsewhere

Areas: G18, G19, G22. `routine` runs the Routine checks; `deep` runs Routine and Deep.

Every command below is a read unless its row says otherwise. Facts are tagged `[observed]`
(run on Git 2.55.0, macOS, on a fixture) or `[doc]` (official page, listed under Sources).
Write history walks as `git --no-replace-objects <command>`: the option is global and
`git log --no-replace-objects` fails `[observed]`.

## Contents

1. What can go wrong
2. Routine checks (G18: 1-5, G19: 6-10, G22: 11-12)
3. Deep checks
4. Recommendations and recovery
5. False positives in this area
6. Version floors
7. Sources

## What can go wrong

G18, server, export and migration footprints:

- `git-daemon-export-ok` marks the repository as public to any `git daemon` serving its
  parent folder, without `--export-all` `[doc]`.
- `info/refs` and `objects/info/packs` are the catalog a "dumb" HTTP server hands out. They
  list **every** ref, including hidden ones (`refs/original`, `refs/codex/*`, notes)
  `[observed]`, and go stale when refs move.
- `description` (used by gitweb and some hooks) still holds the default text or a stale name.
- `receive.*` settings (`denyCurrentBranch`, `denyNonFastForwards`) in a non-bare repository
  show that someone pushes into this checkout.
- Migration leftovers: `.git/gitweb` (from `git instaweb`), `.git/svn/` and
  `refs/remotes/git-svn` (from `git svn`), fast-import marks files, `.git/filter-repo/`
  (a past history rewrite, with its commit map).
- `export-ignore` rules in `.gitattributes` decide what `git archive` (and hosted
  "Download ZIP") leave out; missing rules ship tests, CI files or secrets in release
  archives.

G19, third-party repository references in tracked files:

- Submodules and subtrees pin other repositories.
- Dependencies fetched straight from Git URLs (`git+https://…`, `github:o/r`, `git = "…"`)
  follow a branch or tag that can move, or a host that can disappear.
- CI steps `uses: owner/action@v4` or `@main` run whatever that tag or branch points to
  today; only a full 40-hex commit SHA is immutable `[doc]` GitHub.
- Scripts clone other repositories by hard-coded URL.

G22, copies elsewhere:

- Other clones, worktrees and checkouts of the same project: agent worktree folders
  (`.claude/worktrees`, `~/.codex/worktrees`), temporary directories, external volumes.
  They keep old history (including secrets you rewrote), unpushed work, and credentials in
  their own `.git/config`.
- Registered worktrees whose folder is gone (`prunable`).

## Routine checks

### G18

1. **Footprint files.** Presence, size and time only:

   ```sh
   bash -c 'g=$(git rev-parse --git-common-dir); for f in git-daemon-export-ok info/refs \
     objects/info/packs objects/info/http-alternates description gitweb svn filter-repo; do
     [ -e "$g/$f" ] && ls -ld "$g/$f"; done'
   ```

   `[observed]` on the fixture: `git-daemon-export-ok` (0 bytes) and `description`
   (73 bytes). A default `description` is exactly `Unnamed repository; edit this file
   'description' to name the repository.` `[observed]`; compare with
   `grep -c '^Unnamed repository' "$(git rev-parse --git-common-dir)/description"`.

2. **Server and migration config.**

   ```sh
   git --no-pager config --show-scope --show-origin --get-regexp \
     '^(receive\.|daemon\.|gitweb\.|instaweb\.|svn-remote\.|svn\.|uploadpack\.|uploadarchive\.)'
   git rev-parse --is-bare-repository
   git --no-pager for-each-ref --format='%(refname)' 'refs/remotes/git-svn' \
     'refs/remotes/svn' 'refs/remotes/p4' | head -n 20
   ```

   Finding: any `receive.*` key while `--is-bare-repository` is `false`.

3. **Is the dumb-HTTP catalog stale?** Only when `info/refs` exists. Compare it with the
   refs as they are now (the file lists peeled tags as `^{}` lines; drop them):

   ```sh
   git --no-pager for-each-ref --format='%(objectname)%09%(refname)' | sort \
     > <evidence>/refs-now.txt
   grep -v '\^{}' "$(git rev-parse --git-common-dir)/info/refs" | sort \
     | diff - <evidence>/refs-now.txt | head -n 40
   ```

   `[observed]`: after `update-server-info`, a new branch appeared only on the `>` side and
   deleted bisect refs only on the `<` side. `git gc` and `git repack` also rewrite both
   files `[observed]` (repack runs `update-server-info` unless `-n` `[doc]`): their presence
   alone does not mean anyone serves this repository.

4. **Fast-import marks and filter-repo state.**

   ```sh
   find "$(git rev-parse --git-common-dir)" -maxdepth 2 \( -name '*marks*' -o -name 'fast-import*' \) \
     2>/dev/null | head -n 20
   ls -l "$(git rev-parse --git-common-dir)/filter-repo" 2>/dev/null
   ```

   `.git/filter-repo/` with `commit-map`, `ref-map`, `already_ran`: a rewrite happened here;
   `already_ran` makes the next filter-repo run a continuation of that rewrite `[doc]`.

5. **Archive `export-ignore` coverage.** What a release archive would contain:

   ```sh
   git --no-pager ls-files -z | git check-attr --stdin -z export-ignore export-subst \
     | tr '\0' '\n' | paste - - - | awk -F'\t' '$3!="unspecified"' | head -n 40
   git archive --format=tar HEAD | tar -tf - | head -n 200
   git archive --format=tar HEAD | tar -tf - | wc -l
   ```

   `[observed]`: with `.github/ export-ignore`, `check-attr` reported `.github/w.yml` as
   `unspecified` while the archive listing left the whole folder out: a directory pattern is
   applied to the directory, not to each file. Trust the `tar -tf` listing. Use
   `--format=tar`: `tgz` and custom formats pipe through `tar.<format>.command`, a
   configured program `[doc]`. Look for tests, `.github/`, `.env*` or fixtures in the list.

### G19

6. **Submodules and subtrees.**

   ```sh
   git config --file .gitmodules --get-regexp '^submodule\..*\.(url|branch)' 2>/dev/null \
     | sed -E 's#(://)[^/@[:space:]]+@#\1***@#g'
   git --no-pager ls-files -s | awk '$1=="160000"' | head -n 50
   git --no-replace-objects --no-pager log --all --grep='^git-subtree-dir:' \
     --format='%h %(trailers:key=git-subtree-dir,valueonly) %(trailers:key=git-subtree-split,valueonly)' \
     | head -n 20
   ```

   `[observed]`: a subtree squash commit printed `ab3d976 lib 0123…4567`. Submodule state
   itself belongs to `areas/stashes-worktrees-submodules.md`; here record only the upstream.

7. **Dependencies from Git URLs.**

   ```sh
   git --no-pager grep -n -I -E \
     '(git\+(https?|ssh)://|git://|github:[[:space:]]*"?[A-Za-z0-9_.-]+/|\.git#|@ git\+|git[[:space:]]*=[[:space:]]*"|git:[[:space:]]*"|"resolved":[[:space:]]*"git)' \
     -- . | head -n 50
   git --no-pager grep -n -E '^[[:space:]]*(replace|require)[[:space:]]' -- '**/go.mod' | head -n 30
   ```

   `[observed]` hits: `package.json` (`git+https://…#v1`, `github:o/b`,
   `git+ssh://…#<40-hex>`), `pyproject.toml` (`@ git+https://…@main`), `requirements.txt`
   (`git+https://…@v1`), `Cargo.toml` (`git = "…", branch = "main"`), `Gemfile`
   (`git:` and `github:`). Classify each: pinned to a 40-hex commit, a tag, a branch, or
   nothing. Lockfiles may pin what the manifest leaves floating: check the lockfile before
   calling it unpinned. `go.mod` modules are fetched by module path, and `replace … => ../q`
   points outside the repository.

8. **CI actions and reusable workflows not pinned to a commit.**

   ```sh
   git --no-pager grep -n -E 'uses:[[:space:]]*[^[:space:]#]+@' -- '.github/workflows' '.github/actions' \
     | grep -v -E '@[0-9a-f]{40}([^0-9a-f]|$)'
   git --no-pager grep -h -o -E 'uses:[[:space:]]*[^[:space:]#]+@[^[:space:]#]+' -- '.github/workflows' \
     | sed -E 's/^uses:[[:space:]]*//' | sort | uniq -c | sort -rn | head -n 30
   ```

   `[observed]`: `actions/checkout@v4`, `someorg/act@main` and
   `org/repo/.github/workflows/r.yml@v1` were reported; `actions/setup-node@<40-hex> # v4.1.0`,
   `./local-action` and `docker://alpine:3.20` were not. Classify the ref after `@`: 40-hex
   (pinned), `v1`/`v4.1.0` (tag, movable), anything else (branch). A `docker://…@sha256:`
   digest is pinned. Other CI systems: `include:`/`project:` with `ref:` (GitLab),
   `orbs:` (CircleCI); search them the same way.

9. **Hard-coded clone and fetch URLs in scripts.**

   ```sh
   git --no-pager grep -n -I -E 'git (clone|submodule add|fetch|ls-remote|remote add)[[:space:]]+[^[:space:]]*(://|@)' \
     | sed -E 's#(://)[^/@[:space:]]+@#\1***@#g' | head -n 30
   ```

   `[observed]`: `scripts/setup.sh:1:git clone https://github.com/o/tool.git /tmp/tool`.

10. **Vendored copies of other repositories.** Nested `.git` folders and vendor trees:
    `find . -path ./.git -prune -o -name .git -print 2>/dev/null | head -n 20` (untracked
    nested repositories belong to `areas/stashes-worktrees-submodules.md`) and tracked
    `vendor/`, `third_party/`, `external/` folders from `git ls-files`.

### G22

11. **Registered worktrees.**

    ```sh
    git --no-pager worktree list --porcelain | head -n 60
    ```

    `[observed]`: the fixture listed `…/wt-gone` with `prunable gitdir file points to
    non-existent location` and `…/wt-live` on `wt/live`. Worktree state belongs to
    `areas/stashes-worktrees-submodules.md`; here record that each one is a copy.

12. **The repository's own agent worktree folders.**

    ```sh
    ls -d .claude/worktrees/* 2>/dev/null | head -n 50
    ls -d "$HOME/.codex/worktrees" 2>/dev/null
    ```

    A folder under `.claude/worktrees` that `git worktree list` does not show is an orphan
    copy. `~/.codex/worktrees` is scanned in Deep check 5 by root commit.

## Deep checks

1. **Footprint contents and consequences.** Read `description` (plain text) and list
   `.git/svn` (`find "$(git rev-parse --git-common-dir)/svn" -maxdepth 3 | head -n 40`: its
   `.rev_map.*` maps SVN revisions to commits `[doc]`). For `.git/filter-repo/`, count
   `changed-refs` and `commit-map` lines and read `first-changed-commits` (commit IDs only):
   old SHAs in issues, CI or deploys no longer exist upstream.
2. **What a daemon would expose.** With `git-daemon-export-ok` present, list refs that a
   client would see: `git --no-pager for-each-ref --format='%(refname)' | cut -d/ -f1-2 | sort | uniq -c`.
   Hidden refs (`uploadpack.hideRefs`, `transfer.hideRefs`) reduce it; check them in config.
3. **Upstream liveness and pin drift** (network read, no credentials, no prompts):

   ```sh
   git ls-remote --get-url https://github.com/actions/checkout
   GIT_TERMINAL_PROMPT=0 git -c credential.helper= ls-remote --exit-code \
     https://github.com/actions/checkout refs/tags/v4
   ```

   `[observed]` exit codes: `0` found, `2` no matching ref with `--exit-code`, `128` for a
   missing repository (`fatal: … does not appear to be a git repository`). Run `--get-url`
   first: `insteadOf` rewrites the URL `[observed]`, so the check may reach a mirror. `-c credential.helper=` stops configured helpers from running; for
   SSH URLs, `core.sshCommand` still runs. Drift: compare the pinned SHA with what the tag
   or branch resolves to now. Rate-limit and retry rules are in `audit-contract.md`
   section 11.
4. **Pinned SHA reachable upstream.** A 40-hex pin can point to a commit that only exists in
   a fork or was force-pushed away; `ls-remote` cannot prove it (it lists tips only). Mark
   it `unknown` unless the provider API confirms the commit (see `provider.md`).
5. **Bounded traversal for other copies.** Roots: `$HOME`, `${TMPDIR:-/tmp}`, `/private/tmp`
   (macOS), and a volume under `/Volumes` **only when the user names it**. Excluded unless
   the user names them: `~/Library`, `~/Desktop`, `~/Documents`, `~/Downloads`,
   `~/Pictures`, `~/Movies`, `~/Music`, `~/.Trash` (macOS privacy-protected folders; the
   repository's own CLAUDE.md rule warns that entering them triggers privacy prompts), and
   every `node_modules`. Depth limit 6.

   ```sh
   find "$HOME" -maxdepth 6 \( -path "$HOME/Library" -o -path "$HOME/Desktop" \
     -o -path "$HOME/Documents" -o -path "$HOME/Downloads" -o -path "$HOME/Pictures" \
     -o -path "$HOME/Movies" -o -path "$HOME/Music" -o -path "$HOME/.Trash" \
     -o -name node_modules \) -prune -o \( -name .git -o \( -type d -name '*.git' \) \) -print \
     2><evidence>/find-errors-home.txt > <evidence>/git-dirs-home.txt
   wc -l < <evidence>/git-dirs-home.txt
   wc -l < <evidence>/find-errors-home.txt
   ```

   Repeat with the temporary roots. Then match each candidate, reading config as a file
   (includes are not followed with `--file` `[doc]`) and the root commit (a commit with no
   parent, shared by every copy of a project):

   ```sh
   git --no-replace-objects rev-list --max-parents=0 HEAD
   bash -c 'while IFS= read -r g; do
     case $g in */.git) d=${g%/.git} ;; *) d=$g ;; esac
     if [ -f "$g" ]; then printf "gitfile\t%s\t%s\n" "$d" "$(head -c 300 "$g")"; continue; fi
     u=$(git config --file "$g/config" --get-regexp "^remote\..*\.url" 2>/dev/null \
       | sed -E "s#(://)[^/@[:space:]]+@#\1***@#g" | tr "\n" " ")
     r=$(git -C "$g" --no-replace-objects rev-list --max-parents=0 HEAD 2>/dev/null | tr "\n" " ")
     printf "repo\t%s\t%s\t%s\n" "$d" "$r" "$u"
   done < <evidence>/git-dirs-home.txt' > <evidence>/copies.tsv
   grep -c . <evidence>/copies.tsv
   ```

   `[observed]` on the scratch tree: a `git clone --no-local` copy and the bare remote both
   matched the fixture's root commit; the copy's `remote.origin.url` pointed at the
   fixture; a linked worktree appeared as `gitfile … gitdir: …/work/.git/worktrees/wt-live`;
   the embedded credential in a remote URL printed as `https://***@example.com/r.git`.
   Use `rev-list --max-parents=0 HEAD`, not `--all`: `--all` added the roots of
   `refs/notes/commits` and of a stash's untracked-files commit `[observed]`.
   A match by URL alone is `likely`; a match by root commit is `proven` for shared history
   (forks and templates share roots too: say so).

   Report, per the coverage rules: roots, directories visited (count of `find` output
   lines is not a visit count; say "candidates found"), errors (from the error file),
   exclusions, the matching rule, candidates that could not be recognized (for example
   `safe.directory` refusals for repositories owned by another user), and what was not
   scanned: other hosts, containers and VMs, Codespaces, cloud sync folders under
   `~/Library`, disconnected disks, and the excluded folders. A finding in an unrelated
   repository is reported as **incidental** and never acted on.
6. **What each copy holds.** For every matched copy: unpushed commits
   (`git -C <copy> --no-replace-objects rev-list --count --branches --not --remotes`),
   stash count, whether it still has history this repository rewrote (the First Changed
   Commit from `areas/history-and-secrets.md` present: `git -C <copy> cat-file -e <sha>`),
   and embedded credentials (count of `://…@` in its config). Reads only.

## Recommendations and recovery

| Finding | Action (literal command) | Undo | Approval scope |
| --- | --- | --- | --- |
| `git-daemon-export-ok` not wanted | `rm .git/git-daemon-export-ok` | `touch .git/git-daemon-export-ok` | That file |
| Stale `info/refs` exposing hidden refs, repo not served | `rm .git/info/refs .git/objects/info/packs` | `git update-server-info` | Those two files |
| Served over dumb HTTP and stale | `git update-server-info` | Restore the old files from the evidence package | Those two files |
| Default `description` on a served repository | Write the project name into `.git/description` | Restore from the evidence package | That file |
| `receive.*` in a non-bare checkout | `git config --local --unset receive.denycurrentbranch` | `git config --local receive.denyCurrentBranch updateInstead` | Named key |
| Finished git-svn migration | Archive `.git/svn` to the evidence package, then `rm -r .git/svn` and `git update-ref -d refs/remotes/git-svn` | `git update-ref refs/remotes/git-svn <sha>` from the ref snapshot; restore `.git/svn` from the archive | Named ref and folder |
| Old `.git/filter-repo/` | Move it to the evidence package | Move it back | That folder |
| Missing `export-ignore` | Add rules to `.gitattributes` and commit | `git revert <commit>` | One tracked file |
| Action pinned to a tag or branch | Replace with `owner/action@<40-hex> # vX.Y.Z` and commit | `git revert <commit>` | Named workflow files |
| Dependency from a moving Git ref | Pin to a commit or a released version and commit | `git revert <commit>` | Named manifest and lockfile |
| Prunable worktree | `git worktree prune --dry-run`, then `git worktree prune` | Recreate: `git worktree add <path> <branch>` | Registrations only |
| Orphan copy with unpushed work | Report only; the user decides (push, archive, or delete it themselves) | — | None: copies outside the repository are never touched without an item naming the path |

## False positives in this area

| It looks like | It is not proof of |
| --- | --- |
| `info/refs` present | A dumb-HTTP server: `git gc` and `git repack` write it `[observed]` |
| `git-daemon-export-ok` present | Exposure: no daemon may be running; it matters when one serves the parent folder |
| `check-attr` says `unspecified` | The file ships: a directory pattern excludes it from the archive `[observed]` |
| `uses: owner/action@v4` | A compromise: it is a policy gap (movable tag), not evidence of tampering |
| A 40-hex pin | Safety: the commit may live only in a fork; the comment tag may lie |
| A clone with the same root commit | A copy of this repository: forks and repositories created from a template share roots |
| No copies found | No copies exist: excluded folders, other machines and containers were not scanned |
| `ls-remote` 403/404 | The upstream is gone (`audit-contract.md` section 9) |

## Version floors

| Feature | Floor |
| --- | --- |
| `git ls-remote --exit-code` | any modern Git `[doc]` |
| `--end-of-options` for untrusted names | 2.24 `[doc]` RelNotes 2.24.0 |
| `log --format=%(trailers:key=…,valueonly)` | present in 2.55 `[observed]`; floor not verified |
| `git worktree list --porcelain` `prunable` | present in 2.55 `[observed]` |

## Sources

- https://git-scm.com/docs/git-daemon (export-ok, `--export-all`, services)
- https://git-scm.com/docs/git-update-server-info, https://git-scm.com/docs/git-repack (`-n`)
- https://git-scm.com/docs/gitrepository-layout (`description`, `info/refs`, `objects/info/packs`)
- https://git-scm.com/docs/git-archive and https://git-scm.com/docs/gitattributes
  (`export-ignore`, `export-subst`, `tar.<format>.command`)
- https://git-scm.com/docs/git-svn (FILES), https://git-scm.com/docs/git-fast-export
- https://git-scm.com/docs/git-ls-remote, https://git-scm.com/docs/git-config (`--file`, includes)
- https://github.com/newren/git-filter-repo (OUTPUT: commit-map, ref-map, already_ran)
- GitHub Actions secure use ("Pin actions to a full-length commit SHA"),
  https://docs.github.com/en/actions/reference/security/secure-use
- Corpus: `commands/git-daemon.md`, `commands/git-update-server-info.md`,
  `commands/git-archive.md`, `commands/git-svn.md`, `commands/git-fast-export.md`,
  `commands/git-filter-repo.md`
