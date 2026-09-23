# git archive

Official: https://git-scm.com/docs/git-archive · Areas: G4, G18 · Floor: any

## Purpose in an audit

Show exactly which files a release archive of a revision would contain, to check that
`export-ignore` keeps tests, CI files, fixtures and secrets out, and that `export-subst`
expands where intended.

## Safety class

| Form | Class | Why |
| --- | --- | --- |
| `git archive --format=tar <tree> \| tar -tf -` | read | Streams to stdout; lists names only |
| `-o <file>` / `--output=<file>` | writes-local-state | Writes the archive file (outside the repository) |
| `--format=tgz`, `tar.gz`, custom formats | executes-config | Piped through `tar.<format>.command` when configured `[doc]` |
| `--remote=<repo>` | network | Asks a remote `upload-archive` service |
| `--worktree-attributes` | read | Also reads `.gitattributes` from the working tree |

## Options that matter

- `--format=tar|zip|tar.gz|tgz|<custom>`, `--prefix=<dir>/`, `--add-file`,
  `--add-virtual-file` `[doc]`.
- Attributes `[doc]` gitattributes: `export-ignore` (leave the path out), `export-subst`
  (expand `$Format:…$` placeholders in the file; expansion only, no program runs).
- Config: `tar.<format>.command`, `tar.<format>.remote`, `uploadArchive.allowUnreachable`
  `[doc]`.

## Verified recipes

```sh
git archive --format=tar HEAD | tar -tf - | wc -l
git archive --format=tar HEAD | tar -tf - | head -n 200
git --no-pager ls-files -z | git check-attr --stdin -z export-ignore export-subst \
  | tr '\0' '\n' | paste - - - | awk -F'\t' '$3!="unspecified"' | head -n 40
```

`[observed]`: with `.mailmap export-ignore` and `.github/ export-ignore`, the archive held
only `.gitattributes` and `a`; `check-attr` reported `.mailmap: export-ignore: set` but
`unspecified` for `.github/w.yml`, because the directory pattern applies to the folder.

## Footprint it leaves when interrupted or misused

Only the output file when `-o` is used; a partial file after an interruption.

## Gotchas

- Trust the `tar -tf` listing over per-file `check-attr` for directory rules `[observed]`.
- Hosted "Download ZIP" and release source archives use the same attributes on most hosts;
  confirm per provider.
- The archive is built from the committed tree; untracked or ignored files never appear.
