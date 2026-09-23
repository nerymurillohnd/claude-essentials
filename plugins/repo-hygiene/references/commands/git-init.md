# git init

Official: https://git-scm.com/docs/git-init · Areas: G1, G11 · Floor: any

## Purpose in an audit

Explains where a repository's initial layout came from (templates, object format, ref
format, initial branch, shared permissions) and what re-running it would change. The audit
never runs it on the user's repository.

## Safety class

| Form | Class | Why |
| --- | --- | --- |
| `git init <new-dir>` | mutates (outside the audited repository) | Creates a repository |
| `git init` in an existing repository | mutates | "Reinitializes": picks up newly added templates; "will not overwrite things that are already there" `[doc]` |
| `git init --separate-git-dir=<dir>` on an existing repository | mutates | Moves the repository `[doc]` |
| `git init` with `init.templateDir` or `--template` | mutates, installs files | Copies template files, hooks included, into `.git/` `[doc]` |
| `git config --get init.templateDir`, `git var GIT_DEFAULT_BRANCH` | read | Inventory |

## Options that matter

- `--bare` `[doc]`.
- `--template=<dir>` / `init.templateDir`: source of the files copied into `.git/`
  (`hooks/`, `info/exclude`, `description`) `[doc]`. A template with real hooks installs
  them in every new repository: a G11/G12 finding.
- `--separate-git-dir=<dir>`: `.git` becomes a gitfile pointing elsewhere `[doc]`.
- `--object-format=(sha1|sha256)`, `--ref-format=(files|reftable)` `[doc]`.
- `-b <name>`/`--initial-branch`, `init.defaultBranch` `[doc]`.
- `--shared[=(false|true|umask|group|all|world|everybody|<perm>)]`: group-writable
  repositories (and the `safe.directory` interplay) `[doc]`.

## Verified recipes

```sh
git config --show-origin --get init.templateDir
git var GIT_DEFAULT_BRANCH
```

`[observed]`: exit 1 (no template directory set); `main`.

On a disposable fixture only:

```sh
git init
```

`[observed]`: `Reinitialized existing Git repository in <repo>/.git/`; a deleted
`.git/description` was recreated from the templates; `.git/config` was byte-identical
before and after.

```sh
git init -q -b main --object-format=sha256 sha256repo
git init -q -b main --ref-format=reftable reftable
```

`[observed]`: `rev-parse --show-object-format` printed `sha256`, `--show-ref-format`
printed `reftable`; both set `core.repositoryformatversion 1` and an `extensions.*` key.

## Footprint it leaves when interrupted or misused

- A reinit restores missing template files, including sample hooks, into an existing
  repository `[observed]` (description) `[doc]` (templates).
- `--separate-git-dir` leaves a `.git` file (`gitdir: <path>`) in the working tree.

## Gotchas

- Running `git init` inside a directory that is already inside another repository creates
  a nested repository the outer one sees as untracked (`areas/stashes-worktrees-submodules.md`,
  G10 check 13).
- sha256 and reftable repositories need a Git that knows the extension; tools that
  assume SHA-1 or loose refs break (G1).
- A home directory turned into a repository by an accidental `git init ~` makes every
  project below it look nested; check `--show-toplevel` (G1 check 1).
