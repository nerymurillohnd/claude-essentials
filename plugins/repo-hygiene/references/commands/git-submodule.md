# git submodule

Official: https://git-scm.com/docs/git-submodule · Areas: G10, G19 · Floor: any

## Purpose in an audit

Shows whether each submodule is initialized, at the recorded commit, conflicted, and where
its URL comes from. Most subcommands change checkouts or fetch; only `status` and
`summary` read.

## Safety class

| Form | Class | Why |
| --- | --- | --- |
| `git --no-optional-locks submodule status [--cached] [--recursive]` | read | Prints recorded or checked-out commits |
| `summary [--cached\|--files]` | read | Commit summaries inside submodules |
| `foreach <command>` | executes-config | "Evaluate an arbitrary shell command" in each submodule `[doc]`; never in an audit |
| `init` | mutates (config) | Copies `.gitmodules` URLs into `.git/config` `[doc]` |
| `update` | network, mutates | Clones, fetches, checks out, rebases or merges `[doc]` |
| `update` with `submodule.<name>.update=!<cmd>` | executes-config | Runs the command with the commit ID `[doc]` |
| `sync` | mutates (config) | Rewrites remote URLs from `.gitmodules` `[doc]` |
| `set-url`, `set-branch` | mutates (tracked `.gitmodules`) | `[doc]` |
| `deinit` | mutates | Removes the config section and the submodule's working tree `[doc]` |
| `absorbgitdirs` | mutates | Moves an embedded git dir into `$GIT_DIR/modules/` `[doc]` |
| `add` | network, mutates | Clones and stages |

## Options that matter

- `status` prefixes: `-` not initialized, `+` checked-out commit differs from the index,
  `U` merge conflicts; `--cached` prints the recorded commit; `--recursive` descends
  `[doc]`.
- `update` modes: `checkout` (detached HEAD), `rebase`, `merge`, `!<custom-command>`
  (only from `.git/config`, not `.gitmodules` or the command line), `none` `[doc]`.
  `--init`, `--remote`, `--recursive`, `--force`, `--filter` `[doc]`.
- `deinit --all` or `-- <path>`; without a pathspec it errors out; `--force` removes a
  working tree with local changes `[doc]`.
- `init` does not copy a custom-command `update` value "for security reasons" `[doc]`.
- Relative URLs (`../x.git`) resolve against the superproject's default remote `[doc]`.

## Verified recipes

```sh
git --no-optional-locks submodule status
```

`[observed]`: `+99676cff… libs/a (99676cf)` (moved after `checkout HEAD~1` in the
submodule) and `-29c050ab… libs/b` (after `deinit`).

```sh
git --no-pager config --file .gitmodules --get-regexp '^submodule\.' \
  | sed -E 's#(://)[^/@[:space:]]+@#\1***@#g'
git --no-pager config --get-regexp '^submodule\.' \
  | sed -E 's#(://)[^/@[:space:]]+@#\1***@#g'
```

`[observed]`: `.gitmodules` URL (a local path) vs `.git/config`
`https://changed.example.com/a.git`, plus `submodule.libs/a.active true`.

```sh
git --no-optional-locks --no-pager ls-files --stage | awk '$1=="160000"'
```

`[observed]`: two gitlinks, both at `29c050a`.

```sh
git rev-parse --resolve-git-dir libs/a/.git
```

`[observed]`: `<super>/.git/modules/libs/a` (absorbed layout; `libs/a/.git` is a file
`gitdir: ../../.git/modules/libs/a`).

## Footprint it leaves when interrupted or misused

- `$GIT_DIR/modules/<name>/` stays after `git rm <submodule>`: `.git/modules/libs/b`
  (120 KiB) remained after removal `[observed]`.
- `deinit` empties the path and removes the config section; the module repository in
  `.git/modules` stays `[observed]` (`-` prefix afterwards).
- `update --rebase`/`--merge` can leave a rebase or merge in progress inside the
  submodule: run G2 checks there.

## Gotchas

- `status` does not list untracked nested repositories (`nested/`) or directories with a
  broken `.git` file; use `find` and `git ls-files -o` (see
  `areas/stashes-worktrees-submodules.md`).
- The module directory is named after the submodule **name**, not the path `[doc]`
  (`gitrepository-layout`).
- Local-path (file protocol) submodules are refused by default since the security
  releases that changed `protocol.file.allow` to `user` (2.30.6 and 2.37.4 lines, RelNotes);
  the fixture needed `-c protocol.file.allow=always` to add them `[observed]`. Do not set
  it globally to make an update pass.
- `--no-optional-locks` sets `GIT_OPTIONAL_LOCKS=0` for child processes `[doc]` (`git`).
