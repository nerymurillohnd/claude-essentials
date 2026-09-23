# git blame

Official: https://git-scm.com/docs/git-blame · Areas: G21 · Floor: any (`--ignore-rev`,
`--ignore-revs-file`, `blame.ignoreRevsFile` 2.23 `[doc]` RelNotes 2.23.0)

## Purpose in an audit

Attribute each line to the commit that last changed it, seeing through moves, copies and
formatting commits, to trace where code or a behavior came from and to adjudicate review
threads (D14).

## Safety class

| Form | Class | Why |
| --- | --- | --- |
| `git blame <file>` (default) | executes-config | Runs `diff.<driver>.textconv` by default `[observed]` |
| `git blame --no-textconv …` | read | Driver not run `[observed]` |
| `--contents <file>` | read | Blames another file's content; never a secret-shaped file |

## Options that matter

- `-L <start>,<end>`, `-L :<funcname>` (repeatable), `-s`, `-e`, `-w`.
- `-M[<num>]` moves within a file; `-C[<num>]` once: other files changed in the same commit;
  twice: also the commit that created the file; three times: any commit. `<num>` is the
  minimum alphanumeric characters (default about 40) `[doc]`.
- `--ignore-rev <rev>`, `--ignore-revs-file <file>` (fsck.skipList format; repeatable; an
  empty value clears earlier lists, including `blame.ignoreRevsFile`) `[doc]` `[observed]`.
- `blame.markIgnoredLines` (`?` prefix) and `blame.markUnblamableLines` (`*`) `[doc]`.
- `--first-parent`, `--reverse <start>..<end>`.
- `--porcelain`, `--line-porcelain`, `--incremental` for parsing.

## Verified recipes

```sh
git --no-pager blame --no-textconv -s -C -C -M -- g.py
git --no-pager blame --no-textconv --line-porcelain -L 1,3 -C -C -M -- g.py \
  | grep -E '^([0-9a-f]{40} |author |filename |previous )'
git --no-pager blame --no-textconv -s -C -C -M --ignore-revs-file=.git-blame-ignore-revs -- n.py
git -c blame.markIgnoredLines=true --no-pager blame --no-textconv -s \
  --ignore-revs-file=.git-blame-ignore-revs -- n.py
```

`[observed]`: `-C` moved credit for a relocated function from the move commit to the
original one (`e697ca22 m.py …`); a 23-character block was not detected; the ignore file
moved a reformatted line to its previous commit, marked `?` with `markIgnoredLines`.

## Footprint it leaves when interrupted or misused

None.

## Gotchas

- `blame.ignoreRevsFile` set to a missing file makes every blame fail with
  `fatal: could not open object name list: <file>` `[observed]`.
- `blame` credits the last change, not the author of the idea; pair it with `log -S`/`-G`.
- The Git reference map lists `blame` as executes-config only with `--textconv`; the
  observed default is the opposite: add `--no-textconv`.
