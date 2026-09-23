# git fast-export

Official: https://git-scm.com/docs/git-fast-export · Areas: G14, G18 · Floor: any
(`--signed-commits` present in 2.55 `[doc]`)

## Purpose in an audit

Recognize fast-export/fast-import footprints (marks files from migrations or incremental
mirrors), and understand what the filter-repo pipeline does with signatures. Rarely run
during an audit.

## Safety class

| Form | Class | Why |
| --- | --- | --- |
| `git fast-export <revs>` to stdout | read | Streams objects, **including file contents** |
| `--export-marks=<file>` | writes-local-state | Writes the marks table |
| `--import-marks=<file>` | read | Reads a marks table |
| `--anonymize` | read | Stream with contents and names replaced `[doc]` |
| `\| git fast-import` | mutates | Writes objects and refs |

## Options that matter

- `--signed-tags=(verbatim|warn-verbatim|warn-strip|strip|abort)`: default `abort` `[doc]`.
- `--signed-commits=(…)`: default `strip`, the historical behavior `[doc]`.
- `--tag-of-filtered-object=(abort|drop|rewrite)`, `-M`, `-C`, `--no-data`, `--full-tree`,
  `--mark-tags`, `--reference-excluded-parents`, `--show-original-ids` `[doc]`.
- Marks files: `:markid SHA` one per line, commits only `[doc]`.

## Verified recipes

```sh
find "$(git rev-parse --git-common-dir)" -maxdepth 2 \( -name '*marks*' -o -name 'fast-import*' \) \
  2>/dev/null | head -n 20
git fast-export --anonymize --all | wc -c
```

`[observed]`: the `find` ran with no hits on the fixture; the anonymized stream (4 313 bytes)
contained no match for the planted token pattern. The second line gives a size estimate of
history without printing content; do not run `fast-export` without
`--anonymize` into the transcript (it prints file contents, secrets included).

## Footprint it leaves when interrupted or misused

Marks files where `--export-marks` pointed; fast-import leaves
`.git/fast_import_crash_<pid>` reports on failure `[doc]` git-fast-import.

## Gotchas

- An export–import round trip strips commit signatures by default and aborts on signed
  tags: a rewrite loses signatures unless told otherwise.
- A stale marks file makes the next incremental export skip commits.
