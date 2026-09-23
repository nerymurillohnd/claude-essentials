# git am

Official: https://git-scm.com/docs/git-am · Areas: G2 · Floor: any

## Purpose in an audit

Recognize and explain an `am` session left half done (`rebase-apply/` with `applying`),
and the `*.patch`/`*.mbox` files it consumed. The audit never applies mail.

## Safety class

| Form | Class | Why |
| --- | --- | --- |
| `git am <mbox>…` | mutates, executes-config | Creates commits; runs `applypatch-msg`, `pre-applypatch`, `post-applypatch` hooks `[doc]` |
| `--continue`, `--resolved`, `--skip` | mutates | Commit or skip the current patch |
| `--abort` | mutates | Restore the original branch; also clears rerere state `[doc]` (`git-rerere`) |
| `--quit` | mutates | Drop the session, keep HEAD and index as they are `[doc]` |
| `--retry` | mutates | Try the current patch again `[doc]` |
| `--show-current-patch[=diff\|raw]` | read, prints contents | Shows the stopped patch; may contain secrets |

## Options that matter

- `--3way`, `--keep-cr`, `--whitespace=`, `--reject` (leaves `*.rej`), `--directory`,
  `--exclude`, `--include`, `-p<n>` are passed to `git apply` `[doc]`.
- `--signoff`, `--keep`, `--keep-non-patch`, `--scissors`, `--message-id` shape the commit
  message `[doc]`.
- `--no-verify` skips the `applypatch-msg` and `pre-applypatch` hooks `[doc]`: never add
  it to make an item pass.

## Verified recipes

```sh
git rev-parse --git-path rebase-apply
ls "$(git rev-parse --git-path rebase-apply)"
```

`[observed]` after a failed `git am`: the directory held `0001`, `0002`, `applying`,
`next`, `last`, `patch`, `msg`, `info`, `final-commit`, `author-script`, `abort-safety`,
and option files (`keep`, `sign`, `threeway`, `utf8`, `quiet`, `scissors`, `messageid`,
`quoted-cr`, `apply-opt`).

```sh
cat "$(git rev-parse --git-path rebase-apply/next)" \
  "$(git rev-parse --git-path rebase-apply/last)"
```

`[observed]`: `1` and `2` (stopped at patch 1 of 2).

```sh
git apply --stat "$(git rev-parse --git-path rebase-apply/patch)"
```

Lists the files of the stopped patch without printing its lines (a read, see
`commands/git-apply.md`).

## Footprint it leaves when interrupted or misused

- `$GIT_DIR/rebase-apply/` with the file `applying` (the marker that tells `am` apart from
  a rebase with the apply backend) `[observed]`; Git's status code checks the same file
  (`wt-status.c`, `rebase-apply/applying`).
- The mbox or `*.patch` files in the working tree.
- `*.rej` files when `--reject` was used.
- `porcelain=v2` status shows nothing special; the branch header stays on the branch
  `[observed]`.

## Gotchas

- `--show-current-patch` prints the whole message and diff; use `git apply --stat` on
  `rebase-apply/patch` instead.
- An abandoned `am` blocks `git rebase` and `git am` until aborted or quit.
- Patch files left in the tree are often untracked noise; check with
  `git apply --check -R` whether they are already applied (`commands/git-apply.md`).
