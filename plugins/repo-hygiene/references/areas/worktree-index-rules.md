# Working tree, index, ignore and attribute rules

Areas: G3, G4, G20. `routine` runs the Routine checks; `deep` runs Routine and Deep.

Every command below is a read unless its row says otherwise. Facts are tagged `[observed]`
(run on Git 2.55.0, macOS, case-insensitive APFS, on a fixture) or `[doc]` (official page,
listed under Sources). In a partial clone add `--no-lazy-fetch` after `git`
(`areas/repository-and-operations.md`, G1 check 3).

## Contents

1. What can go wrong
2. Routine checks (G3: 1-8, G4: 9-14, G20: 15-16)
3. Deep checks
4. Recommendations and recovery
5. False positives in this area
6. Version floors
7. Sources

## What can go wrong

G3, working tree and index:

- Staged and unstaged changes mixed on the same file; unresolved conflicts.
- Untracked files piling up by directory.
- **Hidden local changes**: files marked assume-unchanged or skip-worktree. Git stops
  reporting their edits, so `git status` looks clean while the file differs.
- Intent-to-add entries (`git add -N`): tracked names with no content yet.
- Executable-bit flips that `core.filemode=false` hides.
- Case-only collisions (`README.md` and `readme.md`): on a case-insensitive disk only one
  survives, silently.
- Line endings in the index that contradict `.gitattributes`.
- Large files tracked in the tree.

G4, ignore and attribute rules:

- Rules at every level: `.gitignore` in each directory, `.git/info/exclude`,
  `core.excludesFile` (global); rules that match nothing, rules that cannot work (a
  negation under an excluded directory), rules that contradict each other.
- Tracked files that a rule now ignores (rule added after the file was committed).
- Secret-shaped files (`.env*`, keys, `credentials*`, …) that no rule ignores.
- `.gitattributes` drift: `eol`/`text` settings the index does not follow; `filter`,
  `diff`, `merge` drivers (for example `lfs`) that no config defines.

G20, editor, OS and environment noise:

- Tracked `.DS_Store`, `Thumbs.db`, `desktop.ini`, `.vscode/`, `.idea/`, swap and backup
  files (`*.swp`, `*~`, `*.bak`).
- Noise ignored only by one person's global excludes file, so collaborators still commit it.
- `core.autocrlf`, `core.eol`, `core.filemode`, `core.ignorecase`, `core.symlinks` set
  against the platform or the filesystem.

## Routine checks

### G3

1. **One porcelain snapshot, counted by kind.**

   ```sh
   git --no-optional-locks --no-pager status --porcelain=v2 --branch --show-stash \
     --untracked-files=normal > "<evidence-dir>/status.txt"
   awk '{print $1}' "<evidence-dir>/status.txt" | sort | uniq -c
   ```

   Line kinds `[doc]`: `1` ordinary change, `2` rename or copy, `u` unmerged (conflict),
   `?` untracked, `!` ignored (only with `--ignored`), `#` headers. `XY` uses `.` for
   "unchanged": `M.` staged only, `.M` unstaged only, `MM` both, `.A` intent-to-add
   `[observed]`. Conflict codes in `XY`: `UU`, `AA`, `DD`, `AU`, `UA`, `DU`, `UD` (`UD`
   seen during a stopped revert `[observed]`). `# stash <N>` appears with `--show-stash`
   or `status.showStash=true` in config `[observed]`. Stderr may carry
   `warning: in the working copy of '<path>', LF will be replaced by CRLF` lines when
   `core.autocrlf` is on `[observed]`: they are line-ending notices, not errors.
   Explain staged vs unstaged: "staged means ready for the next commit; unstaged means
   edited but not yet marked for it".

2. **Untracked files by directory.** `git --no-optional-locks --no-pager ls-files -o
   --exclude-standard --directory | head -n 50` lists untracked directories once, with a
   trailing `/` `[doc]`; count first with `| wc -l`. For a per-directory total use
   `git --no-optional-locks --no-pager ls-files -o --exclude-standard | awk -F/
   '{print (NF>1?$1"/":"(top)")}' | sort | uniq -c | sort -rn | head -n 20`.

