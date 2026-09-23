# Tracing: where a string, line or behavior came from

Areas: G21. `routine` runs the Routine checks only when the request asks where code, a line
or a behavior came from; `deep` runs Routine and Deep.

Every command below is a read unless its row says otherwise. Facts are tagged `[observed]`
(run on Git 2.55.0, macOS, on a fixture) or `[doc]` (official page, listed under Sources).
Three rules hold for every recipe here:

- `--no-replace-objects` is a global option: `git --no-replace-objects log …` `[observed]`.
- `git log -S/-G/-L/-p`, `git show <commit>` and `git blame` run `diff.<driver>.textconv`
  programs by default `[observed]`: always add `--no-textconv`. Never use
  `git grep --textconv` or `git grep -O` (`--open-files-in-pager`).
- Never let a search reach a secret-shaped file (`audit-contract.md` section 4).

## Contents

1. What can go wrong
2. Routine checks: find it (1-4), date it (5-8), attribute it (9-11)
3. Deep checks: bisect (12-20)
4. Recommendations and recovery
5. False positives in this area
6. Version floors
7. Sources

## What can go wrong

- A search misses the answer because it looked in the wrong place: the working tree instead
  of the index, the current tree instead of history, tracked files instead of untracked.
- `blame` credits a reformatting commit, a file move or a mass rename instead of the author
  of the logic.
- `log --follow` wanders into another file's history through copy detection.
- `bisect` is left running: `HEAD` stays detached on an old commit and `refs/bisect/*` pin
  objects. Starting a bisection checks out commits, so it is an **approved item**, never a
  read.
- A bisect script that lives inside the repository changes or disappears as commits are
  checked out, and an exit code above 127 aborts the whole session.

## Routine checks

### Find it (git grep)

1. **Tracked files, working-tree content.**

   ```sh
   git --no-pager grep -n --column -I -e 'uses' --and -e 'actions' -- .github
   git --no-pager grep -c -e 'def' --and --not -e 'alpha' -- '*.py'
   git --no-pager grep -l --all-match -e 'def' -e 'gamma' -- '*.py'
   ```

   `[observed]`: `--column` printed `path:line:column:`; `--and`, `--not` and `--all-match`
   combined as documented. Options that matter: `-e` (one pattern each, safe for patterns
   starting with `-`), `--and`/`--or`/`--not` and `( … )`, `-F` fixed string, `-E` extended,
   `-P` Perl (a compile-time option; Git dies when missing `[doc]`; it worked on Homebrew
   Git 2.55 `[observed]`), `-w` whole word, `-i` ignore case, `-n` line numbers, `-l` / `-L`
   file names with / without a match, `-c` counts, `-q` exit status only (0 match, 1 none
   `[observed]`), `-z` NUL-separated names, `-m <n>` / `--max-count` hits per file
   `[observed]`, `-I` skip binary files, `-h` no file names, `-o` only the match.

2. **The index and any revision.**

   ```sh
   git --no-pager grep -n --cached 'staged-only'
   git --no-pager grep -n -F 'b' HEAD~2 -- a
   git --no-pager grep -n -e 'pattern' main v1.0 -- 'src/*'
   ```

   `[observed]`: a line only in the index was found with `--cached` and not without it;
   a revision search prefixes each hit with the revision (`HEAD~2:a:2:b`). Revisions go
   before `--`, paths after it (`gitcli`). A tree search covers only that tree, not history
   (use check 5 for history).

