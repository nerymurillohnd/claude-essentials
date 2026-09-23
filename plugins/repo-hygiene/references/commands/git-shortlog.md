# git shortlog

Official: https://git-scm.com/docs/git-shortlog · Areas: G13 · Floor: any (`--group` 2.29
`[doc]` RelNotes 2.29.0)

## Purpose in an audit

Count commits per identity (author, committer, or trailer value) to find one person under
several names or emails, identities that no longer match config, and trailer coverage.

## Safety class

| Form | Class | Why |
| --- | --- | --- |
| `git shortlog -s -n -e <rev>…` | read | Counts per identity |
| `git shortlog` with no revision | read | Reads a log from **stdin** when stdin is not a terminal |

## Options that matter

- `-s` counts only, `-n` sort by count, `-e` show emails.
- `-c` / `--committer` groups by committer instead of author.
- `--group=author|committer|trailer:<key>` (repeatable; `format:<fmt>` also accepted
  `[doc]`): a commit counts once per distinct identity across groups.
- `--all`, `--branches`, `--since=<date>` and any revision range, like `git log`.
- Always applies `.mailmap`; `--no-mailmap` is rejected (`error: unknown option`)
  `[observed]`.

## Verified recipes

```sh
git --no-replace-objects --no-pager shortlog -s -n -e --all | head -n 30
git --no-replace-objects --no-pager shortlog -s -n -e -c --all | head -n 30
git --no-replace-objects --no-pager shortlog -s -n -e --all \
  --group=author --group=committer --group=trailer:co-authored-by --group=trailer:signed-off-by \
  | head -n 30
git --no-replace-objects --no-pager shortlog -s -n -e --since=90.days --all | head -n 20
```

`[observed]`: author grouping showed one identity with 4 commits while committer grouping
showed `Dev` 3 and `Dev Old` 1 (the session's `GIT_AUTHOR_*` overrode the local
`user.name`); the trailer groups listed `Pat` and `Someone Else`.

## Footprint it leaves when interrupted or misused

None.

## Gotchas

- `git shortlog -s -n -e` with no revision in a non-interactive shell read an empty stdin and
  printed nothing, exit 0 `[observed]`: always pass `HEAD`, `--all` or a range.
- Raw identities need `git log --format='%an <%ae>'` (`%aN`/`%aE` are mapped) `[observed]`.
- `--no-replace-objects` goes before `shortlog`, as a global option `[observed]`.