3. **Hidden local changes.**

   ```sh
   git --no-optional-locks --no-pager ls-files -v | grep -E '^[a-zS]'
   ```

   `-v` prints the `-t` tag in lowercase for assume-unchanged `[doc]`; `S` is
   skip-worktree `[doc]`. `[observed]`: `h app.txt` (assume-unchanged) and `S skip.txt`
   (skip-worktree, with an edit that neither `status`, `ls-files -m` nor
   `diff HEAD -- skip.txt` showed). To see whether a flagged file really differs, compare
   hashes without touching the bit:

   ```sh
   git hash-object -- skip.txt
   git rev-parse :skip.txt
   ```

   Different hashes mean the file on disk was edited `[observed]`. `hash-object` without
   `-w` writes nothing, and the hash reveals no content. It applies the path's clean
   filter and line-ending conversion, so skip it for a path whose `filter` attribute names
   a driver (that would run a configured program, contract section 2); use
   `git hash-object --no-filters -- <path>` there and expect false differences from line
   endings.
   **Protect-work priority** `[observed]`: after `git update-index --assume-unchanged a`
   and an edit to `a`, a `git stash push` made for another file restored `a` to its index
   version; the edit was not in the stash (`stash@{0}:a` equals `:a`) and was gone. In the
   main fixture a hidden edit was lost the same way. Report every flagged file whose
   hashes differ as work at risk.
   Explain: "Git was told to stop watching this file, so your edits to it are invisible,
   will never be committed, and some commands (stash, checkout) can overwrite them without
   a warning".

4. **Intent-to-add entries.** In porcelain v2 they show as `1 .A` with an all-zero index
   object name `[observed]`; `git ls-files --eol` shows `i/none` for them `[observed]`.
   Explain: "the file name is registered but its content is not".

5. **Mode flips hidden by `core.filemode=false`.**

   ```sh
   git --no-optional-locks --no-pager -c core.filemode=true diff --no-ext-diff \
     --no-textconv --summary
   ```

   `[observed]`: with `core.filemode=false`, a `chmod +x` was invisible; with
   `-c core.filemode=true` the command printed `mode change 100644 => 100755 mode.sh`. The
   `-c` only affects this read.

6. **Case-only collisions.**

   ```sh
   git --no-optional-locks --no-pager ls-files | LC_ALL=C tr '[:upper:]' '[:lower:]' \
     | sort | uniq -d
   test -e "$(git rev-parse --show-toplevel)/.GIT" && echo case-insensitive
   ```

   `[observed]`: a repository with `README.md` and `readme.md` printed `readme.md`; cloning
   it on macOS warned "the following paths have collided" and `status` then showed nothing,
   because both entries had the same content. With different contents one file shows as
   modified forever. The `.GIT` probe works on a main or linked worktree.

7. **Line endings against `.gitattributes`.**

   ```sh
   git --no-optional-locks --no-pager ls-files --eol | grep -E '^i/(crlf|mixed)' \
     | grep -v -e 'attr/-text' -e 'attr/text eol=crlf' | head -n 50
   ```

   Columns: `i/<index eol> w/<worktree eol> attr/<eol attribute> <TAB> path` `[doc]`.
   `[observed]`: `i/crlf  w/crlf  attr/text=auto  crlf.txt` (CRLF stored although the
   attribute says it is text and must be stored with LF). Preview the fix without writing:
   `git add --renormalize --dry-run -- <path>` printed `add 'crlf.txt'` and left the index
   checksum unchanged `[observed]`.
   Explain: "the rules say this file must be stored with Unix line endings, but it was
   committed with Windows ones; the next person to touch it gets a whole-file diff".

8. **Large tracked files.**

   ```sh
   git --no-optional-locks --no-pager ls-files --format='%(objectsize) %(path)' \
     | sort -rn | head -n 20
   git --no-optional-locks --no-pager ls-files --format='%(objectsize) %(path)' \
     | awk '$1>=1048576{n++; s+=$1} END{print n+0, s+0}'
   ```

   `[observed]`: `6000000 big.bin` first; the second line printed the count and total
   bytes over 1 MiB. `%(objectsize)` is the size of the blob recorded in the index `[doc]`.
   History-wide large blobs belong to G14.

### G4