3. **Untracked files, with secrets excluded.**

   ```sh
   git --no-pager grep -l --untracked --no-exclude-standard -e 'pattern' -- \
     ':(exclude,glob)**/.env*' ':(exclude,glob)**/*.pem' ':(exclude,glob)**/*.key' \
     ':(exclude,glob)**/id_*' ':(exclude,glob)**/credentials*' ':(exclude,glob)**/.npmrc' \
     ':(exclude,glob)**/.pypirc' ':(exclude,glob)**/.netrc' ':(exclude,glob)**/*.tfvars' \
     ':(exclude,glob)**/.dev.vars' ':(exclude,glob)**/*.p12' ':(exclude,glob)**/*.pfx' \
     ':(exclude,glob)**/node_modules/**'
   ```

   `[observed]`: without the exclusions, `--untracked --no-exclude-standard` listed the
   ignored `.env`; with them it did not, and still found ignored `dist/b.js`,
   `app.txt.orig` and `s.txt.rej`. Plain `--untracked` (ignored files skipped) is safer
   when ignored files are out of scope. The exclusions also drop `.env.example`; search it
   by name if needed.

4. **Submodules.** `git grep --recurse-submodules -n -e 'pattern'` searches every active,
   checked-out submodule; with a `<tree>` it prefixes hits with the superproject tree
   `[doc]`. It cannot be combined with `--untracked` and has no effect with `--no-index`
   `[doc]`.

### Date it (history)

5. **When a string was added or removed (pickaxe).**

   ```sh
   git --no-replace-objects --no-pager log --all --no-textconv -S'intermediate_value' \
     --format='%h %ad %s' --date=short --name-status
   git --no-replace-objects --no-pager log --all --no-textconv --extended-regexp \
     -G'gamma_function_[a-z]+' --format='%h %s' --name-only
   ```

   `-S<string>` lists commits that change the **number** of occurrences (an added or
   removed line, not a moved one); `--pickaxe-regex` makes it a regex. `-G<regex>` lists
   commits whose added or removed lines match, even when the count stays the same `[doc]`.
   `--pickaxe-all` shows every file of a matching commit, not only the matching one.
   `-G` skips binary files unless `--text` `[doc]`. Output commit and path; show a patch
   only for non-secret files and only with `--no-textconv`.

6. **Evolution of a line range or a function.**

   ```sh
   git --no-replace-objects --no-pager log --no-textconv -L '/^def gamma/,+2:g.py' \
     --format='%h %s' --no-patch
   git --no-replace-objects --no-pager log --no-textconv -L ':alpha:m.py' --format='%h %s' --no-patch
   git --no-replace-objects --no-pager log --no-textconv -L 10,20:path/file.py \
     <commit>..HEAD --format='%h %s'
   ```

   `[observed]`: the function form listed `eaa6f1e style: reformat` and `35f0a85 add m.py`.
   `-L` takes at most one positive revision and no pathspec, and the range must exist at the
   start revision `[doc]`. It does **not** follow code moved from another file: for
   `g.py`, whose lines came from `m.py`, it listed only the move commit `[observed]`; use
   `blame -C` (check 9) for moved code.

7. **A file across renames.**

   ```sh
   git --no-replace-objects --no-pager log --no-textconv --follow -M \
     --format='%h %s' --name-status -- h.py
   ```

   `[observed]`: it showed `R100 g.py h.py`, then `C084 m.py g.py`, and continued with
   `m.py`'s whole history: `--follow` accepts copies as ancestors. Read the status letters
   before trusting the lineage. `--follow` works for one file only `[doc]`. For merges
   along the main line, add `--first-parent`.

8. **Which release first contained a commit, and a name for a commit.**

   ```sh
   git describe --tags <commit>
   git describe --contains <commit>
   git name-rev --name-only --tags <commit>
   git log -1 --format=%B <commit> | git name-rev --annotate-stdin
   git describe --dirty --broken
   ```

   `[observed]`: `describe main` gave `v1.0-5-gfacfde2` (5 commits after annotated tag
   `v1.0`); `describe` ignores lightweight tags unless `--tags`; `describe --contains`
   gave `v1.0~2` (the first tag that contains it); `name-rev` preferred a tag
   (`tags/light~2`); `--annotate-stdin` appended `(tags/v1.0^0)` after a full SHA in text.
   `--dirty` and `--broken` add a suffix when the working tree differs from `HEAD` `[doc]`;
   they compare the working tree like `status` does, so run them as
   `git --no-optional-locks describe --dirty` and only after G12 cleared filter drivers.

