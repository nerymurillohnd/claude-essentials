# git grep

Official: https://git-scm.com/docs/git-grep · Areas: G14, G19, G21 · Floor: any (`--untracked`
1.7.8, `--column` 2.19, `-m` 2.38 `[doc]` RelNotes)

## Purpose in an audit

Search tracked content in the working tree, the index or any tree: token formats still in the
current tree, third-party URLs and CI pins, and where a string lives now.

## Safety class

| Form | Class | Why |
| --- | --- | --- |
| tracked files, `--cached`, `<tree>…` | read | Searches Git-known content |
| `--untracked` | read | Adds untracked, non-ignored files |
| `--untracked --no-exclude-standard` without exclusions | read, **forbidden** | Reached an ignored `.env` `[observed]` |
| `--no-index` | read | Searches any directory; needs the same exclusions |
| `--textconv` | executes-config | Runs `diff.<driver>.textconv` |
| `-O` / `--open-files-in-pager` | executes-config | Starts the pager or editor on matches |

## Options that matter

- Where: default working tree (tracked), `--cached` (index), `<tree>` revisions before `--`,
  `--untracked`, `--no-exclude-standard`, `--no-index`, `--recurse-submodules` (not with
  `--untracked`) `[doc]`.
- Patterns: `-e` (repeatable), `--and`, `--or`, `--not`, `(`, `)`, `--all-match`,
  `-f <file>` `[doc]`.
- Flavors: `-G` basic (default), `-E` extended, `-F` fixed, `-P` Perl (dies when Git was built
  without PCRE `[doc]`; available in Homebrew Git 2.55 `[observed]`).
- Matching: `-w`, `-i`, `-v`, `-I` (skip binary), `--max-depth`.
- Output: `-n`, `--column`, `-l`, `-L`, `-c`, `-q` (exit 0 match / 1 none `[observed]`),
  `-z`, `-h`/`-H`, `-o`, `-m <n>`/`--max-count` (per file).
- Pathspec magic: `':(exclude,glob)**/.env*'`, `':(glob)**/*.yml'` `[doc]` gitglossary.

## Verified recipes

```sh
git --no-pager grep -n --column -e 'uses' --and -e 'actions' -- .github
git --no-pager grep -n --cached 'staged-only'
git --no-pager grep -n -F 'b' HEAD~2 -- a
git --no-pager grep -n -E 'uses:[[:space:]]*[^[:space:]#]+@' -- '.github/workflows' \
  | grep -v -E '@[0-9a-f]{40}([^0-9a-f]|$)'
git --no-pager grep -l --untracked --no-exclude-standard -e 'pattern' -- \
  ':(exclude,glob)**/.env*' ':(exclude,glob)**/*.pem' ':(exclude,glob)**/*.key' \
  ':(exclude,glob)**/id_*' ':(exclude,glob)**/credentials*' ':(exclude,glob)**/.npmrc' \
  ':(exclude,glob)**/.pypirc' ':(exclude,glob)**/.netrc' ':(exclude,glob)**/*.tfvars' \
  ':(exclude,glob)**/.dev.vars' ':(exclude,glob)**/*.p12' ':(exclude,glob)**/*.pfx' \
  ':(exclude,glob)**/node_modules/**'
```

`[observed]`: each recipe returned the expected hits on the fixtures (see
`areas/tracing.md` checks 1-3 and `areas/footprints-and-references.md` check 8); the
exclusion list kept `.env` out while ignored build output was still searched.

## Footprint it leaves when interrupted or misused

None, unless `-O` opened files in an editor.

## Gotchas

- Plain `git grep` searches only tracked files: absence is not proof (untracked, ignored,
  binary with `-I`, other revisions).
- `-l` on a secret file name is acceptable; `-n` on it prints the secret line. Exclude first.
- A tree search (`HEAD~2`) prefixes hits with `HEAD~2:`; revisions go before `--`.
