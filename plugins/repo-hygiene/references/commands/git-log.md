# git log

Official: https://git-scm.com/docs/git-log · Areas: G5, G13, G14, G16, G21 · Floor: any
(`-L` 1.8.4, `--find-object` 2.17 `[doc]` RelNotes)

## Purpose in an audit

Walk history: who changed what and when, which commits added or removed a string (pickaxe),
where a line range or file came from, identity and trailer inventories, and which commits
hold large or secret-shaped paths.

## Safety class

| Form | Class | Why |
| --- | --- | --- |
| `--format=…`, `--name-only`, `--name-status`, `--stat`, `--numstat`, `--shortstat`, `--raw` | read | No content conversion `[observed]` |
| `-S`, `-G`, `-L`, `-p`, `--patch` **without** `--no-textconv` | executes-config | Runs `diff.<driver>.textconv` `[observed]` |
| the same **with** `--no-textconv` | read | Driver not run `[observed]` |
| `--ext-diff` | executes-config | Runs `diff.<driver>.command` / `diff.external` |
| `--show-signature`, `%G?`, `%GS`, `%GK` | read + executes-config | Runs the signing program |
| any form, secret-shaped path with `-p` | read, **forbidden** | Prints secret lines |

## Options that matter

- Revisions and walk: `--all`, `--branches`, `--tags`, `--remotes`, `--reflog` (adds every
  reflog entry), `--first-parent`, `--since`/`--until`, `--max-count`, `A..B`, `A...B`,
  `--left-right`, `--cherry-pick` `[doc]`.
- Pickaxe: `-S<string>` (occurrence count changes; binary files searched too),
  `--pickaxe-regex`, `-G<regex>` (added/removed lines match; binary skipped unless
  `--text`), `--pickaxe-all`, `--find-object=<oid>` `[doc]`.
- Regex flavor for `--grep`/`--author`: `-E`, `-F`, `-P`, `-i` `[doc]`. `-G` matched ERE
  syntax with or without `-E` `[observed]`.
- Lines and files: `-L<start>,<end>:<file>`, `-L:<funcname>:<file>` (one positive revision,
  no pathspec), `--follow` (one file), `-M[<n>]`, `-C[<n>]`, `--diff-filter=ADMR…` `[doc]`.
- Identity: `%an/%ae` raw, `%aN/%aE` mailmapped, `--use-mailmap`/`--no-mailmap`;
  `%(trailers:key=…,valueonly,separator=…,only,unfold)` `[doc]`.
- `--ignore-cr-at-eol`, `-w` to hide whitespace-only changes.
- Safety: `--no-textconv`, `--no-ext-diff`, and the global `git --no-replace-objects`.

## Verified recipes

```sh
git --no-replace-objects --no-pager log --all --no-textconv --extended-regexp \
  -G'ghp_[A-Za-z0-9]{20,}' --format='%h %ad' --date=short --name-only
git --no-replace-objects --no-pager log --all --no-textconv \
  --find-object=d71cf43961df814dc010963df1d3489f95850b12 --format='%h %s' --name-status
git --no-replace-objects --no-pager log --no-textconv -L ':alpha:m.py' --format='%h %s' --no-patch
git --no-replace-objects --no-pager log --no-textconv --follow -M --format='%h %s' --name-status -- h.py
git --no-replace-objects --no-pager log --all --format='%an <%ae>|%cn <%ce>' | sort | uniq -c
```

`[observed]`: the pickaxe found the planted token path in two commits with no line content;
`--find-object` returned the add and delete commits of `blob.dat`; `-L` listed two commits
of `alpha`; `--follow` crossed a rename and then a copy (`C084 m.py g.py`).

## Footprint it leaves when interrupted or misused

None in the repository. A pager (`core.pager`, `pager.log`) runs unless `--no-pager`.

## Gotchas

- `git log --no-replace-objects` fails with `fatal: unrecognized argument`; the option is
  global: `git --no-replace-objects log` `[observed]`.
- Textconv drivers run by default for `log` (the page says textconv is on by default only
  for `git diff` and `git log`) `[doc]`; `-S`, `-G`, `-L` and `-p` triggered one
  `[observed]`.
- `--all` does not include older stash entries or reflog-only commits; add `--reflog`.
- `-L` does not follow lines moved from another file; `--follow` may follow a copy into an
  unrelated file's history `[observed]`.
- `%G?` prints `N` for SSH-signed commits when `gpg.ssh.allowedSignersFile` is missing
  `[observed]`.