### Attribute it (blame)

9. **Who last changed each line, seeing through moves.**

   ```sh
   git --no-pager blame --no-textconv -s -C -C -M -- g.py
   git --no-pager blame --no-textconv --line-porcelain -L 1,3 -C -C -M -- g.py \
     | grep -E '^([0-9a-f]{40} |author |filename |previous )'
   ```

   `[observed]`: after moving a three-line function from `m.py` to `g.py`, plain `blame`
   credited the move commit; `-C` credited the original commit and printed the old file
   name `m.py`. A two-line block of 23 characters was **not** detected: copy detection
   needs about 40 alphanumeric characters by default (`-C<num>`) `[doc]`. One `-C` looks in
   files changed by the same commit, two add the commit that created the file, three look
   in every commit (slow) `[doc]`. `-M` detects moves within the file.

10. **Ignore formatting commits.**

    ```sh
    git --no-pager blame --no-textconv -s -C -C -M --ignore-revs-file=.git-blame-ignore-revs -- n.py
    git -c blame.markIgnoredLines=true --no-pager blame --no-textconv -s \
      --ignore-revs-file=.git-blame-ignore-revs -- n.py
    git --no-pager config --show-scope --get-regexp '^blame\.'
    ```

    `[observed]`: with the reformat commit listed, its line was credited to the earlier
    commit, and `markIgnoredLines` prefixed it with `?`. `--ignore-revs-file=` (empty)
    clears the list, including files from `blame.ignoreRevsFile` `[observed]` `[doc]`.
    `blame.ignoreRevsFile` pointing at a missing file makes **every** `blame` fail with
    `fatal: could not open object name list` `[observed]`: report it as a finding.
    `--ignore-rev <rev>` ignores one commit. `--first-parent` blames along the main line.

11. **Other blame options that matter.** `--reverse <start>..<end>` shows the last commit
    in which a line still existed `[doc]`; `--contents <file>` blames a working copy
    (never pass a secret-shaped file); `-w` ignores whitespace; `--porcelain` and
    `--line-porcelain` are the parseable forms; `--color-lines` and `--color-by-age` are
    for humans only.

## Deep checks

`git bisect` finds the commit that changed a behavior by checking out commits between a
known "old" and a known "new" state. `start`, `good`/`bad`/`old`/`new`, `skip`, `replay`
and `run` move `HEAD`, write `refs/bisect/*` and `BISECT_*` files, and can run programs:
propose the whole session as one approved item, stating the range, the terms, the script
and that `git bisect reset` ends it. `git bisect log` and `git bisect terms` are reads;
`git bisect visualize` starts `gitk` or a log with a pager, so do not use it.

12. **Preconditions** (reads, re-checked right before the item runs): clean tree
    (`git --no-optional-locks status --porcelain` empty, after G12 cleared filter drivers),
    no operation in progress (`areas/repository-and-operations.md`), no bisect already
    running (`git bisect log` prints `error: We are not bisecting.` and exits 1 when idle
    `[observed]`), and the script
    stored **outside** the repository (the official examples say it is safer `[doc]`).

13. **Start with explicit terms.** (Mutates: checks out a commit.)

    ```sh
    git bisect start --term-old=fast --term-new=slow main good-point --
    git bisect terms
    ```

    `[observed]`: `bisect terms` printed `Your current terms are 'works' for the old state
    and 'broken' for the new state.` for a custom pair. Default pairs are `good`/`bad` and
    `old`/`new` (for "when was this fixed" searches). Revisions: first the new one, then
    one or more old ones, then `--` and an optional pathspec that narrows candidates to
    commits touching those paths `[doc]`.

14. **Main line only.** `git bisect start --first-parent main base --` follows only first
    parents, so a merge is blamed instead of a broken commit inside the merged branch
    `[doc]` (Git ≥ 2.29). `[observed]` it ran and found the first bad main-line commit on a
    fixture with a merged topic branch.