9. **Where every rule lives.** Per-directory `.gitignore` files:
   `git --no-optional-locks --no-pager ls-files -- '.gitignore' '*/.gitignore'` (a pathspec
   `*` matches across `/`, so `*/.gitignore` finds every depth `[observed]`). Also:
   `git config --show-origin --get core.excludesFile` (global excludes; `[observed]`
   defined in `~/.config/git/config`), `$XDG_CONFIG_HOME/git/ignore` when that key is
   unset `[doc]`, and `"$(git rev-parse --git-path info/exclude)"`.
   Reading these files is safe: they hold patterns, not secrets.

10. **Which rule matches each ignored path.**

    ```sh
    git --no-optional-locks --no-pager ls-files -z -o -i --exclude-standard --directory \
      | git --no-pager check-ignore -z -v --stdin | tr '\0' '\n' | paste - - - - \
      | awk -F'\t' '{print $1":"$2":"$3}' | sort | uniq -c
    ```

    `[observed]`: one line per rule in use (`.gitignore:1:node_modules/`, …). A rule that
    never appears matches nothing today: report it as "unused", not "dead", since it may
    guard files that do not exist yet. `-v` output format: `<source>:<line>:<pattern>
    <TAB><path>`; with `-z`, NUL separates the four fields `[doc]`, `[observed]`.
    `<source>` is absolute for `core.excludesFile` and relative for the others `[doc]`.

11. **Tracked files that a rule now ignores.**

    ```sh
    git --no-optional-locks --no-pager ls-files -c -i --exclude-standard
    ```

    `[observed]`: listed `app.log` (`*.log` added after commit) **and** `.DS_Store`,
    `.idea/workspace.xml`, `.notes.txt.swp`, matched only by the user's global excludes
    file. Separate the two: rerun with `-c core.excludesFile=/dev/null` to see what the
    repository's own rules ignore (`app.log` only `[observed]`). Explain the source with
    `git check-ignore -v --no-index -- <path>`: without `--no-index`, tracked paths are
    never reported (exit 1) `[observed]`, `[doc]`.
    Explain: "this file is committed although the ignore rules say it should not be;
    ignore rules do not apply to files Git already tracks".

12. **Secret-shaped files that no rule ignores.**

    ```sh
    git --no-optional-locks --no-pager ls-files -o --exclude-standard \
      | grep -E '(^|/)(\.env[^/]*|[^/]*\.(pem|key|p12|pfx|tfvars)|id_[^/]*|credentials[^/]*|\.npmrc|\.pypirc|\.netrc|\.dev\.vars)$' \
      | grep -Ev '\.(example|sample|template)$'
    ```

    Run the same filter on `git ls-files -c` (tracked secrets: a G14 finding too) and on
    `git ls-files -o -i --exclude-standard` (ignored: fine, but only locally, see below).
    `[observed]`: found `.env.local`, `credentials.json`, `id_rsa` and a nested
    `deep/x/.env`, and skipped `deep/x/.env.example`. Report path, size (`wc -c < <path>`),
    tracked or not, and the rule (none). Never open the file (contract section 4).
    Explain: "a file that usually holds passwords sits in the project with nothing
    stopping `git add .` from committing it".

13. **Rules that cannot work or contradict.** A negation (`!pattern`) under an excluded
    directory never re-includes: "It is not possible to re-include a file if a parent
    directory of that file is excluded" `[doc]`. `[observed]`: with `build/` and
    `!build/keep.o`, `git check-ignore -v build/keep.o` still named `build/`. A negation
    that does match makes `check-ignore -v` exit 0 and print the `!` pattern although the
    path is **not** ignored (`.gitignore:3:!keep.log`), while `check-ignore` without `-v`
    exits 1 `[observed]`: read the pattern, not the exit code.

14. **Attributes that drift.**

    ```sh
    git --no-optional-locks --no-pager ls-files -z -- '.gitattributes' '*/.gitattributes' \
      | xargs -0 grep -HnoE '(^|[[:space:]])(filter|diff|merge)=[^[:space:]]+'
    git --no-pager config --name-only --get-regexp '^(filter|diff|merge)\.[^.]+\.'
    git --no-pager config --show-origin --get core.attributesFile
    ls "$(git rev-parse --git-path info/attributes)" 2>/dev/null
    ```

    A driver named in attributes but absent from config (exit 1 on the second command)
    means Git falls back to defaults: `[observed]` `filter=lfs diff=lfs merge=lfs` with no
    `filter.lfs.*` defined, so LFS pointers are never produced. `git check-attr --all --
    <path>` shows what applies to a path; `--cached` reads only the index version of
    `.gitattributes` and `--source=<tree-ish>` a commit's `[doc]`, `[observed]` (a line added
    only in the working tree did not show under `--cached`). Line-ending drift is check 7.
    `export-ignore` coverage belongs to G18.

