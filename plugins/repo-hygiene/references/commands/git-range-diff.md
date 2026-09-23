# git range-diff

Official: https://git-scm.com/docs/git-range-diff · Areas: G5, P3 · Floor: 2.19

## Purpose in an audit

Compare two versions of a patch series: a local branch against the PR head that was
merged, a branch before and after a force-push (old tip from the reflog), or a
rebased series against its original. It answers "which commits changed, were dropped, or
were added".

## Safety class

| Form | Class | Why |
| --- | --- | --- |
| `range-diff <r1> <r2>`, `<a>...<b>`, `<base> <a> <b>` | read | diffs commits; prints patch text |
| with `--ext-diff`/textconv drivers active | executes-config | diff options pass through; never enable them |

## Options that matter

- `--no-color` for evidence files; `--stat`-like brevity via `-s` (`--no-patch`) prints only
  the pairing lines.
- `--creation-factor=<n>`: how different a commit may be and still pair (default 60).
- `--left-only` / `--right-only`.
- `--no-notes`: avoid pulling notes into the output.
- Pairing symbols: `=` identical, `!` changed, `<` only on the left, `>` only on the right.

## Verified recipes

```sh
git --no-replace-objects --no-pager range-diff --no-color -s origin/main...feat/squashed | head -n 50
```

`[observed]` `1: ffde723 < -: ------- squash feat/squashed`, `-: ------- >
1: 52612d7 s1`, `-: ------- > 2: 65bacac s2`: a squash never pairs with its parts.

## Footprint it leaves when interrupted or misused

None.

## Gotchas

- Without `-s` it prints patch lines, which may contain secrets: use `-s` in reports, and
  never on commits flagged by G14.
- Replace refs change both ranges; use `git --no-replace-objects range-diff`.
- A squash or heavy rewrite shows as all `<`/`>`; use the ladder (`merge-tree`) for
  content equivalence.