15. **No checkout.** `git bisect start --no-checkout main good-point --` leaves the working
    tree and branch alone and moves only `BISECT_HEAD` `[doc]`. `[observed]`: `HEAD` stayed
    on `main`, `BISECT_HEAD` existed during the session and was removed by `reset`. The
    script must read `BISECT_HEAD`, for example `git cat-file -p BISECT_HEAD:state`. It still
    writes `refs/bisect/*` and `BISECT_*` files. Bare repositories assume `--no-checkout`.

16. **Run a script, and its exit codes.**

    ```sh
    git bisect run /absolute/outside/path/probe.sh
    ```

    | Script exit | Meaning |
    | --- | --- |
    | 0 | old / good `[doc]` |
    | 1-127 except 125 | new / bad `[doc]` |
    | 125 | cannot test: skip this commit `[doc]`; `[observed]` all-skip ends with `We cannot bisect more!`, run exit 2 |
    | 126 or 127 on the **first** run | Git re-runs the script on a known-good commit; the same code again aborts with `bogus exit code 127 for 'good' revision` (a missing or non-executable script) `[observed]`, source `builtin/bisect.c` |
    | 128-255, including `exit(-1)` = 255 | aborts: `bisect run failed: exit code 255 … is < 0 or >= 128` `[observed]` |

    `[observed]`: a script returning 1 when a file contained `BUG` found the planted first
    bad commit (`c11`) in 3 steps; `bisect run` itself exited 1 on 255, 128 on 128. The
    script decides only by its exit code; print nothing secret from it.

17. **Skip ranges and manual marks.** `git bisect skip main~9..main~6` skipped 3 commits
    `[observed]`; `git bisect good|bad|old|new|<term> <rev>` marks one commit. Use
    revisions based on a branch name: `HEAD~9` resolves from the checked-out bisect commit,
    not from the branch tip `[observed]` (it failed with a usage error).

18. **Record and replay.**

    ```sh
    git bisect log > <evidence>/bisect-log.txt
    git bisect replay <evidence>/bisect-log.txt
    ```

    `[observed]`: replay reproduced `# first 'bad' commit: [aafd896…] c11`. Edit the saved
    log to drop a wrong mark before replaying.

19. **Always end the session.** `git bisect reset` returns to the branch where it started
    and removes `refs/bisect/*` and every `BISECT_*` file `[observed]`
    (`BISECT_ANCESTORS_OK`, `BISECT_EXPECTED_REV`, `BISECT_LOG`, `BISECT_NAMES`,
    `BISECT_RUN`, `BISECT_START`, `BISECT_TERMS`, plus `BISECT_HEAD` with `--no-checkout`).
    `git bisect reset -q` is **not** valid: it failed with `error: '-q' is not a valid
    commit` and left the session running `[observed]`. `git bisect reset <commit>` ends on
    that commit instead.

20. **Localize damage in a repository (`areas/object-store.md`).** The official example
    bisects with `--no-checkout` and a script that packs everything reachable from
    `BISECT_HEAD` but not from the good commits; the first "bad" commit has a parent whose
    whole graph can be packed `[doc]`. Keep the temporary file outside the repository (the
    official one-liner writes `tmp.$$` into the current directory):

    ```sh
    #!/bin/sh
    t=$(mktemp) || exit 255
    GOOD=$(git for-each-ref '--format=%(objectname)' 'refs/bisect/good-*') &&
    git --no-replace-objects rev-list --objects BISECT_HEAD --not $GOOD >"$t" &&
    git pack-objects --stdout >/dev/null <"$t"
    rc=$?
    rm -f "$t"
    test $rc = 0
    ```

    Save it outside the repository, then `git bisect start --no-checkout HEAD <known-good> --`
    and `git bisect run /absolute/outside/path/packprobe.sh`. `[observed]` on a healthy
    repository it ran to completion and blamed the tip (nothing broken), and left the tree
    clean. With custom terms, replace `good-*` by `<old-term>-*`.

