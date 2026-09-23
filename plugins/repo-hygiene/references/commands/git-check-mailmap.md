# git check-mailmap

Official: https://git-scm.com/docs/git-check-mailmap · Areas: G13 · Floor: 1.8.4 `[doc]`
RelNotes 1.8.4

## Purpose in an audit

Test how `.mailmap` (and `mailmap.file`, `mailmap.blob`) maps each identity found in history,
to show which people appear under several names or emails and whether the mailmap joins
them.

## Safety class

| Form | Class | Why |
| --- | --- | --- |
| `git check-mailmap <contact>…` | read | Prints the canonical form |
| `git check-mailmap --stdin` | read | Same, from standard input |
| `--mailmap-file=<file>`, `--mailmap-blob=<blob>` | read | Tests a candidate mailmap without committing it |

## Options that matter

- Input forms: `Name <user@host>`, `<user@host>`, `user@host`; unknown contacts are echoed
  unchanged `[doc]`.
- `--mailmap-file` / `--mailmap-blob`: extra mailmap that takes precedence over the configured
  ones `[doc]`.
- Mailmap syntax `[doc]` gitmailmap: `Proper Name <commit@email>`,
  `<proper@email> <commit@email>`, `Proper Name <proper@email> <commit@email>`,
  `Proper Name <proper@email> Commit Name <commit@email>`; names and emails match
  case-insensitively; Git does not follow a symlinked `.mailmap` in the working tree.

## Verified recipes

```sh
git --no-replace-objects --no-pager log --all --format='%an <%ae>' | sort -u \
  | git check-mailmap --stdin | sort | uniq -c | sort -rn | head -n 30
git check-mailmap 'Dev Old <dev@old.example>' '<nobody@x>'
```

`[observed]`: with `Dev <dev@example.com> Dev Old <dev@old.example>` in `.mailmap`, the
second command printed `Dev <dev@example.com>` and `<nobody@x>`.

## Footprint it leaves when interrupted or misused

None.

## Gotchas

- `shortlog`, `log --format=%aN/%aE` and `blame` (with `log.mailmap`/`--use-mailmap`) apply
  the mailmap; compare against raw `%an/%ae` to see what history really stores
  `[observed]`.
- Git 2.49 fixed a crash when querying a contact without a name `[doc]` RelNotes 2.49.0.
