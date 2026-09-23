# git check-attr

Official: https://git-scm.com/docs/git-check-attr · Areas: G4, G18 · Floor: any

## Purpose in an audit

Shows which attributes apply to a path (`text`, `eol`, `binary`, `filter`, `diff`,
`merge`, `export-ignore`, …) and lets you compare the working-tree `.gitattributes`, the
index version, and any commit's version. It explains line-ending drift and missing
filter drivers without running them.

## Safety class

| Form | Class | Why |
| --- | --- | --- |
| every form | read | Evaluates attribute files only; it never runs a filter, diff or merge driver |

## Options that matter

- `-a`, `--all`: every attribute set on the path; unspecified ones are omitted `[doc]`.
- `<attr>… --`: query named attributes; without `--`, `--all` or `--stdin` the first
  argument is taken as the attribute `[doc]`.
- `--cached`: use only `.gitattributes` from the index `[doc]`.
- `--source=<tree-ish>`: evaluate against the attribute files of a commit or tree `[doc]`.
- `--stdin`, `-z`: stream paths; `-z` output is `<path> NUL <attribute> NUL <info> NUL`
  `[doc]`.
- Values: `unspecified`, `unset` (`-attr`), `set` (`attr`), or a string (`attr=value`)
  `[doc]`.

## Verified recipes

```sh
git --no-pager check-attr --all -- crlf.txt run.sh big.bin x.psd
```

`[observed]`: `crlf.txt: text: auto`; `run.sh: text: set`, `run.sh: eol: lf`;
`big.bin: binary: set` plus `diff`, `merge`, `text` unset (the `binary` macro);
`x.psd: filter: lfs`, `diff: lfs`, `merge: lfs`, `text: unset`.

```sh
git --no-pager check-attr --cached --all -- x.psd
```

`[observed]`: `x.psd: text: auto` only, because the `*.psd` line existed in the working
tree `.gitattributes` but not in the index.

```sh
git --no-pager check-attr --source=HEAD --all -- run.sh
```

`[observed]`: `text: set`, `eol: lf` from the committed file.

```sh
git --no-pager check-attr -z text eol -- crlf.txt | tr '\0' '|'
```

`[observed]`: `crlf.txt|text|auto|crlf.txt|eol|unspecified|`.

## Footprint it leaves when interrupted or misused

None.

## Gotchas

- An attribute naming a driver (`filter=lfs`) says nothing about whether the driver is
  configured; check `git config --name-only --get-regexp '^filter\.'` (exit 1 when none)
  `[observed]`.
- Attribute sources also include `core.attributesFile` (global),
  `$GIT_DIR/info/attributes`, and the system file (`git var GIT_ATTR_SYSTEM`,
  `git var GIT_ATTR_GLOBAL` print their paths `[observed]`).
- `--all` hides `unspecified`; to prove an attribute is absent, query it by name.
- Macro attributes (`binary`) expand into several lines `[observed]`.
