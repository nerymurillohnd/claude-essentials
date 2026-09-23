# git interpret-trailers

Official: https://git-scm.com/docs/git-interpret-trailers · Areas: G13 · Floor: `--parse`
2.15 `[doc]` RelNotes 2.15.0

## Purpose in an audit

Extract the trailers (`Signed-off-by:`, `Co-authored-by:`, `Reviewed-by:` lines at the end of
a commit message) exactly as Git parses them, to check sign-off and co-author consistency.

## Safety class

| Form | Class | Why |
| --- | --- | --- |
| `git interpret-trailers --parse` (stdin or files) | read | Prints existing trailers only |
| `--only-trailers --only-input` | read | Same as `--parse` without unfolding |
| default mode, `--trailer <k=v>` | executes-config | Adds trailers and applies `trailer.<key>.cmd` / `.command` programs |
| `--in-place <file>` | mutates | Rewrites the file |

## Options that matter

- `--parse` = `--only-trailers --only-input --unfold`: no trailers added from the command
  line or from `trailer.*` config `[doc]`.
- `--unfold` joins multi-line trailer values.
- `--no-divider`: do not treat `---` as the end of the message (use it for messages that
  contain a `---` line) `[doc]`.
- For many commits, `git log --format='%(trailers:…)'` is faster: `key=`, `valueonly`,
  `separator=`, `only`, `unfold` `[doc]` git-log PRETTY FORMATS.

## Verified recipes

```sh
git --no-pager log -1 --format=%B <commit> | git interpret-trailers --parse
git --no-replace-objects --no-pager log --max-count=200 --format='%(trailers:only,unfold)' \
  | grep -v '^$' | sed -E 's/:.*//' | sort | uniq -c
git --no-replace-objects --no-pager log --max-count=200 \
  --format='%h%x09%ae%x09%ce%x09%(trailers:key=Signed-off-by,valueonly,separator=%x2C)'
```

`[observed]`: `--parse` printed `Co-authored-by: Pat <…>` and `Signed-off-by: Someone Else
<…>` for a commit whose committer was `Dev`; the counting recipe printed `1 Co-authored-by`
and `2 Signed-off-by` (after dropping blank lines).

## Footprint it leaves when interrupted or misused

`--in-place` leaves the rewritten file; an interrupted `commit --trailer` leaves
`COMMIT_EDITMSG`.

## Gotchas

- Trailer keys are matched case-insensitively by Git, but projects often require one
  spelling; count spellings separately (`Co-authored-by` vs `Co-Authored-By`).
- A trailer block must be the last paragraph; a trailing non-trailer line hides it.