## Recommendations and recovery

| Finding | Action (literal command) | Undo | Approval scope |
| --- | --- | --- | --- |
| Formatting commits pollute blame | Add their SHAs to `.git-blame-ignore-revs`, commit, and optionally `git config --local blame.ignoreRevsFile .git-blame-ignore-revs` | `git revert <commit>`; `git config --local --unset blame.ignoreRevsFile` | One tracked file; local key |
| `blame.ignoreRevsFile` points to a missing file | `git config --local --unset blame.ignoreRevsFile` (or create the file) | `git config --local blame.ignoreRevsFile <path>` | Named scope and key |
| Origin of a regression unknown | Bisect session: `git bisect start --term-old=<old> --term-new=<new> <new-rev> <old-rev> --`, `git bisect run /absolute/outside/path/probe.sh`, `git bisect log`, `git bisect reset` | `git bisect reset` restores the starting branch | The named range, terms and script; no edits, commits or stashes |
| Bisect left running | `git bisect log > <evidence>/bisect-log.txt`, then `git bisect reset` | `git bisect replay <evidence>/bisect-log.txt` | Ends that session only |

## False positives in this area

| It looks like | It is not proof of |
| --- | --- |
| `blame` names a commit | Its author wrote the logic: moves, reformatting and renames take the credit without `-C -C -M` and ignore-revs |
| `log --follow` lineage | The file's real ancestry: copy detection can jump to another file `[observed]` |
| `-S` finds no commit | The string never changed: a moved line keeps the count; use `-G` |
| `git grep` finds nothing | The text is absent: it searched one tree, skipped untracked, ignored or binary files |
| `describe` output | The commit was released: it names the nearest tag below, not one that contains it (`--contains`) |
| A bisect result | The root cause: a flaky script, skipped commits or a merge can shift it; confirm by testing the parent |

## Version floors

| Feature | Floor |
| --- | --- |
| `log -L` | 1.8.4 `[doc]` RelNotes 1.8.4 |
| `grep --untracked` | 1.7.8 `[doc]` RelNotes 1.7.8 |
| `grep --column` | 2.19 `[doc]` RelNotes 2.19.0 |
| `grep -m` / `--max-count` | 2.38 `[doc]` RelNotes 2.38.0 |
| `blame --ignore-rev`, `--ignore-revs-file`, `blame.ignoreRevsFile` | 2.23 `[doc]` RelNotes 2.23.0 |
| `bisect` old/new and custom terms | 2.7 `[doc]` RelNotes 2.7.0 |
| `bisect --first-parent` | 2.29 `[doc]` RelNotes 2.29.0 |
| `name-rev --annotate-stdin` | 2.36 `[doc]` RelNotes 2.36.0 |
| `--end-of-options` | 2.24 `[doc]` RelNotes 2.24.0 |

## Sources

- https://git-scm.com/docs/git-grep, https://git-scm.com/docs/gitglossary (pathspec magic)
- https://git-scm.com/docs/git-log (`-S`, `-G`, `-L`, `--follow`, `--textconv`),
  https://git-scm.com/docs/gitdiffcore (pickaxe)
- https://git-scm.com/docs/git-blame, https://git-scm.com/docs/git-describe,
  https://git-scm.com/docs/git-name-rev
- https://git-scm.com/docs/git-bisect (terms, run, `--no-checkout`, `--first-parent`, the
  damaged-repository example), https://git-scm.com/docs/git-bisect-lk2009
- `builtin/bisect.c` at v2.55.0, https://github.com/git/git (126/127 first-run check)
- https://git-scm.com/docs/gitcli
- Corpus: `commands/git-grep.md`, `commands/git-log.md`, `commands/git-blame.md`,
  `commands/git-bisect.md`, `commands/git-show.md`
