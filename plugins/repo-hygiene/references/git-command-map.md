# Git command map

Find the command, guide or Pro Git section below, then open its corpus file when the Corpus column links one; otherwise read the official page.
The Areas column names the audit areas (G1–G22, P1–P9) the entry serves; the areas' own files hold the recipes.
The safety class decides whether a command may run without an approved item: only `read` runs freely (see [audit-contract.md](audit-contract.md) section 1).
A class in parentheses applies only to the subcommands or options named there; when a row lists several classes, the strictest one that the planned invocation triggers wins.

Safety classes: read · writes-local-state · mutates · network · executes-config · reference-only (a guide or format document, nothing to run)

Official pages were checked against git-scm.com at Git 2.55.0 on 2026-09-22; Pro Git is the 2nd edition.

## Contents

1. [Setup and Config](#setup-and-config)
2. [Getting and Creating Projects](#getting-and-creating-projects)
3. [Basic Snapshotting](#basic-snapshotting)
4. [Branching and Merging](#branching-and-merging)
5. [Sharing and Updating Projects](#sharing-and-updating-projects)
6. [Inspection and Comparison](#inspection-and-comparison)
7. [Patching](#patching)
8. [Debugging](#debugging)
9. [Email](#email)
10. [External Systems](#external-systems)
11. [Administration](#administration)
12. [Server Admin](#server-admin)
13. [Plumbing Commands](#plumbing-commands)
14. [Guides](#guides)
15. [Main porcelain outside the index](#main-porcelain-outside-the-index)
16. [Ancillary commands: manipulators](#ancillary-commands-manipulators)
17. [Ancillary commands: interrogators](#ancillary-commands-interrogators)
18. [Interacting with others](#interacting-with-others)
19. [Low-level commands: manipulation](#low-level-commands-manipulation)
20. [Low-level commands: interrogation](#low-level-commands-interrogation)
21. [Low-level commands: syncing repositories](#low-level-commands-syncing-repositories)
22. [Low-level commands: internal helpers](#low-level-commands-internal-helpers)
23. [Guides outside the index](#guides-outside-the-index)
24. [Repository, command and file interfaces](#repository-command-and-file-interfaces)
25. [File formats, protocols and developer interfaces](#file-formats-protocols-and-developer-interfaces)
26. [Other git-scm pages](#other-git-scm-pages)
27. [Pro Git (book)](#pro-git-book)
28. [Companion tools](#companion-tools)
29. [Coverage of this map](#coverage-of-this-map)

## Setup and Config

| Command or page | Areas | Safety class | Corpus | Official |
| --- | --- | --- | --- | --- |
| `git` (global options, environment, SECURITY) | G1, G11 | reference-only | [areas/config-links-identity.md](areas/config-links-identity.md) | [git](https://git-scm.com/docs/git) |
| `git config` | G11, G12, G13, G20 | read (`--get`, `--list`, `--show-origin`, `--show-scope`); mutates (`set`, `unset`, `rename-section`, `remove-section`); executes-config (`--edit` opens the editor) | [commands/git-config.md](commands/git-config.md) | [git-config](https://git-scm.com/docs/git-config) |
| `git help` | — | read (executes-config: `help.browser`, `man.viewer`) | — (no footprint: help viewer) | [git-help](https://git-scm.com/docs/git-help) |
| `git bugreport` | G2 | writes-local-state (writes `git-bugreport-*.txt` in the current directory) | [areas/repository-and-operations.md](areas/repository-and-operations.md) | [git-bugreport](https://git-scm.com/docs/git-bugreport) |
| Credential helpers (site page) | G11, G12 | reference-only | [areas/config-links-identity.md](areas/config-links-identity.md) | [credential-helpers](https://git-scm.com/doc/credential-helpers) |

## Getting and Creating Projects

| Command or page | Areas | Safety class | Corpus | Official |
| --- | --- | --- | --- | --- |
| `git init` | G1, G11 | mutates (creates or reinitializes a repository; copies `init.templateDir` hooks) | [commands/git-init.md](commands/git-init.md) | [git-init](https://git-scm.com/docs/git-init) |
| `git clone` | G1, G19, G22 | network + mutates (creates a new repository; runs `post-checkout`) | [commands/git-clone.md](commands/git-clone.md) | [git-clone](https://git-scm.com/docs/git-clone) |

## Basic Snapshotting

| Command or page | Areas | Safety class | Corpus | Official |
| --- | --- | --- | --- | --- |
| `git add` | G3 | mutates (index; `-N` intent-to-add); executes-config (clean filters from `.gitattributes`) | [areas/worktree-index-rules.md](areas/worktree-index-rules.md) | [git-add](https://git-scm.com/docs/git-add) |
| `git status` | G3, G4, G9, G10 | read (writes-local-state without `--no-optional-locks`: refreshes the index; executes-config when `core.fsmonitor` is a hook command) | [commands/git-status.md](commands/git-status.md) | [git-status](https://git-scm.com/docs/git-status) |
| `git diff` (also in Inspection and Comparison, Patching) | G3, G14, G21 | read (executes-config: external diff and textconv drivers run by default, disable with `--no-ext-diff --no-textconv`; writes-local-state: index refresh) | [commands/git-diff.md](commands/git-diff.md) | [git-diff](https://git-scm.com/docs/git-diff) |
| `git commit` | G3, G13 | mutates (new commit, moves the branch); executes-config (hooks, signing program) | [areas/worktree-index-rules.md](areas/worktree-index-rules.md) | [git-commit](https://git-scm.com/docs/git-commit) |
| `git notes` | G15 | read (`list`, `show`); mutates (`add`, `append`, `copy`, `edit`, `merge`, `remove`, `prune`) | [commands/git-notes.md](commands/git-notes.md) | [git-notes](https://git-scm.com/docs/git-notes) |
| `git restore` | G3 | mutates (working tree, index with `--staged`; discards changes) | [commands/git-restore.md](commands/git-restore.md) | [git-restore](https://git-scm.com/docs/git-restore) |
| `git reset` | G3, G16 | mutates (moves HEAD and the branch, index; working tree with `--hard`/`--merge`/`--keep`) | [commands/git-reset.md](commands/git-reset.md) | [git-reset](https://git-scm.com/docs/git-reset) |
| `git rm` | G3, G4 | mutates (index; working tree unless `--cached`); read with `-n` | [areas/worktree-index-rules.md](areas/worktree-index-rules.md) | [git-rm](https://git-scm.com/docs/git-rm) |
| `git mv` | G3 | mutates (index and working tree); read with `-n` | [areas/worktree-index-rules.md](areas/worktree-index-rules.md) | [git-mv](https://git-scm.com/docs/git-mv) |

## Branching and Merging

| Command or page | Areas | Safety class | Corpus | Official |
| --- | --- | --- | --- | --- |
| `git branch` | G5 | read (listing, `-vv`, `--merged`, `--contains`); mutates (create, `-d`/`-D`, `-m`, `-c`, `--set-upstream-to`, `--unset-upstream`) | [commands/git-branch.md](commands/git-branch.md) | [git-branch](https://git-scm.com/docs/git-branch) |
| `git checkout` | G3, G5 | mutates (HEAD, index, working tree); executes-config (`post-checkout`) | [commands/git-checkout.md](commands/git-checkout.md) | [git-checkout](https://git-scm.com/docs/git-checkout) |
| `git switch` | G5 | mutates (HEAD, index, working tree; `-c`/`-C` create branches); executes-config (`post-checkout`) | [commands/git-switch.md](commands/git-switch.md) | [git-switch](https://git-scm.com/docs/git-switch) |
| `git merge` | G2, G5 | mutates (commit, branch, index, working tree; leaves `MERGE_HEAD` on conflict); executes-config (hooks, merge drivers) | [commands/git-merge.md](commands/git-merge.md) | [git-merge](https://git-scm.com/docs/git-merge) |
| `git mergetool` | G2 | mutates (resolves conflicts; leaves `*.orig` unless `mergetool.keepBackup=false`); executes-config (runs the configured tool) | [commands/git-mergetool.md](commands/git-mergetool.md) | [git-mergetool](https://git-scm.com/docs/git-mergetool) |
| `git log` (also in Inspection and Comparison) | G5, G13, G14, G16, G21 | read (executes-config with `-p`: textconv and external diff drivers run by default; `--show-signature` runs the signing program) | [commands/git-log.md](commands/git-log.md) | [git-log](https://git-scm.com/docs/git-log) |
| `git stash` | G8 | read (`list`, `show`); mutates (`push`, `save`, `pop`, `apply`, `drop`, `clear`, `branch`, `store`, `import`) | [commands/git-stash.md](commands/git-stash.md) | [git-stash](https://git-scm.com/docs/git-stash) |
| `git tag` | G7 | read (`-l`, `--contains`, `--points-at`); executes-config (`-v` runs the signing program); mutates (create, `-d`, `-f`) | [commands/git-tag.md](commands/git-tag.md) | [git-tag](https://git-scm.com/docs/git-tag) |
| `git worktree` | G9, G22 | read (`list --porcelain`); mutates (`add`, `move`, `remove`, `prune`, `lock`, `unlock`, `repair`) | [commands/git-worktree.md](commands/git-worktree.md) | [git-worktree](https://git-scm.com/docs/git-worktree) |

## Sharing and Updating Projects

| Command or page | Areas | Safety class | Corpus | Official |
| --- | --- | --- | --- | --- |
| `git fetch` | G6, G7 | network + mutates (moves remote-tracking refs, writes `FETCH_HEAD`, `--prune`/`--prune-tags` delete refs, runs `git maintenance run --auto` unless `--no-auto-maintenance`) | [commands/git-fetch.md](commands/git-fetch.md) | [git-fetch](https://git-scm.com/docs/git-fetch) |
| `git pull` | G5, G6 | network + mutates (fetch, then merge or rebase into the current branch) | [areas/branches-remotes-tags.md](areas/branches-remotes-tags.md) | [git-pull](https://git-scm.com/docs/git-pull) |
| `git push` | G5, G6, G7, P2 | network + mutates (remote refs; `--delete`, `--force-with-lease`); executes-config (`pre-push`); `--dry-run` still contacts the remote | [commands/git-push.md](commands/git-push.md) | [git-push](https://git-scm.com/docs/git-push) |
| `git remote` | G6 | read (`-v`, `get-url`, `show -n`); network (`show`, `prune --dry-run`, `set-head --auto`); mutates (`add`, `rename`, `remove`, `set-url`, `set-branches`, `set-head`, `prune`, `update`) | [commands/git-remote.md](commands/git-remote.md) | [git-remote](https://git-scm.com/docs/git-remote) |
| `git submodule` | G10, G19 | read (`status`, `summary`, `foreach` only with a read command); mutates (`init`, `deinit`, `sync`, `absorbgitdirs`, `set-url`, `set-branch`); network + mutates (`add`, `update`) | [commands/git-submodule.md](commands/git-submodule.md) | [git-submodule](https://git-scm.com/docs/git-submodule) |

## Inspection and Comparison

Also in this category: `git log` (listed under Branching and Merging) and `git diff` (listed under Basic Snapshotting).

| Command or page | Areas | Safety class | Corpus | Official |
| --- | --- | --- | --- | --- |
| `git show` | G14, G16, G21 | read (executes-config: textconv and external diff drivers by default; `--show-signature`) | [commands/git-show.md](commands/git-show.md) | [git-show](https://git-scm.com/docs/git-show) |
| `git difftool` | G3 | read + executes-config (launches the configured diff tool) | [areas/worktree-index-rules.md](areas/worktree-index-rules.md) | [git-difftool](https://git-scm.com/docs/git-difftool) |
| `git range-diff` | G5, G21 | read | [commands/git-range-diff.md](commands/git-range-diff.md) | [git-range-diff](https://git-scm.com/docs/git-range-diff) |
| `git shortlog` | G13 | read | [commands/git-shortlog.md](commands/git-shortlog.md) | [git-shortlog](https://git-scm.com/docs/git-shortlog) |
| `git describe` | G7, G21 | read (writes-local-state with `--dirty`/`--broken`: index refresh) | [commands/git-describe.md](commands/git-describe.md) | [git-describe](https://git-scm.com/docs/git-describe) |

## Patching

Also in this category: `git diff` (listed under Basic Snapshotting).

| Command or page | Areas | Safety class | Corpus | Official |
| --- | --- | --- | --- | --- |
| `git apply` (also in Email) | G2, G3 | read (`--check`, `--stat`, `--numstat`, `--summary`); mutates (working tree, index with `--index`/`--cached`; `--reject` writes `*.rej`) | [commands/git-apply.md](commands/git-apply.md) | [git-apply](https://git-scm.com/docs/git-apply) |
| `git cherry-pick` | G2, G16 | mutates (commits, branch, index, working tree; `sequencer/` on conflict) | [commands/git-cherry-pick.md](commands/git-cherry-pick.md) | [git-cherry-pick](https://git-scm.com/docs/git-cherry-pick) |
| `git rebase` | G2, G5, G16 | mutates (rewrites the branch; `rebase-merge/` or `rebase-apply/` on stop); executes-config (hooks, `exec` lines) | [commands/git-rebase.md](commands/git-rebase.md) | [git-rebase](https://git-scm.com/docs/git-rebase) |
| `git revert` | G2 | mutates (new commits; `sequencer/` on conflict) | [commands/git-revert.md](commands/git-revert.md) | [git-revert](https://git-scm.com/docs/git-revert) |

## Debugging

| Command or page | Areas | Safety class | Corpus | Official |
| --- | --- | --- | --- | --- |
| `git bisect` | G2, G15, G21 | read (`log`, `terms`); mutates (`start`, `good`, `bad`, `skip`, `reset`, `replay` check out commits and write `refs/bisect/*`, `BISECT_LOG`; `--no-checkout` still writes refs); executes-config (`run` executes a script, `visualize` opens gitk) | [commands/git-bisect.md](commands/git-bisect.md) | [git-bisect](https://git-scm.com/docs/git-bisect) |
| `git blame` | G21 | read (executes-config: `diff.<driver>.textconv` runs by default; pass `--no-textconv`) | [commands/git-blame.md](commands/git-blame.md) | [git-blame](https://git-scm.com/docs/git-blame) |
| `git grep` | G14, G21 | read (executes-config with `--textconv` or `-O`/`--open-files-in-pager`; `--untracked --no-exclude-standard` reaches ignored secrets) | [commands/git-grep.md](commands/git-grep.md) | [git-grep](https://git-scm.com/docs/git-grep) |

## Email

Also in this category: `git apply` (listed under Patching).

| Command or page | Areas | Safety class | Corpus | Official |
| --- | --- | --- | --- | --- |
| `git am` | G2 | mutates (commits; `rebase-apply/` on stop); executes-config (`applypatch-msg`, `pre-applypatch`, `post-applypatch`) | [commands/git-am.md](commands/git-am.md) | [git-am](https://git-scm.com/docs/git-am) |
| `git imap-send` | G12 | network + executes-config (`imap.tunnel` runs a command; `imap.pass` holds a plaintext secret) | [areas/config-links-identity.md](areas/config-links-identity.md) | [git-imap-send](https://git-scm.com/docs/git-imap-send) |
| `git format-patch` | G2 | writes-local-state (writes `*.patch` files in the current directory or `-o`) | [areas/repository-and-operations.md](areas/repository-and-operations.md) | [git-format-patch](https://git-scm.com/docs/git-format-patch) |
| `git send-email` | G12 | network + executes-config (`sendemail.smtpServer` may be a command, `sendemail-validate` hook; `sendemail.smtpPass` holds a plaintext secret) | [areas/config-links-identity.md](areas/config-links-identity.md) | [git-send-email](https://git-scm.com/docs/git-send-email) |
| `git request-pull` | — | read + network (checks the remote for the commit) | — (no footprint: prints a pull-request summary) | [git-request-pull](https://git-scm.com/docs/git-request-pull) |

## External Systems

| Command or page | Areas | Safety class | Corpus | Official |
| --- | --- | --- | --- | --- |
| `git svn` | G15, G18 | network + mutates (`refs/remotes/git-svn`, `.git/svn/`); read (`info`, `log` from local metadata) | [commands/git-svn.md](commands/git-svn.md) | [git-svn](https://git-scm.com/docs/git-svn) |
| `git fast-import` | G17, G18 | mutates (writes packs and refs; `--export-marks` writes a marks file) | [areas/footprints-and-references.md](areas/footprints-and-references.md) | [git-fast-import](https://git-scm.com/docs/git-fast-import) |

## Administration

| Command or page | Areas | Safety class | Corpus | Official |
| --- | --- | --- | --- | --- |
| `git clean` | G3, G4, G10, G20 | read with `-n`/`--dry-run`; mutates (`-f` deletes untracked files, `-x` ignored files, `-d` directories) | [commands/git-clean.md](commands/git-clean.md) | [git-clean](https://git-scm.com/docs/git-clean) |
| `git gc` | G16, G17 | mutates (packs objects and refs, prunes unreachable objects, expires reflogs, runs `rerere gc`); executes-config (`pre-auto-gc` with `--auto`) | [commands/git-gc.md](commands/git-gc.md) | [git-gc](https://git-scm.com/docs/git-gc) |
| `git fsck` | G16, G17 | read (writes-local-state with `--lost-found`: writes `.git/lost-found/`) | [commands/git-fsck.md](commands/git-fsck.md) | [git-fsck](https://git-scm.com/docs/git-fsck) |
| `git reflog` | G16 | read (`show`, `list`, `exists`); mutates (`expire`, `delete`, `drop`) | [commands/git-reflog.md](commands/git-reflog.md) | [git-reflog](https://git-scm.com/docs/git-reflog) |
| `git filter-branch` | G14, G15 | mutates (rewrites history, leaves `refs/original/`); executes-config (runs the filter scripts); superseded by `git filter-repo` per its own WARNING | [commands/git-filter-branch.md](commands/git-filter-branch.md) | [git-filter-branch](https://git-scm.com/docs/git-filter-branch) |
| `git instaweb` | G18 | writes-local-state (writes `.git/gitweb/`) + network (starts a web server) + executes-config (`instaweb.browser`, `instaweb.httpd`) | [areas/footprints-and-references.md](areas/footprints-and-references.md) | [git-instaweb](https://git-scm.com/docs/git-instaweb) |
| `git archive` | G4, G18 | read (writes the archive to `-o` or stdout; executes-config: `tar.<format>.command`; `export-subst` only expands placeholders; network with `--remote`) | [commands/git-archive.md](commands/git-archive.md) | [git-archive](https://git-scm.com/docs/git-archive) |
| `git bundle` | G16, G17 | read (`verify`, `list-heads`); writes-local-state (`create` writes a bundle file); mutates (`unbundle` writes objects) | [commands/git-bundle.md](commands/git-bundle.md) | [git-bundle](https://git-scm.com/docs/git-bundle) |

## Server Admin

| Command or page | Areas | Safety class | Corpus | Official |
| --- | --- | --- | --- | --- |
| `git daemon` | G18 | network (starts a server that exports repositories marked `git-daemon-export-ok`) | [commands/git-daemon.md](commands/git-daemon.md) | [git-daemon](https://git-scm.com/docs/git-daemon) |
| `git update-server-info` | G18 | mutates (rewrites `info/refs` and `objects/info/packs`) | [commands/git-update-server-info.md](commands/git-update-server-info.md) | [git-update-server-info](https://git-scm.com/docs/git-update-server-info) |

## Plumbing Commands

| Command or page | Areas | Safety class | Corpus | Official |
| --- | --- | --- | --- | --- |
| `git cat-file` | G14, G16, G17 | read (executes-config with `--textconv` or `--filters`) | [commands/git-cat-file.md](commands/git-cat-file.md) | [git-cat-file](https://git-scm.com/docs/git-cat-file) |
| `git check-ignore` | G4 | read | [commands/git-check-ignore.md](commands/git-check-ignore.md) | [git-check-ignore](https://git-scm.com/docs/git-check-ignore) |
| `git checkout-index` | G3 | mutates (writes working tree files) | [areas/worktree-index-rules.md](areas/worktree-index-rules.md) | [git-checkout-index](https://git-scm.com/docs/git-checkout-index) |
| `git commit-tree` | G16, G17 | mutates (writes a commit object; allowed only after the object census) | [areas/object-store.md](areas/object-store.md) | [git-commit-tree](https://git-scm.com/docs/git-commit-tree) |
| `git count-objects` | G17 | read | [commands/git-count-objects.md](commands/git-count-objects.md) | [git-count-objects](https://git-scm.com/docs/git-count-objects) |
| `git diff-index` | G3 | read | [areas/worktree-index-rules.md](areas/worktree-index-rules.md) | [git-diff-index](https://git-scm.com/docs/git-diff-index) |
| `git for-each-ref` | G5, G6, G7, G15 | read | [commands/git-for-each-ref.md](commands/git-for-each-ref.md) | [git-for-each-ref](https://git-scm.com/docs/git-for-each-ref) |
| `git hash-object` | G17 | read (computes the ID only); mutates with `-w` (writes the object) | [commands/git-hash-object.md](commands/git-hash-object.md) | [git-hash-object](https://git-scm.com/docs/git-hash-object) |
| `git ls-files` | G3, G4, G20 | read | [commands/git-ls-files.md](commands/git-ls-files.md) | [git-ls-files](https://git-scm.com/docs/git-ls-files) |
| `git ls-tree` | G3, G14 | read | [areas/history-and-secrets.md](areas/history-and-secrets.md) | [git-ls-tree](https://git-scm.com/docs/git-ls-tree) |
| `git merge-base` | G5 | read | [commands/git-merge-base.md](commands/git-merge-base.md) | [git-merge-base](https://git-scm.com/docs/git-merge-base) |
| `git read-tree` | G3 | mutates (index; working tree with `-u`) | [areas/worktree-index-rules.md](areas/worktree-index-rules.md) | [git-read-tree](https://git-scm.com/docs/git-read-tree) |
| `git rev-list` | G5, G14, G16, G17 | read | [commands/git-rev-list.md](commands/git-rev-list.md) | [git-rev-list](https://git-scm.com/docs/git-rev-list) |
| `git rev-parse` | G1, G9 | read | [commands/git-rev-parse.md](commands/git-rev-parse.md) | [git-rev-parse](https://git-scm.com/docs/git-rev-parse) |
| `git show-ref` | G5, G7, G15 | read | [commands/git-show-ref.md](commands/git-show-ref.md) | [git-show-ref](https://git-scm.com/docs/git-show-ref) |
| `git symbolic-ref` | G6, G15 | read (query); mutates (set, `--delete`) | [commands/git-symbolic-ref.md](commands/git-symbolic-ref.md) | [git-symbolic-ref](https://git-scm.com/docs/git-symbolic-ref) |
| `git update-index` | G3 | mutates (`--assume-unchanged`, `--skip-worktree`, `--add`, `--remove`, `--split-index`, `--untracked-cache`); writes-local-state (`--refresh`) | [commands/git-update-index.md](commands/git-update-index.md) | [git-update-index](https://git-scm.com/docs/git-update-index) |
| `git update-ref` | G15, G16 | mutates (creates, moves or deletes refs; `--stdin` transactions) | [commands/git-update-ref.md](commands/git-update-ref.md) | [git-update-ref](https://git-scm.com/docs/git-update-ref) |
| `git verify-pack` | G17 | read | [commands/git-verify-pack.md](commands/git-verify-pack.md) | [git-verify-pack](https://git-scm.com/docs/git-verify-pack) |
| `git write-tree` | G17 | mutates (writes a tree object from the index) | [areas/object-store.md](areas/object-store.md) | [git-write-tree](https://git-scm.com/docs/git-write-tree) |

## Guides

| Command or page | Areas | Safety class | Corpus | Official |
| --- | --- | --- | --- | --- |
| `gitattributes` | G4, G12 | reference-only | [areas/worktree-index-rules.md](areas/worktree-index-rules.md) | [gitattributes](https://git-scm.com/docs/gitattributes) |
| `gitcli` | G1–G22 (command form) | reference-only | [audit-contract.md](audit-contract.md) section 3 | [gitcli](https://git-scm.com/docs/gitcli) |
| `giteveryday` | — | reference-only | — (no footprint: general tutorial) | [giteveryday](https://git-scm.com/docs/giteveryday) |
| `gitfaq` | G5, G6, G11, G12 | reference-only | [areas/branches-remotes-tags.md](areas/branches-remotes-tags.md) | [gitfaq](https://git-scm.com/docs/gitfaq) |
| `gitglossary` | G16, G17 | reference-only | [areas/refs-reflogs-recovery.md](areas/refs-reflogs-recovery.md) | [gitglossary](https://git-scm.com/docs/gitglossary) |
| `githooks` | G12 | reference-only | [areas/config-links-identity.md](areas/config-links-identity.md) | [githooks](https://git-scm.com/docs/githooks) |
| `gitignore` | G4, G20 | reference-only | [areas/worktree-index-rules.md](areas/worktree-index-rules.md) | [gitignore](https://git-scm.com/docs/gitignore) |
| `gitmodules` | G10, G19 | reference-only | [areas/stashes-worktrees-submodules.md](areas/stashes-worktrees-submodules.md) | [gitmodules](https://git-scm.com/docs/gitmodules) |
| `gitrevisions` | G16, G21 | reference-only | [areas/refs-reflogs-recovery.md](areas/refs-reflogs-recovery.md) | [gitrevisions](https://git-scm.com/docs/gitrevisions) |
| `gitsubmodules` | G10 | reference-only | [areas/stashes-worktrees-submodules.md](areas/stashes-worktrees-submodules.md) | [gitsubmodules](https://git-scm.com/docs/gitsubmodules) |
| `gittutorial` | — | reference-only | — (no footprint: general tutorial) | [gittutorial](https://git-scm.com/docs/gittutorial) |
| `gitworkflows` | — | reference-only | — (no footprint: workflow policy guide) | [gitworkflows](https://git-scm.com/docs/gitworkflows) |

## Main porcelain outside the index

| Command or page | Areas | Safety class | Corpus | Official |
| --- | --- | --- | --- | --- |
| `git backfill` | G1, G17 | network + mutates (downloads missing objects into a partial clone) | [areas/repository-and-operations.md](areas/repository-and-operations.md) | [git-backfill](https://git-scm.com/docs/git-backfill) |
| `git citool` | G3 | mutates (commits through a GUI) | [areas/worktree-index-rules.md](areas/worktree-index-rules.md) | [git-citool](https://git-scm.com/docs/git-citool) |
| `git gui` | G3 | mutates (stages and commits through a GUI) | [areas/worktree-index-rules.md](areas/worktree-index-rules.md) | [git-gui](https://git-scm.com/docs/git-gui) |
| `git history` (experimental) | G5, G16 | mutates (rewrites commits and, by default, every descendant branch); read with `--dry-run` | [areas/refs-reflogs-recovery.md](areas/refs-reflogs-recovery.md) | [git-history](https://git-scm.com/docs/git-history) |
| `git maintenance` | G11, G17 | mutates (`run`); mutates outside the repository (`register`, `unregister`, `start`, `stop` edit global config and the OS scheduler) | [commands/git-maintenance.md](commands/git-maintenance.md) | [git-maintenance](https://git-scm.com/docs/git-maintenance) |
| `git sparse-checkout` | G1, G3 | read (`list`, `check-rules`); mutates (`set`, `add`, `init`, `reapply`, `disable`) | [commands/git-sparse-checkout.md](commands/git-sparse-checkout.md) | [git-sparse-checkout](https://git-scm.com/docs/git-sparse-checkout) |
| `gitk` | G21 | read (GUI; writes its own settings file outside the repository) | [areas/tracing.md](areas/tracing.md) | [gitk](https://git-scm.com/docs/gitk) |
| `scalar` | G1, G11, G17 | read (`list`); mutates (`register`, `clone`, `reconfigure`, `unregister`, `delete` change repositories, global config and schedules); network (`clone`) | [areas/repository-and-operations.md](areas/repository-and-operations.md) | [scalar](https://git-scm.com/docs/scalar) |

## Ancillary commands: manipulators

| Command or page | Areas | Safety class | Corpus | Official |
| --- | --- | --- | --- | --- |
| `git fast-export` | G14 | read (writes-local-state with `--export-marks`) | [commands/git-fast-export.md](commands/git-fast-export.md) | [git-fast-export](https://git-scm.com/docs/git-fast-export) |
| `git pack-refs` | G15, G17 | mutates (moves loose refs into `packed-refs`) | [commands/git-pack-refs.md](commands/git-pack-refs.md) | [git-pack-refs](https://git-scm.com/docs/git-pack-refs) |
| `git prune` | G16, G17 | read with `-n`/`--dry-run`; mutates (deletes unreachable loose objects) | [commands/git-prune.md](commands/git-prune.md) | [git-prune](https://git-scm.com/docs/git-prune) |
| `git refs` | G15 | read (`list`, `exists`, `verify`); mutates (`migrate`, `optimize`); read with `migrate --dry-run` | [areas/refs-reflogs-recovery.md](areas/refs-reflogs-recovery.md) | [git-refs](https://git-scm.com/docs/git-refs) |
| `git repack` | G17 | mutates (rewrites packs; `-d` deletes redundant packs and loose objects) | [commands/git-repack.md](commands/git-repack.md) | [git-repack](https://git-scm.com/docs/git-repack) |
| `git replace` | G15 | read (`-l`, `--format`); mutates (create, `-d`, `--edit`, `--graft`, `--convert-graft-file`) | [commands/git-replace.md](commands/git-replace.md) | [git-replace](https://git-scm.com/docs/git-replace) |

## Ancillary commands: interrogators

| Command or page | Areas | Safety class | Corpus | Official |
| --- | --- | --- | --- | --- |
| `git annotate` | G21 | read (executes-config: textconv by default, as `git blame`) | [areas/tracing.md](areas/tracing.md) | [git-annotate](https://git-scm.com/docs/git-annotate) |
| `git diagnose` | G1, G17 | writes-local-state (writes a zip archive of repository metadata) | [areas/repository-and-operations.md](areas/repository-and-operations.md) | [git-diagnose](https://git-scm.com/docs/git-diagnose) |
| `git merge-tree` | G5 | read (`--no-messages`, `--name-only`); mutates with `--write-tree` (writes tree objects; allowed only after the object census) | [commands/git-merge-tree.md](commands/git-merge-tree.md) | [git-merge-tree](https://git-scm.com/docs/git-merge-tree) |
| `git rerere` | G12 | read (`status`, `diff`, `remaining`); mutates (`clear`, `forget`, `gc`) | [commands/git-rerere.md](commands/git-rerere.md) | [git-rerere](https://git-scm.com/docs/git-rerere) |
| `git show-branch` | G5 | read | [areas/branches-remotes-tags.md](areas/branches-remotes-tags.md) | [git-show-branch](https://git-scm.com/docs/git-show-branch) |
| `git verify-commit` | G13 | read + executes-config (runs the signing program) | [commands/git-verify-commit.md](commands/git-verify-commit.md) | [git-verify-commit](https://git-scm.com/docs/git-verify-commit) |
| `git verify-tag` | G7, G13 | read + executes-config (runs the signing program) | [commands/git-verify-tag.md](commands/git-verify-tag.md) | [git-verify-tag](https://git-scm.com/docs/git-verify-tag) |
| `git version` | G1 | read | [areas/repository-and-operations.md](areas/repository-and-operations.md) | [git-version](https://git-scm.com/docs/git-version) |
| `git whatchanged` (deprecated) | G21 | read | [areas/tracing.md](areas/tracing.md) | [git-whatchanged](https://git-scm.com/docs/git-whatchanged) |
| `gitweb` | G18 | network (CGI web frontend served by a web server; nothing to run in an audit) | [areas/footprints-and-references.md](areas/footprints-and-references.md) | [gitweb](https://git-scm.com/docs/gitweb) |

## Interacting with others

| Command or page | Areas | Safety class | Corpus | Official |
| --- | --- | --- | --- | --- |
| `git archimport` | G15, G18 | network + mutates (imports commits and refs) | [areas/footprints-and-references.md](areas/footprints-and-references.md) | [git-archimport](https://git-scm.com/docs/git-archimport) |
| `git cvsexportcommit` | G18 | mutates (writes into a CVS checkout outside the repository) | [areas/footprints-and-references.md](areas/footprints-and-references.md) | [git-cvsexportcommit](https://git-scm.com/docs/git-cvsexportcommit) |
| `git cvsimport` | G15, G18 | network + mutates (imports commits and refs) | [areas/footprints-and-references.md](areas/footprints-and-references.md) | [git-cvsimport](https://git-scm.com/docs/git-cvsimport) |
| `git cvsserver` | G18 | network (serves the repository over the CVS protocol) | [areas/footprints-and-references.md](areas/footprints-and-references.md) | [git-cvsserver](https://git-scm.com/docs/git-cvsserver) |
| `git p4` | G15, G18 | network + mutates (`refs/remotes/p4/*`; `submit` writes to Perforce) | [areas/footprints-and-references.md](areas/footprints-and-references.md) | [git-p4](https://git-scm.com/docs/git-p4) |
| `git quiltimport` | G18 | mutates (commits a quilt patch series); read with `--dry-run` | [areas/footprints-and-references.md](areas/footprints-and-references.md) | [git-quiltimport](https://git-scm.com/docs/git-quiltimport) |

## Low-level commands: manipulation

| Command or page | Areas | Safety class | Corpus | Official |
| --- | --- | --- | --- | --- |
| `git commit-graph` | G17 | read (`verify`); mutates (`write`) | [commands/git-commit-graph.md](commands/git-commit-graph.md) | [git-commit-graph](https://git-scm.com/docs/git-commit-graph) |
| `git index-pack` | G17 | mutates (writes `.idx`, and `.pack` with `--stdin`); read with `--verify` | [areas/object-store.md](areas/object-store.md) | [git-index-pack](https://git-scm.com/docs/git-index-pack) |
| `git merge-file` | G2, G3 | mutates (overwrites the current file); read with `-p`/`--stdout` | [areas/worktree-index-rules.md](areas/worktree-index-rules.md) | [git-merge-file](https://git-scm.com/docs/git-merge-file) |
| `git merge-index` | G3 | mutates (runs a merge program on unmerged index entries) | [areas/worktree-index-rules.md](areas/worktree-index-rules.md) | [git-merge-index](https://git-scm.com/docs/git-merge-index) |
| `git mktag` | G7, G17 | mutates (writes a tag object) | [areas/object-store.md](areas/object-store.md) | [git-mktag](https://git-scm.com/docs/git-mktag) |
| `git mktree` | G17 | mutates (writes a tree object) | [areas/object-store.md](areas/object-store.md) | [git-mktree](https://git-scm.com/docs/git-mktree) |
| `git multi-pack-index` | G17 | read (`verify`); mutates (`write`, `expire`, `repack`) | [commands/git-multi-pack-index.md](commands/git-multi-pack-index.md) | [git-multi-pack-index](https://git-scm.com/docs/git-multi-pack-index) |
| `git pack-objects` | G17 | writes-local-state (writes packs at the given base name, or to stdout with `--stdout`) | [areas/object-store.md](areas/object-store.md) | [git-pack-objects](https://git-scm.com/docs/git-pack-objects) |
| `git prune-packed` | G17 | mutates (deletes loose objects already in packs); read with `-n` | [areas/object-store.md](areas/object-store.md) | [git-prune-packed](https://git-scm.com/docs/git-prune-packed) |
| `git replay` (experimental) | G5, G21 | mutates (writes commits and, by default, updates refs atomically); `--ref-action=print` still writes commit objects | [areas/branches-remotes-tags.md](areas/branches-remotes-tags.md) | [git-replay](https://git-scm.com/docs/git-replay) |
| `git unpack-objects` | G17 | mutates (writes loose objects from a pack); read with `-n` | [areas/object-store.md](areas/object-store.md) | [git-unpack-objects](https://git-scm.com/docs/git-unpack-objects) |

## Low-level commands: interrogation

| Command or page | Areas | Safety class | Corpus | Official |
| --- | --- | --- | --- | --- |
| `git cherry` | G5 | read | [commands/git-cherry.md](commands/git-cherry.md) | [git-cherry](https://git-scm.com/docs/git-cherry) |
| `git diff-files` | G3 | read | [areas/worktree-index-rules.md](areas/worktree-index-rules.md) | [git-diff-files](https://git-scm.com/docs/git-diff-files) |
| `git diff-pairs` | — | read | — (no footprint: diff plumbing fed by `diff-tree -z`) | [git-diff-pairs](https://git-scm.com/docs/git-diff-pairs) |
| `git diff-tree` | G14, G21 | read | [areas/history-and-secrets.md](areas/history-and-secrets.md) | [git-diff-tree](https://git-scm.com/docs/git-diff-tree) |
| `git for-each-repo` | G11, G17 | executes-config (runs the given git command in every repository listed by a config key, such as `maintenance.repo`; class of that command applies) | [areas/config-links-identity.md](areas/config-links-identity.md) | [git-for-each-repo](https://git-scm.com/docs/git-for-each-repo) |
| `git format-rev` (experimental) | G21 | read | [areas/tracing.md](areas/tracing.md) | [git-format-rev](https://git-scm.com/docs/git-format-rev) |
| `git get-tar-commit-id` | G19 | read (commit ID of an archive made by `git archive`) | [areas/footprints-and-references.md](areas/footprints-and-references.md) | [git-get-tar-commit-id](https://git-scm.com/docs/git-get-tar-commit-id) |
| `git last-modified` (experimental) | G21 | read | [areas/tracing.md](areas/tracing.md) | [git-last-modified](https://git-scm.com/docs/git-last-modified) |
| `git ls-remote` | G6, G7, G19 | read + network | [commands/git-ls-remote.md](commands/git-ls-remote.md) | [git-ls-remote](https://git-scm.com/docs/git-ls-remote) |
| `git name-rev` | G16, G21 | read | [commands/git-name-rev.md](commands/git-name-rev.md) | [git-name-rev](https://git-scm.com/docs/git-name-rev) |
| `git pack-redundant` (deprecated) | G17 | read | [areas/object-store.md](areas/object-store.md) | [git-pack-redundant](https://git-scm.com/docs/git-pack-redundant) |
| `git repo` (experimental) | G1, G17 | read (`info`, `structure`) | [areas/repository-and-operations.md](areas/repository-and-operations.md) | [git-repo](https://git-scm.com/docs/git-repo) |
| `git show-index` | G17 | read | [areas/object-store.md](areas/object-store.md) | [git-show-index](https://git-scm.com/docs/git-show-index) |
| `git unpack-file` | G17 | writes-local-state (writes a `.merge_file_*` temporary file in the current directory) | [areas/object-store.md](areas/object-store.md) | [git-unpack-file](https://git-scm.com/docs/git-unpack-file) |
| `git var` | G11, G12 | read | [commands/git-var.md](commands/git-var.md) | [git-var](https://git-scm.com/docs/git-var) |

## Low-level commands: syncing repositories

| Command or page | Areas | Safety class | Corpus | Official |
| --- | --- | --- | --- | --- |
| `git fetch-pack` | — | network + mutates (writes received objects) | — (no footprint of its own: transport backend of `git fetch`) | [git-fetch-pack](https://git-scm.com/docs/git-fetch-pack) |
| `git http-backend` | G18 | network (server-side CGI; `http.getanyfile`, `http.receivepack`) | [areas/footprints-and-references.md](areas/footprints-and-references.md) | [git-http-backend](https://git-scm.com/docs/git-http-backend) |
| `git send-pack` | — | network + mutates (updates refs on the remote) | — (no footprint of its own: transport backend of `git push`) | [git-send-pack](https://git-scm.com/docs/git-send-pack) |
| `git http-fetch` | — | network + mutates (writes received objects) | — (no footprint of its own: dumb HTTP transport) | [git-http-fetch](https://git-scm.com/docs/git-http-fetch) |
| `git http-push` | — | network + mutates (updates refs on the remote) | — (no footprint of its own: HTTP/DAV transport) | [git-http-push](https://git-scm.com/docs/git-http-push) |
| `git receive-pack` | G18 | network (server side of push; `receive.*` settings, server hooks) | [areas/footprints-and-references.md](areas/footprints-and-references.md) | [git-receive-pack](https://git-scm.com/docs/git-receive-pack) |
| `git shell` | — | network (restricted login shell on a server) | — (no footprint: server login shell outside any repository) | [git-shell](https://git-scm.com/docs/git-shell) |
| `git upload-archive` | G18 | network (server side of `git archive --remote`; `uploadarchive.allowUnreachable`) | [areas/footprints-and-references.md](areas/footprints-and-references.md) | [git-upload-archive](https://git-scm.com/docs/git-upload-archive) |
| `git upload-pack` | G1, G18 | network (server side of fetch; SECURITY section on untrusted repositories; `uploadpack.*`) | [areas/footprints-and-references.md](areas/footprints-and-references.md) | [git-upload-pack](https://git-scm.com/docs/git-upload-pack) |

## Low-level commands: internal helpers

| Command or page | Areas | Safety class | Corpus | Official |
| --- | --- | --- | --- | --- |
| `git check-attr` | G4 | read | [commands/git-check-attr.md](commands/git-check-attr.md) | [git-check-attr](https://git-scm.com/docs/git-check-attr) |
| `git check-mailmap` | G13 | read | [commands/git-check-mailmap.md](commands/git-check-mailmap.md) | [git-check-mailmap](https://git-scm.com/docs/git-check-mailmap) |
| `git check-ref-format` | G5, G15 | read | [areas/branches-remotes-tags.md](areas/branches-remotes-tags.md) | [git-check-ref-format](https://git-scm.com/docs/git-check-ref-format) |
| `git column` | — | read | — (no footprint: output formatting) | [git-column](https://git-scm.com/docs/git-column) |
| `git credential` | G11, G12 | executes-config (`fill` runs every configured helper and may prompt); mutates outside the repository (`approve`, `reject` store or erase in helpers) | [commands/git-credential.md](commands/git-credential.md) | [git-credential](https://git-scm.com/docs/git-credential) |
| `git credential-cache` | G12 | executes-config + mutates outside the repository (in-memory daemon and its socket) | [areas/config-links-identity.md](areas/config-links-identity.md) | [git-credential-cache](https://git-scm.com/docs/git-credential-cache) |
| `git credential-store` | G12 | mutates outside the repository (plaintext `~/.git-credentials` or `--file`) | [areas/config-links-identity.md](areas/config-links-identity.md) | [git-credential-store](https://git-scm.com/docs/git-credential-store) |
| `git fmt-merge-msg` | — | read | — (no footprint: merge message helper) | [git-fmt-merge-msg](https://git-scm.com/docs/git-fmt-merge-msg) |
| `git hook` | G12 | read (`list`); executes-config (`run` executes the hook) | [commands/git-hook.md](commands/git-hook.md) | [git-hook](https://git-scm.com/docs/git-hook) |
| `git interpret-trailers` | G13 | read (`--parse`, stdout); mutates with `--in-place` | [commands/git-interpret-trailers.md](commands/git-interpret-trailers.md) | [git-interpret-trailers](https://git-scm.com/docs/git-interpret-trailers) |
| `git mailinfo` | — | writes-local-state (writes the message and patch files it is given) | — (no footprint of its own: email helper of `git am`) | [git-mailinfo](https://git-scm.com/docs/git-mailinfo) |
| `git mailsplit` | — | writes-local-state (writes one file per message) | — (no footprint of its own: mbox helper of `git am`) | [git-mailsplit](https://git-scm.com/docs/git-mailsplit) |
| `git merge-one-file` | — | mutates (index and working tree) | — (no footprint of its own: helper of `git merge-index`) | [git-merge-one-file](https://git-scm.com/docs/git-merge-one-file) |
| `git patch-id` | G5 | read | [commands/git-patch-id.md](commands/git-patch-id.md) | [git-patch-id](https://git-scm.com/docs/git-patch-id) |
| `git sh-i18n` | — | reference-only | — (no footprint: shell i18n internals) | [git-sh-i18n](https://git-scm.com/docs/git-sh-i18n) |
| `git sh-setup` | — | reference-only | — (no footprint: shell script internals) | [git-sh-setup](https://git-scm.com/docs/git-sh-setup) |
| `git stripspace` | — | read | — (no footprint: message whitespace tooling) | [git-stripspace](https://git-scm.com/docs/git-stripspace) |
| `git url-parse` | G6, G19 | read (splits a Git URL into components) | [areas/branches-remotes-tags.md](areas/branches-remotes-tags.md) | [git-url-parse](https://git-scm.com/docs/git-url-parse) |

## Guides outside the index

| Command or page | Areas | Safety class | Corpus | Official |
| --- | --- | --- | --- | --- |
| `gitcore-tutorial` | — | reference-only | — (no footprint: developer tutorial) | [gitcore-tutorial](https://git-scm.com/docs/gitcore-tutorial) |
| `gitcredentials` | G11, G12 | reference-only | [areas/config-links-identity.md](areas/config-links-identity.md) | [gitcredentials](https://git-scm.com/docs/gitcredentials) |
| `gitcvs-migration` | — | reference-only | — (no footprint: CVS migration tutorial) | [gitcvs-migration](https://git-scm.com/docs/gitcvs-migration) |
| `gitdiffcore` | G21 | reference-only (pickaxe `-S`/`-G`, rename and copy detection) | [areas/tracing.md](areas/tracing.md) | [gitdiffcore](https://git-scm.com/docs/gitdiffcore) |
| `gitnamespaces` | G15 | reference-only | [areas/refs-reflogs-recovery.md](areas/refs-reflogs-recovery.md) | [gitnamespaces](https://git-scm.com/docs/gitnamespaces) |
| `gitremote-helpers` | G6, G11 | reference-only | [areas/branches-remotes-tags.md](areas/branches-remotes-tags.md) | [gitremote-helpers](https://git-scm.com/docs/gitremote-helpers) |
| `gittutorial-2` | — | reference-only | — (no footprint: general tutorial) | [gittutorial-2](https://git-scm.com/docs/gittutorial-2) |

## Repository, command and file interfaces

| Command or page | Areas | Safety class | Corpus | Official |
| --- | --- | --- | --- | --- |
| `gitmailmap` | G13 | reference-only | [areas/config-links-identity.md](areas/config-links-identity.md) | [gitmailmap](https://git-scm.com/docs/gitmailmap) |
| `gitrepository-layout` | G1, G2, G15, G17, G18 | reference-only | [areas/repository-and-operations.md](areas/repository-and-operations.md) | [gitrepository-layout](https://git-scm.com/docs/gitrepository-layout) |

## File formats, protocols and developer interfaces

| Command or page | Areas | Safety class | Corpus | Official |
| --- | --- | --- | --- | --- |
| `gitformat-bundle` | G16, G17 | reference-only | [commands/git-bundle.md](commands/git-bundle.md) | [gitformat-bundle](https://git-scm.com/docs/gitformat-bundle) |
| `gitformat-chunk` | G17 | reference-only (chunk layout of commit-graph and multi-pack-index files) | [areas/object-store.md](areas/object-store.md) | [gitformat-chunk](https://git-scm.com/docs/gitformat-chunk) |
| `gitformat-commit-graph` | G17 | reference-only | [commands/git-commit-graph.md](commands/git-commit-graph.md) | [gitformat-commit-graph](https://git-scm.com/docs/gitformat-commit-graph) |
| `gitformat-index` | G1, G3 | reference-only (index versions, split index, untracked cache, fsmonitor extension) | [areas/worktree-index-rules.md](areas/worktree-index-rules.md) | [gitformat-index](https://git-scm.com/docs/gitformat-index) |
| `gitformat-pack` | G17 | reference-only | [areas/object-store.md](areas/object-store.md) | [gitformat-pack](https://git-scm.com/docs/gitformat-pack) |
| `gitformat-signature` | G7, G13 | reference-only | [areas/config-links-identity.md](areas/config-links-identity.md) | [gitformat-signature](https://git-scm.com/docs/gitformat-signature) |
| `gitprotocol-capabilities` | — | reference-only | — (no footprint: wire protocol) | [gitprotocol-capabilities](https://git-scm.com/docs/gitprotocol-capabilities) |
| `gitprotocol-common` | — | reference-only | — (no footprint: wire protocol) | [gitprotocol-common](https://git-scm.com/docs/gitprotocol-common) |
| `gitprotocol-http` | — | reference-only | — (no footprint: wire protocol) | [gitprotocol-http](https://git-scm.com/docs/gitprotocol-http) |
| `gitprotocol-pack` | — | reference-only | — (no footprint: wire protocol) | [gitprotocol-pack](https://git-scm.com/docs/gitprotocol-pack) |
| `gitprotocol-v2` | — | reference-only | — (no footprint: wire protocol) | [gitprotocol-v2](https://git-scm.com/docs/gitprotocol-v2) |

## Other git-scm pages

Pages on git-scm.com that git(1) does not list.

| Command or page | Areas | Safety class | Corpus | Official |
| --- | --- | --- | --- | --- |
| `gitdatamodel` | G15, G16, G17 | reference-only | [areas/object-store.md](areas/object-store.md) | [gitdatamodel](https://git-scm.com/docs/gitdatamodel) |
| `git fsmonitor--daemon` | G1, G12 | read (`status`); mutates (`start`, `run`, `stop` manage a background daemon and its IPC socket in `.git`) | [areas/repository-and-operations.md](areas/repository-and-operations.md) | [git-fsmonitor--daemon](https://git-scm.com/docs/git-fsmonitor--daemon) |
| Partial clone (technical design) | G1, G17 | reference-only | [areas/object-store.md](areas/object-store.md) | [partial-clone](https://git-scm.com/docs/partial-clone) |
| Hash function transition (technical design) | G1 | reference-only (`extensions.objectFormat`, `extensions.compatObjectFormat`) | [areas/repository-and-operations.md](areas/repository-and-operations.md) | [hash-function-transition](https://git-scm.com/docs/hash-function-transition) |

## Pro Git (book)

Every section is reference-only. Where the book and the reference manual disagree, the reference manual wins; conflicts are flagged in the row.

| Command or page | Areas | Safety class | Corpus | Official |
| --- | --- | --- | --- | --- |
| 1.1 About Version Control | — | reference-only | — (no footprint: introductory material) | [1.1](https://git-scm.com/book/en/v2/Getting-Started-About-Version-Control) |
| 1.2 A Short History of Git | — | reference-only | — (no footprint: introductory material) | [1.2](https://git-scm.com/book/en/v2/Getting-Started-A-Short-History-of-Git) |
| 1.3 What is Git? | — | reference-only | — (no footprint: introductory material) | [1.3](https://git-scm.com/book/en/v2/Getting-Started-What-is-Git%3F) |
| 1.4 The Command Line | — | reference-only | — (no footprint: introductory material) | [1.4](https://git-scm.com/book/en/v2/Getting-Started-The-Command-Line) |
| 1.5 Installing Git | G1 | reference-only | [areas/repository-and-operations.md](areas/repository-and-operations.md) — installed Git version and origin | [1.5](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git) |
| 1.6 First-Time Git Setup | G11, G13 | reference-only | [areas/config-links-identity.md](areas/config-links-identity.md) — config scopes, identity, default editor | [1.6](https://git-scm.com/book/en/v2/Getting-Started-First-Time-Git-Setup) |
| 1.7 Getting Help | — | reference-only | — (no footprint: help viewer) | [1.7](https://git-scm.com/book/en/v2/Getting-Started-Getting-Help) |
| 1.8 Summary | — | reference-only | — (no footprint: chapter summary) | [1.8](https://git-scm.com/book/en/v2/Getting-Started-Summary) |
| 2.1 Getting a Git Repository | G1 | reference-only | [areas/repository-and-operations.md](areas/repository-and-operations.md) — `init` and `clone` basics | [2.1](https://git-scm.com/book/en/v2/Git-Basics-Getting-a-Git-Repository) |
| 2.2 Recording Changes to the Repository | G3, G4 | reference-only | [areas/worktree-index-rules.md](areas/worktree-index-rules.md) — file states, `.gitignore` patterns, `rm --cached` | [2.2](https://git-scm.com/book/en/v2/Git-Basics-Recording-Changes-to-the-Repository) |
| 2.3 Viewing the Commit History | G21 | reference-only | [areas/tracing.md](areas/tracing.md) — `log` limiting and formatting | [2.3](https://git-scm.com/book/en/v2/Git-Basics-Viewing-the-Commit-History) |
| 2.4 Undoing Things | G3, G16 | reference-only | [areas/worktree-index-rules.md](areas/worktree-index-rules.md) — amend, unstage, restore | [2.4](https://git-scm.com/book/en/v2/Git-Basics-Undoing-Things) |
| 2.5 Working with Remotes | G6 | reference-only | [areas/branches-remotes-tags.md](areas/branches-remotes-tags.md) — remote show, rename, remove | [2.5](https://git-scm.com/book/en/v2/Git-Basics-Working-with-Remotes) |
| 2.6 Tagging | G7 | reference-only | [areas/branches-remotes-tags.md](areas/branches-remotes-tags.md) — lightweight vs annotated tags, pushing and deleting tags | [2.6](https://git-scm.com/book/en/v2/Git-Basics-Tagging) |
| 2.7 Git Aliases | G12 | reference-only | [areas/config-links-identity.md](areas/config-links-identity.md) — aliases, including `!` shell aliases | [2.7](https://git-scm.com/book/en/v2/Git-Basics-Git-Aliases) |
| 2.8 Summary | — | reference-only | — (no footprint: chapter summary) | [2.8](https://git-scm.com/book/en/v2/Git-Basics-Summary) |
| 3.1 Branches in a Nutshell | G5 | reference-only | [areas/branches-remotes-tags.md](areas/branches-remotes-tags.md) — branches as movable pointers, HEAD | [3.1](https://git-scm.com/book/en/v2/Git-Branching-Branches-in-a-Nutshell) |
| 3.2 Basic Branching and Merging | G2, G5 | reference-only | [areas/branches-remotes-tags.md](areas/branches-remotes-tags.md) — fast-forward vs merge commit, conflicts | [3.2](https://git-scm.com/book/en/v2/Git-Branching-Basic-Branching-and-Merging) |
| 3.3 Branch Management | G5 | reference-only | [areas/branches-remotes-tags.md](areas/branches-remotes-tags.md) — `--merged`/`--no-merged`, rename | [3.3](https://git-scm.com/book/en/v2/Git-Branching-Branch-Management) |
| 3.4 Branching Workflows | G5 | reference-only | [areas/branches-remotes-tags.md](areas/branches-remotes-tags.md) — long-running and topic branches | [3.4](https://git-scm.com/book/en/v2/Git-Branching-Branching-Workflows) |
| 3.5 Remote Branches | G5, G6 | reference-only | [areas/branches-remotes-tags.md](areas/branches-remotes-tags.md) — tracking, `push --delete` | [3.5](https://git-scm.com/book/en/v2/Git-Branching-Remote-Branches) |
| 3.6 Rebasing | G5, G16 | reference-only | [areas/branches-remotes-tags.md](areas/branches-remotes-tags.md) — the perils-of-rebasing rule | [3.6](https://git-scm.com/book/en/v2/Git-Branching-Rebasing) |
| 3.7 Summary | — | reference-only | — (no footprint: chapter summary) | [3.7](https://git-scm.com/book/en/v2/Git-Branching-Summary) |
| 4.1 The Protocols | G6 | reference-only | [areas/branches-remotes-tags.md](areas/branches-remotes-tags.md) — local, HTTP, SSH and git URL forms | [4.1](https://git-scm.com/book/en/v2/Git-on-the-Server-The-Protocols) |
| 4.2 Getting Git on a Server | G18 | reference-only | [areas/footprints-and-references.md](areas/footprints-and-references.md) — bare repositories, `--shared` | [4.2](https://git-scm.com/book/en/v2/Git-on-the-Server-Getting-Git-on-a-Server) |
| 4.3 Generating Your SSH Public Key | — | reference-only | — (no footprint: SSH key setup outside any repository) | [4.3](https://git-scm.com/book/en/v2/Git-on-the-Server-Generating-Your-SSH-Public-Key) |
| 4.4 Setting Up the Server | G18 | reference-only | [areas/footprints-and-references.md](areas/footprints-and-references.md) — server accounts, `git-shell` | [4.4](https://git-scm.com/book/en/v2/Git-on-the-Server-Setting-Up-the-Server) |
| 4.5 Git Daemon | G18 | reference-only | [commands/git-daemon.md](commands/git-daemon.md) — `git-daemon-export-ok` | [4.5](https://git-scm.com/book/en/v2/Git-on-the-Server-Git-Daemon) |
| 4.6 Smart HTTP | G18 | reference-only | [areas/footprints-and-references.md](areas/footprints-and-references.md) — `git http-backend` setup | [4.6](https://git-scm.com/book/en/v2/Git-on-the-Server-Smart-HTTP) |
| 4.7 GitWeb | G18 | reference-only | [areas/footprints-and-references.md](areas/footprints-and-references.md) — `instaweb`, `.git/gitweb` | [4.7](https://git-scm.com/book/en/v2/Git-on-the-Server-GitWeb) |
| 4.8 GitLab | P1, P7 | reference-only | [provider.md](provider.md) — hosted server administration | [4.8](https://git-scm.com/book/en/v2/Git-on-the-Server-GitLab) |
| 4.9 Third Party Hosted Options | — | reference-only | — (no footprint: hosting overview) | [4.9](https://git-scm.com/book/en/v2/Git-on-the-Server-Third-Party-Hosted-Options) |
| 4.10 Summary | — | reference-only | — (no footprint: chapter summary) | [4.10](https://git-scm.com/book/en/v2/Git-on-the-Server-Summary) |
| 5.1 Distributed Workflows | — | reference-only | — (no footprint: collaboration workflows) | [5.1](https://git-scm.com/book/en/v2/Distributed-Git-Distributed-Workflows) |
| 5.2 Contributing to a Project | G2, G13 | reference-only | [areas/repository-and-operations.md](areas/repository-and-operations.md) — commit guidelines, `format-patch` files | [5.2](https://git-scm.com/book/en/v2/Distributed-Git-Contributing-to-a-Project) |
| 5.3 Maintaining a Project | G2, G7, G13 | reference-only | [areas/repository-and-operations.md](areas/repository-and-operations.md) — `am`/`apply`, signed tags, `archive`, `shortlog` | [5.3](https://git-scm.com/book/en/v2/Distributed-Git-Maintaining-a-Project) |
| 5.4 Summary | — | reference-only | — (no footprint: chapter summary) | [5.4](https://git-scm.com/book/en/v2/Distributed-Git-Summary) |
| 6.1 Account Setup and Configuration | P7 | reference-only | [provider.md](provider.md) — SSH keys, 2FA | [6.1](https://git-scm.com/book/en/v2/GitHub-Account-Setup-and-Configuration) |
| 6.2 Contributing to a Project | P3 | reference-only | [provider.md](provider.md) — forks and pull requests | [6.2](https://git-scm.com/book/en/v2/GitHub-Contributing-to-a-Project) |
| 6.3 Maintaining a Project | P1, P3, P7 | reference-only | [provider.md](provider.md) — default branch, PR refs (`refs/pull/*`), collaborators | [6.3](https://git-scm.com/book/en/v2/GitHub-Maintaining-a-Project) |
| 6.4 Managing an organization | P7 | reference-only | [provider.md](provider.md) — teams and audit log | [6.4](https://git-scm.com/book/en/v2/GitHub-Managing-an-organization) |
| 6.5 Scripting GitHub | P5, P7 | reference-only | [provider.md](provider.md) — webhooks and the API | [6.5](https://git-scm.com/book/en/v2/GitHub-Scripting-GitHub) |
| 6.6 Summary | — | reference-only | — (no footprint: chapter summary) | [6.6](https://git-scm.com/book/en/v2/GitHub-Summary) |
| 7.1 Revision Selection | G16, G21 | reference-only | [areas/refs-reflogs-recovery.md](areas/refs-reflogs-recovery.md) — reflog shortnames, ranges | [7.1](https://git-scm.com/book/en/v2/Git-Tools-Revision-Selection) |
| 7.2 Interactive Staging | G3 | reference-only | [areas/worktree-index-rules.md](areas/worktree-index-rules.md) — partial staging | [7.2](https://git-scm.com/book/en/v2/Git-Tools-Interactive-Staging) |
| 7.3 Stashing and Cleaning | G3, G8 | reference-only | [areas/stashes-worktrees-submodules.md](areas/stashes-worktrees-submodules.md) — stash variants, `git clean` | [7.3](https://git-scm.com/book/en/v2/Git-Tools-Stashing-and-Cleaning) |
| 7.4 Signing Your Work | G7, G13 | reference-only | [areas/config-links-identity.md](areas/config-links-identity.md) — signed commits and tags | [7.4](https://git-scm.com/book/en/v2/Git-Tools-Signing-Your-Work) |
| 7.5 Searching | G14, G21 | reference-only | [areas/tracing.md](areas/tracing.md) — `git grep`, `log -S`, `log -L` | [7.5](https://git-scm.com/book/en/v2/Git-Tools-Searching) |
| 7.6 Rewriting History | G14, G15, G16 | reference-only | [areas/history-and-secrets.md](areas/history-and-secrets.md) — `rebase -i`, history removal. CONFLICT: shows `filter-branch`, which git-filter-branch(1) warns against; use `git filter-repo` | [7.6](https://git-scm.com/book/en/v2/Git-Tools-Rewriting-History) |
| 7.7 Reset Demystified | G3, G16 | reference-only | [areas/worktree-index-rules.md](areas/worktree-index-rules.md) — three trees, reset modes | [7.7](https://git-scm.com/book/en/v2/Git-Tools-Reset-Demystified) |
| 7.8 Advanced Merging | G2, G16 | reference-only | [areas/repository-and-operations.md](areas/repository-and-operations.md) — abort, undoing merges | [7.8](https://git-scm.com/book/en/v2/Git-Tools-Advanced-Merging) |
| 7.9 Rerere | G12 | reference-only | [commands/git-rerere.md](commands/git-rerere.md) — `rr-cache` | [7.9](https://git-scm.com/book/en/v2/Git-Tools-Rerere) |
| 7.10 Debugging with Git | G21 | reference-only | [areas/tracing.md](areas/tracing.md) — `blame -L/-C`, `bisect` | [7.10](https://git-scm.com/book/en/v2/Git-Tools-Debugging-with-Git) |
| 7.11 Submodules | G10 | reference-only | [areas/stashes-worktrees-submodules.md](areas/stashes-worktrees-submodules.md) — submodule workflows | [7.11](https://git-scm.com/book/en/v2/Git-Tools-Submodules) |
| 7.12 Bundling | G16, G17 | reference-only | [commands/git-bundle.md](commands/git-bundle.md) — `bundle create`/`verify` as a pre-operation backup | [7.12](https://git-scm.com/book/en/v2/Git-Tools-Bundling) |
| 7.13 Replace | G15 | reference-only | [commands/git-replace.md](commands/git-replace.md) — `refs/replace` | [7.13](https://git-scm.com/book/en/v2/Git-Tools-Replace) |
| 7.14 Credential Storage | G11, G12 | reference-only | [areas/config-links-identity.md](areas/config-links-identity.md) — cache, store, osxkeychain helpers | [7.14](https://git-scm.com/book/en/v2/Git-Tools-Credential-Storage) |
| 7.15 Summary | — | reference-only | — (no footprint: chapter summary) | [7.15](https://git-scm.com/book/en/v2/Git-Tools-Summary) |
| 8.1 Git Configuration | G11, G12, G20 | reference-only | [areas/config-links-identity.md](areas/config-links-identity.md) — config levels, `core.*` | [8.1](https://git-scm.com/book/en/v2/Customizing-Git-Git-Configuration) |
| 8.2 Git Attributes | G4, G12 | reference-only | [areas/worktree-index-rules.md](areas/worktree-index-rules.md) — diff and filter drivers, `export-ignore` | [8.2](https://git-scm.com/book/en/v2/Customizing-Git-Git-Attributes) |
| 8.3 Git Hooks | G12 | reference-only | [areas/config-links-identity.md](areas/config-links-identity.md) — client and server hooks | [8.3](https://git-scm.com/book/en/v2/Customizing-Git-Git-Hooks) |
| 8.4 An Example Git-Enforced Policy | G12 | reference-only | [areas/config-links-identity.md](areas/config-links-identity.md) — example server and client hooks | [8.4](https://git-scm.com/book/en/v2/Customizing-Git-An-Example-Git-Enforced-Policy) |
| 8.5 Summary | — | reference-only | — (no footprint: chapter summary) | [8.5](https://git-scm.com/book/en/v2/Customizing-Git-Summary) |
| 9.1 Git as a Client | G15, G18 | reference-only | [areas/footprints-and-references.md](areas/footprints-and-references.md) — `git svn` and bridge refs | [9.1](https://git-scm.com/book/en/v2/Git-and-Other-Systems-Git-as-a-Client) |
| 9.2 Migrating to Git | G18 | reference-only | [areas/footprints-and-references.md](areas/footprints-and-references.md) — importers and `fast-import` | [9.2](https://git-scm.com/book/en/v2/Git-and-Other-Systems-Migrating-to-Git) |
| 9.3 Summary | — | reference-only | — (no footprint: chapter summary) | [9.3](https://git-scm.com/book/en/v2/Git-and-Other-Systems-Summary) |
| 10.1 Plumbing and Porcelain | G1 | reference-only | [areas/repository-and-operations.md](areas/repository-and-operations.md) — `.git` directory contents | [10.1](https://git-scm.com/book/en/v2/Git-Internals-Plumbing-and-Porcelain) |
| 10.2 Git Objects | G17 | reference-only | [areas/object-store.md](areas/object-store.md) — blob, tree and commit objects | [10.2](https://git-scm.com/book/en/v2/Git-Internals-Git-Objects) |
| 10.3 Git References | G15 | reference-only | [areas/refs-reflogs-recovery.md](areas/refs-reflogs-recovery.md) — refs, HEAD, tags, remotes | [10.3](https://git-scm.com/book/en/v2/Git-Internals-Git-References) |
| 10.4 Packfiles | G17 | reference-only | [areas/object-store.md](areas/object-store.md) — packs, `verify-pack` | [10.4](https://git-scm.com/book/en/v2/Git-Internals-Packfiles) |
| 10.5 The Refspec | G6 | reference-only | [areas/branches-remotes-tags.md](areas/branches-remotes-tags.md) — fetch and push refspecs | [10.5](https://git-scm.com/book/en/v2/Git-Internals-The-Refspec) |
| 10.6 Transfer Protocols | — | reference-only | — (no footprint: wire protocol) | [10.6](https://git-scm.com/book/en/v2/Git-Internals-Transfer-Protocols) |
| 10.7 Maintenance and Data Recovery | G14, G16, G17 | reference-only | [areas/refs-reflogs-recovery.md](areas/refs-reflogs-recovery.md) — gc, reflog and fsck recovery, removing objects. CONFLICT: removes objects with `filter-branch` (superseded by `git filter-repo`) and deletes `.git/refs/original` and `.git/logs` by hand (use `git update-ref --stdin` deletes and `git reflog expire --expire=now --all`); simulates loss with `rm -Rf .git/logs/`, never for a real audit; "around 7,000" loose objects rounds the reference `gc.auto` default of 6700 | [10.7](https://git-scm.com/book/en/v2/Git-Internals-Maintenance-and-Data-Recovery) |
| 10.8 Environment Variables | G11, G21 | reference-only | [areas/config-links-identity.md](areas/config-links-identity.md) — `GIT_*` overrides, `GIT_TRACE*` | [10.8](https://git-scm.com/book/en/v2/Git-Internals-Environment-Variables) |
| 10.9 Summary | — | reference-only | — (no footprint: chapter summary) | [10.9](https://git-scm.com/book/en/v2/Git-Internals-Summary) |
| A1.1 Graphical Interfaces | — | reference-only | — (no footprint: GUI overview) | [A1.1](https://git-scm.com/book/en/v2/Appendix-A:-Git-in-Other-Environments-Graphical-Interfaces) |
| A1.2 Git in Visual Studio | G20 | reference-only | [areas/worktree-index-rules.md](areas/worktree-index-rules.md) — editor directories (`.vs/`) | [A1.2](https://git-scm.com/book/en/v2/Appendix-A:-Git-in-Other-Environments-Git-in-Visual-Studio) |
| A1.3 Git in Visual Studio Code | G20 | reference-only | [areas/worktree-index-rules.md](areas/worktree-index-rules.md) — editor directories (`.vscode/`) | [A1.3](https://git-scm.com/book/en/v2/Appendix-A:-Git-in-Other-Environments-Git-in-Visual-Studio-Code) |
| A1.4 Git in IntelliJ / PyCharm / WebStorm / PhpStorm / RubyMine | G20 | reference-only | [areas/worktree-index-rules.md](areas/worktree-index-rules.md) — editor directories (`.idea/`) | [A1.4](https://git-scm.com/book/en/v2/Appendix-A:-Git-in-Other-Environments-Git-in-IntelliJ-/-PyCharm-/-WebStorm-/-PhpStorm-/-RubyMine) |
| A1.5 Git in Sublime Text | G20 | reference-only | [areas/worktree-index-rules.md](areas/worktree-index-rules.md) — editor project files | [A1.5](https://git-scm.com/book/en/v2/Appendix-A:-Git-in-Other-Environments-Git-in-Sublime-Text) |
| A1.6 Git in Bash | — | reference-only | — (no footprint: shell completion and prompt) | [A1.6](https://git-scm.com/book/en/v2/Appendix-A:-Git-in-Other-Environments-Git-in-Bash) |
| A1.7 Git in Zsh | — | reference-only | — (no footprint: shell completion and prompt) | [A1.7](https://git-scm.com/book/en/v2/Appendix-A:-Git-in-Other-Environments-Git-in-Zsh) |
| A1.8 Git in PowerShell | — | reference-only | — (no footprint: shell completion and prompt) | [A1.8](https://git-scm.com/book/en/v2/Appendix-A:-Git-in-Other-Environments-Git-in-PowerShell) |
| A1.9 Summary | — | reference-only | — (no footprint: chapter summary) | [A1.9](https://git-scm.com/book/en/v2/Appendix-A:-Git-in-Other-Environments-Summary) |
| A2.1 Command-line Git | — | reference-only | — (no footprint: embedding libraries) | [A2.1](https://git-scm.com/book/en/v2/Appendix-B:-Embedding-Git-in-your-Applications-Command-line-Git) |
| A2.2 Libgit2 | — | reference-only | — (no footprint: embedding libraries) | [A2.2](https://git-scm.com/book/en/v2/Appendix-B:-Embedding-Git-in-your-Applications-Libgit2) |
| A2.3 JGit | — | reference-only | — (no footprint: embedding libraries) | [A2.3](https://git-scm.com/book/en/v2/Appendix-B:-Embedding-Git-in-your-Applications-JGit) |
| A2.4 go-git | — | reference-only | — (no footprint: embedding libraries) | [A2.4](https://git-scm.com/book/en/v2/Appendix-B:-Embedding-Git-in-your-Applications-go-git) |
| A2.5 Dulwich | — | reference-only | — (no footprint: embedding libraries) | [A2.5](https://git-scm.com/book/en/v2/Appendix-B:-Embedding-Git-in-your-Applications-Dulwich) |
| A3.1 Setup and Config | G11, G12 | reference-only | [areas/config-links-identity.md](areas/config-links-identity.md) — book index of config commands; see [Setup and Config](#setup-and-config) | [A3.1](https://git-scm.com/book/en/v2/Appendix-C:-Git-Commands-Setup-and-Config) |
| A3.2 Getting and Creating Projects | G1 | reference-only | [areas/repository-and-operations.md](areas/repository-and-operations.md) — book index; see [Getting and Creating Projects](#getting-and-creating-projects) | [A3.2](https://git-scm.com/book/en/v2/Appendix-C:-Git-Commands-Getting-and-Creating-Projects) |
| A3.3 Basic Snapshotting | G3 | reference-only | [areas/worktree-index-rules.md](areas/worktree-index-rules.md) — book index; see [Basic Snapshotting](#basic-snapshotting) | [A3.3](https://git-scm.com/book/en/v2/Appendix-C:-Git-Commands-Basic-Snapshotting) |
| A3.4 Branching and Merging | G5, G7, G8, G9 | reference-only | [areas/branches-remotes-tags.md](areas/branches-remotes-tags.md) — book index; see [Branching and Merging](#branching-and-merging) | [A3.4](https://git-scm.com/book/en/v2/Appendix-C:-Git-Commands-Branching-and-Merging) |
| A3.5 Sharing and Updating Projects | G6, G10 | reference-only | [areas/branches-remotes-tags.md](areas/branches-remotes-tags.md) — book index; see [Sharing and Updating Projects](#sharing-and-updating-projects) | [A3.5](https://git-scm.com/book/en/v2/Appendix-C:-Git-Commands-Sharing-and-Updating-Projects) |
| A3.6 Inspection and Comparison | G21 | reference-only | [areas/tracing.md](areas/tracing.md) — book index; see [Inspection and Comparison](#inspection-and-comparison) | [A3.6](https://git-scm.com/book/en/v2/Appendix-C:-Git-Commands-Inspection-and-Comparison) |
| A3.7 Debugging | G21 | reference-only | [areas/tracing.md](areas/tracing.md) — book index; see [Debugging](#debugging) | [A3.7](https://git-scm.com/book/en/v2/Appendix-C:-Git-Commands-Debugging) |
| A3.8 Patching | G2 | reference-only | [areas/repository-and-operations.md](areas/repository-and-operations.md) — book index; see [Patching](#patching) | [A3.8](https://git-scm.com/book/en/v2/Appendix-C:-Git-Commands-Patching) |
| A3.9 Email | G2, G12 | reference-only | [areas/repository-and-operations.md](areas/repository-and-operations.md) — book index; see [Email](#email) | [A3.9](https://git-scm.com/book/en/v2/Appendix-C:-Git-Commands-Email) |
| A3.10 External Systems | G18 | reference-only | [areas/footprints-and-references.md](areas/footprints-and-references.md) — book index; see [External Systems](#external-systems) | [A3.10](https://git-scm.com/book/en/v2/Appendix-C:-Git-Commands-External-Systems) |
| A3.11 Administration | G16, G17 | reference-only | [areas/object-store.md](areas/object-store.md) — book index; see [Administration](#administration) | [A3.11](https://git-scm.com/book/en/v2/Appendix-C:-Git-Commands-Administration) |
| A3.12 Plumbing Commands | G17 | reference-only | [areas/object-store.md](areas/object-store.md) — book index; see [Plumbing Commands](#plumbing-commands) | [A3.12](https://git-scm.com/book/en/v2/Appendix-C:-Git-Commands-Plumbing-Commands) |

## Companion tools

Third-party tools with a corpus page. They are not git-scm pages and are not counted below; the plugin detects and uses them when installed and never installs them.

| Command or page | Areas | Safety class | Corpus | Official |
| --- | --- | --- | --- | --- |
| `git filter-repo` | G14, G18 | writes-local-state (`--analyze` writes a report under `.git/filter-repo/`); mutates (every rewrite) | [commands/git-filter-repo.md](commands/git-filter-repo.md) | [git-filter-repo](https://github.com/newren/git-filter-repo) |
| `git lfs` | G4, G12, G17 | read (`ls-files`, `status`, `env`); network (`fetch`, `pull`, `push`); mutates (`install`, `track`, `migrate`, `prune`) | [commands/git-lfs.md](commands/git-lfs.md) | [git-lfs](https://git-lfs.com/) |

## Coverage of this map

198 git-scm reference pages (91 from the /docs index, 107 outside it) and 101 Pro Git sections; each appears exactly once.