### G20

15. **Tracked noise.**

    ```sh
    git --no-optional-locks --no-pager ls-files \
      | grep -E -i '(^|/)(\.DS_Store|Thumbs\.db|ehthumbs\.db|desktop\.ini|\.vscode/|\.idea/|[^/]*\.sw[a-p]|[^/]*~|\.#[^/]*|#[^/]*#|[^/]*\.(bak|tmp|orig|rej)|__MACOSX/|\._[^/]*|[^/]*\.iml|\.fleet/|\.history/)'
    ```

    `[observed]`: `.DS_Store`, `.idea/workspace.xml`, `.notes.txt.swp`. `.vscode/` may be
    shared on purpose (`settings.json`, `extensions.json`, `launch.json`); report it as a
    question, not a defect. Then check whether the repository's own `.gitignore` covers
    each (check 11): a rule only in one person's global file does not protect anyone else.

16. **Platform-sensitive core settings.**

    ```sh
    git --no-pager config --show-origin --show-scope --get-regexp \
      '^core\.(autocrlf|eol|safecrlf|filemode|ignorecase|symlinks|precomposeunicode|protecthfs|protectntfs|longpaths)$'
    uname -s
    ```

    `[observed]`: global `core.autocrlf input` overridden by local `core.autocrlf true`
    (the last one read wins, so local wins); local `core.filemode false` on a filesystem
    that supports modes; `core.ignorecase true` on case-insensitive APFS. Expectations:
    `core.autocrlf=true` belongs on Windows, not macOS or Linux; `core.filemode=false` is
    right on FAT/exFAT/NTFS or network shares, wrong on APFS or ext4 (it hides check 5);
    `core.ignorecase` must match the probe in check 6; `core.symlinks=false` turns symlinks
    into plain text files. Explain each as "this setting was probably copied from another
    machine; here it hides X".

## Deep checks

1. **Index vs HEAD vs worktree on every path.**

   ```sh
   git --no-optional-locks --no-pager diff --no-ext-diff --no-textconv --cached --name-status
   git --no-optional-locks --no-pager diff --no-ext-diff --no-textconv --name-status
   git --no-optional-locks --no-pager ls-files -u
   git --no-optional-locks --no-pager diff --no-ext-diff --no-textconv --check
   ```

   `--check` exits 2 and prints `leftover conflict marker` lines for a file with markers
   `[observed]`. `ls-files -u` prints stages 1 (base), 2 (ours), 3 (theirs) `[doc]`,
   `[observed]`. Add the hidden paths from Routine 3 (their index version vs the file on
   disk) so the reconciliation covers every path.

2. **When noise and rules entered history.** `git --no-replace-objects --no-pager log
   --diff-filter=A --format='%h %ad %an' --date=short -- <path>` for each tracked noise
   file and each `.gitignore`: report "the rule came on D2, after the file on D1". See
   `commands/git-log.md`.

3. **Ignored secret-shaped files everywhere, including ignored directories.** Routine 12
   uses `--directory` semantics on untracked listings; in deep run the filter over
   `git ls-files -o -i --exclude-standard` without `--directory` (can be long: count first,
   `head -n 200`, full list to the evidence package). These files are safe from `git add`
   but are copied by backups, archives and `git clean -X` (see `commands/git-clean.md`).

4. **Attribute changes in history.** `git --no-replace-objects --no-pager log --format='%h
   %ad %s' --date=short -- .gitattributes` and, for each line-ending drift from Routine 7,
   the commit that added the path. A renormalization commit is the usual fix.

## Recommendations and recovery

