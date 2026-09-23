# git apply

Official: https://git-scm.com/docs/git-apply · Areas: G2 · Floor: any

## Purpose in an audit

Read leftover patch files safely: what they touch (`--stat`, `--summary`, `--numstat`),
whether they still apply (`--check`) and whether they are already applied
(`--check -R`). Explain `*.rej` files.

## Safety class

| Form | Class | Why |
| --- | --- | --- |
| `--stat`, `--numstat`, `--summary` | read | "Instead of applying the patch, output …"; turn off apply `[doc]` |
| `--check [-R] [--index\|--cached]` | read | Tests applicability; "Turns off apply" `[doc]` |
| plain `git apply <patch>` | mutates (working tree) | Applies to files |
| `--index`, `--cached`, `--3way`, `--intent-to-add` | mutates (index) | `--3way` implies `--index` unless `--cached` `[doc]` |
| `--reject` | mutates | Applies what fits and writes `*.rej` for the rest `[doc]` |
| `--build-fake-ancestor=<file>` | mutates | Writes an index file |
| `--unsafe-paths` | mutates outside the tree | Lifts the protection against paths outside the working area `[doc]` |

## Options that matter

- `-R`, `--reverse`: apply in reverse; with `--check`, tests "already applied" `[doc]`.
- `--include=<path-pattern>`, `--exclude=<path-pattern>`, `--directory=<root>`, `-p<n>`
  `[doc]`.
- `--whitespace=(nowarn|warn|fix|error|error-all)`, `--ignore-whitespace` `[doc]`.
- `--allow-empty`, `--recount`, `--inaccurate-eof` `[doc]`.
- `-z` with `--numstat`: NUL-terminated `[doc]`.
- Without `--unsafe-paths`, a patch touching a path outside the working area "is rejected
  as a mistake (or a mischief)" `[doc]`.

## Verified recipes

```sh
git apply --stat --summary ../patches/0002-t2.patch
```

`[observed]`: `g | 1 +`, `1 file changed, 1 insertion(+)`, `create mode 100644 g`.

```sh
git apply --check ../patches/0002-t2.patch
git apply --check -R ../patches/0002-t2.patch
```

`[observed]`: the first exited 1 (`g: already exists in working directory`), the second
exited 0: the patch's content is already present.

```sh
git apply --numstat ../p.diff
```

`[observed]`: `2<TAB>2<TAB>n.txt`.

## Footprint it leaves when interrupted or misused

- `--reject` leaves `<file>.rej` next to each file with rejected hunks and applies the
  rest: `Applying patch n.txt with 1 reject... Hunk #1 applied cleanly. Rejected hunk
  #2.`, exit 1, `n.txt.rej` created `[observed]`.
- Without `--reject`, a failing patch changes nothing ("fails the whole patch and does
  not touch the working tree") `[doc]`.

## Gotchas

- `--check` success does not mean "not yet applied"; run `--check -R` too.
- A patch file may hold secrets in its lines; `--stat`/`--summary` print only names and
  counts.
- `*.rej` files are untracked leftovers; they are safe to remove only after the hunks are
  handled.
