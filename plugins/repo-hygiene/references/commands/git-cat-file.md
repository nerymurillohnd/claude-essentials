# git cat-file

Official: https://git-scm.com/docs/git-cat-file · Areas: G14, G15, G16, G17 · Floor: any
(`--batch-all-objects` 2.6, `--batch-command` 2.36)

## Purpose in an audit

Test existence, type and size of objects without printing content; census every object in
the store; show commit and tag headers when needed. It is the safe replacement for
`cat`-ing anything inside `.git`.

## Safety class

| Form | Class | Why |
| --- | --- | --- |
| `-e <obj>` | read | exit status only |
| `-t`, `-s` | read | type, size |
| `--batch-check[=<fmt>]`, `--batch-all-objects`, `--unordered`, `--buffer` | read | metadata only |
| `-p <obj>`, `<type> <obj>`, `--batch` | read, prints content | blob content may be a secret: never on blobs from G14 or unknown payloads |
| `--textconv`, `--filters`, and `--batch --textconv/--filters` | executes-config | run configured textconv / clean-smudge drivers |
| `--batch-command` with `remote-object-info` | network | asks the remote about objects |

## Options that matter

- `--batch-check='%(objecttype) %(objectsize) %(objectsize:disk) %(objectname) %(deltabase)'`.
- `--batch-all-objects`: every object in the repository **and its alternates**, reachable or
  not; add `--unordered` for speed.
- `--follow-symlinks` (batch): follow in-tree symlinks; `--use-mailmap`.
- `-e` exits 0 when the object exists and is valid, non-zero otherwise, silently.

## Verified recipes

```sh
git cat-file -e 0000000000000000000000000000000000000001; echo "exit=$?"
git cat-file -t 3f2f61edd7c8e32ba676f916ebbe3d2e71e2eaf4
git cat-file --batch-all-objects --batch-check='%(objecttype)' --unordered | sort | uniq -c
git cat-file --batch-all-objects --batch-check='%(objectsize) %(objecttype) %(objectname)' --unordered \
  | sort -n -r | head -n 10
git --no-replace-objects cat-file commit 21a4d8d | tail -n 1
```

`[observed]`: exit 128 for the planted lost-found name; `tree`; 20 blob, 21 commit, 1 tag,
21 tree; the two largest objects were 3 072 000- and 2 097 152-byte blobs; the last line
printed `big blob`, while the same command without `--no-replace-objects` printed the
replacement's subject `remove config`.

## Footprint it leaves when interrupted or misused

None.

## Gotchas

- It honors replace refs `[observed]`: always `git --no-replace-objects cat-file`.
- `-p` on a blob prints it: that is how secrets reach the transcript. Use sizes and hashes.
- `--batch-all-objects` counts unreachable and cruft-pack objects and alternates: it is a
  census, not "what the project contains".
- A `lost-found` file's name is not proof that the object exists; `-e` is.