| Finding | Recommended action (literal command) | Undo | Approval scope notes |
| --- | --- | --- | --- |
| Assume-unchanged hides an edit | `git update-index --no-assume-unchanged -- app.txt` | `git update-index --assume-unchanged -- app.txt` | Only the bit; the file and the edit stay. Afterwards `status` shows the edit |
| Skip-worktree hides an edit (not a sparse checkout) | `git update-index --no-skip-worktree -- skip.txt` | `git update-index --skip-worktree -- skip.txt` | Same; never in a sparse checkout (use `git sparse-checkout` there) |
| Tracked file now ignored | `git rm --cached -- app.log` then commit | Before commit: `git reset -q HEAD -- app.log` | File stays on disk; collaborators lose it from their checkout on pull: say so |
| Secret-shaped file not ignored | Add a rule: append `.env.local` to `.gitignore` (Edit tool), commit | Revert the line | Does not remove anything already committed (G14) |
| Tracked editor/OS noise | `git rm --cached -- .DS_Store` + rule in the repository `.gitignore` | `git reset -q HEAD -- .DS_Store` before commit | One literal path per entry |
| Line-ending drift | `git add --renormalize -- crlf.txt` then commit | `git reset -q HEAD -- crlf.txt` before commit | Whole-file diff for that path; tell collaborators |
| Mode flip wanted/unwanted | Wanted: `git update-index --chmod=+x -- mode.sh`; unwanted: `chmod -x mode.sh` | The opposite flag | Fixing `core.filemode` itself is a separate item |
| Wrong `core.filemode` / `core.autocrlf` | `git config --local core.filemode true` / `git config --local --unset core.autocrlf` | `git config --local core.filemode false` / `git config --local core.autocrlf true` | Local scope only; never global without asking |
| Case-only collision | `git rm --cached -- readme.md` then commit (keep one name) | `git reset -q HEAD -- readme.md` before commit | Decide which content survives first: compare `git rev-parse :README.md :readme.md` |
| Intent-to-add left behind | `git rm --cached -- ita.txt` | `git add -N -- ita.txt` | File stays on disk |
| Unused ignore rule | Remove the line (Edit tool) | Restore the line | Low priority; "reduce noise" |
| Attribute driver missing | Configure the driver the way its tool documents it (Git LFS documents `git lfs install --local`; not run here, git-lfs was not installed) or remove the attribute line | The tool's own uninstall, or restore the line | After it, checkouts run the filter program (executes-config): say so |

## False positives in this area

- `S` entries are normal in a sparse checkout (`[doc]` skip-worktree section) and Git clears
  the bit itself when the file reappears in a sparse checkout `[doc]`.
- Assume-unchanged can be set on purpose on slow filesystems (`core.ignorestat`) `[doc]`.
- An ignored path is not a disposable path (contract section 9): `.env`, local config.
- `check-ignore -v` exit 0 does not mean "ignored" when the pattern starts with `!`
  `[observed]`.
- A rule that matches nothing today is not proof it is useless.
- `.vscode/` tracked may be a team decision.
- `LF will be replaced by CRLF` warnings are notices from `core.safecrlf`, not corruption.
- Noise ignored by your global excludes file looks clean to you and not to others.

## Version floors

| Feature | Floor | Source |
| --- | --- | --- |
| `ls-files --eol` | 2.8 | RelNotes 2.8.0 |
| `status --porcelain=v2` showing `# stash` | 2.35 | RelNotes 2.35.0 |
| `ls-files --format` | 2.38 | RelNotes 2.38.0 |
| `ls-files --sparse` | 2.35 | RelNotes 2.35.0 |
| Everything else here | available in 2.55 `[observed]`; floor not verified | — |

## Sources

- https://git-scm.com/docs/git-status
- https://git-scm.com/docs/git-ls-files
- https://git-scm.com/docs/git-update-index
- https://git-scm.com/docs/git-check-ignore
- https://git-scm.com/docs/git-check-attr
- https://git-scm.com/docs/gitignore
- https://git-scm.com/docs/gitattributes
- https://git-scm.com/docs/git-diff
- https://git-scm.com/docs/git-add (`--renormalize`)
- https://git-scm.com/docs/git-config (`core.*`)
- https://github.com/git/git/tree/master/Documentation/RelNotes
- Corpus: `commands/git-status.md`, `commands/git-ls-files.md`,
  `commands/git-check-ignore.md`, `commands/git-check-attr.md`,
  `commands/git-update-index.md`, `commands/git-diff.md`, `commands/git-clean.md`,
  `commands/git-log.md`, `areas/config-links-identity.md`
