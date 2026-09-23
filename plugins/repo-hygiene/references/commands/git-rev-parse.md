# git rev-parse

Official: https://git-scm.com/docs/git-rev-parse · Areas: G1, G2, G8, G9, G10 · Floor: any
(`--is-shallow-repository` 2.15, `--end-of-options` 2.24)

## Purpose in an audit

Where the repository is and what shape it has (top level, git dir, common dir, bare,
shallow, object and ref format), where a state file lives in this worktree
(`--git-path`), and whether a name resolves to an object (`--verify`).

## Safety class

| Form | Class | Why |
| --- | --- | --- |
| every form | read | Resolves names and paths; writes nothing |
| `--verify '<rev>:<path>'` in a blobless partial clone | read | Resolves through trees only: the missing-object count stayed at 3 before and after `[observed]` |

## Options that matter

- `--show-toplevel` (error without a working tree), `--show-prefix`, `--show-cdup`
  `[doc]`.
- `--git-dir` (relative when possible), `--absolute-git-dir`, `--git-common-dir`
  (`$GIT_COMMON_DIR` or `$GIT_DIR`) `[doc]`.
- `--git-path <path>`: resolve `$GIT_DIR/<path>` honoring worktrees and relocation
  variables (`GIT_OBJECT_DIRECTORY`, `GIT_INDEX_FILE`) `[doc]`. Repeatable in one call
  `[observed]`.
- `--path-format=(absolute|relative)`: applies to the options after it `[doc]`.
- `--is-bare-repository`, `--is-shallow-repository`, `--is-inside-work-tree`,
  `--is-inside-git-dir` `[doc]`.
- `--show-object-format[=(storage|input|output|compat)]`, `--show-ref-format` `[doc]`.
- `--show-superproject-working-tree`: empty unless inside a submodule `[doc]`.
- `--shared-index-path`: the shared index in split-index mode, else empty `[doc]`.
- `--resolve-git-dir <path>`: validate a git dir or gitfile and print the real location
  `[doc]`.
- `--local-env-vars`: names (not values) of repository-local `GIT_*` variables `[doc]`.
- `--verify`: exactly one argument that resolves to an object; add `^{commit}` (or
  another type) to require a type; `-q`/`--quiet` silences errors `[doc]`.
- `--end-of-options`: everything after is a revision, never an option (use before names
  taken from repository data) `[doc]` (`gitcli`).
- `--symbolic-full-name`, `--abbrev-ref` (`HEAD` when detached) `[doc]`.

## Verified recipes

```sh
git --no-optional-locks --no-pager rev-parse --show-toplevel --show-prefix --git-dir \
  --git-common-dir --absolute-git-dir --is-bare-repository --is-shallow-repository \
  --show-object-format --show-ref-format --show-superproject-working-tree
```

`[observed]`: main fixture `.git`, `.git`, `false`, `false`, `sha1`, `files`, empty
superproject line; sha256 repository `sha256`; reftable repository `reftable`; shallow
clone `true`; bare repository `true`; in a submodule the superproject path.

```sh
git rev-parse --git-path MERGE_HEAD --git-path BISECT_LOG --git-path rr-cache
```

`[observed]` in a linked worktree: `…/.git/worktrees/wt-live/MERGE_HEAD`,
`…/.git/worktrees/wt-live/BISECT_LOG`, `…/.git/rr-cache` (shared).

```sh
git --no-optional-locks rev-parse --shared-index-path
```

`[observed]`: `.git/sharedindex.<hash>` in split-index mode; empty otherwise.

```sh
git rev-parse --resolve-git-dir elsewhere/.git
```

`[observed]`: `fatal: not a git repository: /nonexistent/path/.git`, exit 128.

```sh
git rev-parse --verify --quiet --end-of-options 'refs/bisect/bad^{commit}'
```

`[observed]`: the SHA; `--verify` with three names exits 1 with no output.

```sh
git -C <subdir> rev-parse --show-prefix --show-cdup
```

`[observed]`: `sub/` and `../`.

## Footprint it leaves when interrupted or misused

None.

## Gotchas

- Outside a repository most forms exit 128 with `fatal: not a git repository`
  `[observed]`; report it as "not a repository", not as an error.
- `--git-dir` is relative (`.git`) in the main worktree and absolute in a linked one
  `[observed]`; use `--absolute-git-dir` or `--path-format=absolute` when comparing.
- `--show-object-format=compat` prints an empty line when no compatibility hash is on
  `[observed]`, `[doc]`.
- `--abbrev-ref HEAD` prints `HEAD` when detached `[observed]`; prefer
  `git symbolic-ref -q HEAD` (exit 1 when detached).
