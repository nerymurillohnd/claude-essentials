# git config

Official: https://git-scm.com/docs/git-config · Areas: G11, G12, G13, G20 · Floor: any
(`--show-origin` 2.8, `--show-scope` 2.26, `list`/`get`/`set` subcommands 2.46)

## Purpose in an audit

Show every setting that shapes this repository, where it comes from (scope and file), and
which settings run programs, rewrite URLs, pull in other files or hold secrets.

## Safety class

| Form | Class | Why |
| --- | --- | --- |
| `--list`, `list`, `--get`, `get`, `--get-regexp`, `--get-all`, `--get-urlmatch` | read | Prints values; redact in the same command |
| `--name-only`, `--show-origin`, `--show-scope` | read | Metadata only |
| `--file <path>` / `--blob <blob>` reads | read | Reads one file or blob; includes off by default |
| `set`, `--add`, `unset`, `--unset`, `--replace-all`, `rename-section`, `remove-section` | mutates | Writes a config file |
| `--edit`, `edit` | executes-config | Opens `core.editor` / `GIT_EDITOR` |
| `--includes` on `--file` | read | Follows `include.*`; may read files outside the repository |

## Options that matter

- Scopes: `--system`, `--global`, `--local`, `--worktree`, `--file <path>`; reading without
  one merges all, writing without one writes `--local` `[doc]`. Scope `command` covers
  `git -c` and `GIT_CONFIG_{COUNT,KEY,VALUE}` `[doc]`.
- `--show-scope` (worktree, local, global, system, command) and `--show-origin`
  (`file:<path>`, `blob:`, `command line:`) `[doc]`.
- `--name-only` prints keys without values: the safe default for a first listing.
- `-z` / `--null` for values with newlines.
- `--includes` / `--no-includes`: on when reading all scopes, off with `--file`,
  `--global` etc. `[doc]`.
- `--type=bool|int|path|url|color|expiry-date` canonicalizes values.
- Exit codes `[doc]`: 1 key missing or invalid section/key, 3 invalid file, 5 unset of a
  missing or multi-matching key, 6 invalid regexp.
- Protected configuration = system, global and command scopes; some keys are honored only
  there (`safe.directory`, `uploadpack.packObjectsHook`, `trace2.*`) `[doc]`.
- Environment: `GIT_CONFIG_GLOBAL`, `GIT_CONFIG_SYSTEM`, `GIT_CONFIG_NOSYSTEM`,
  `GIT_CONFIG_COUNT`/`KEY_n`/`VALUE_n` (override files, overridden by `-c`) `[doc]`.
- `includeIf` conditions: `gitdir:`, `gitdir/i:`, `onbranch:`, `hasconfig:remote.*.url:`
  `[doc]`.

## Verified recipes

```sh
git --no-pager config --list --show-scope --show-origin --name-only | head -n 80
git --no-pager config --list --show-origin --show-scope \
  | sed -E -e 's#(://)[^/@[:space:]]+@#\1***@#g' \
           -e 's#^([^=]*(pass|token|secret|key|auth|cred)[^=]*=).*#\1***#I'
git --no-pager config --show-scope --show-origin --get-regexp '^url\..*\.(insteadof|pushinsteadof)$'
git --no-pager config --show-scope --show-origin --get-regexp '^include(if)?\.'
git config --file .gitmodules --get-regexp '^submodule\..*\.(url|branch)'
```

`[observed]` on 2.55: `--name-only` with both flags prints `scope<TAB>origin<TAB>key`;
`--get-regexp` with both prints `scope<TAB>origin<TAB>key value`; no match exits 1 with no
output. The full executing-key pattern is in `areas/config-links-identity.md` check 7.

## Footprint it leaves when interrupted or misused

- A write leaves `config.lock` next to the file if interrupted; a stale lock blocks every
  later write (`areas/repository-and-operations.md`).
- `--global` / `--system` writes change every repository of the user or machine: an
  approved item must name the scope.
- `git config` (no subcommand) with a key and value **sets** it: never type a read with two
  arguments.

## Gotchas

- Keys are case-insensitive in section and name, and printed lowercased
  (`core.hookspath`) `[observed]`; subsections keep their case.
- `git remote -v` shows URLs after `insteadOf`; the stored value is
  `remote.<name>.url` `[observed]`.
- A regexp word that contains both `$` and a `git`-like key can be refused by the
  `block-no-verify` guard; keep such patterns unanchored `[observed]`.
- The local `commit.gpgSign false` and `gpg.ssh.program` writes are refused by the same
  guard as signing bypasses `[observed]`: never try to work around it.
- Values of `credential.*`, `http.*.extraHeader`, `sendemail.smtpPass` and URLs can hold
  secrets; print names first.
