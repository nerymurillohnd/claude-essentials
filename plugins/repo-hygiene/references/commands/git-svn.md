# git svn

Official: https://git-scm.com/docs/git-svn · Areas: G15, G18 · Floor: any (needs Perl SVN
bindings; often absent)

## Purpose in an audit

Recognize a Subversion bridge or a finished SVN migration: its metadata folder, refs and
config, and whether they are still needed.

## Safety class

| Form | Class | Why |
| --- | --- | --- |
| reading `.git/svn/`, `refs/remotes/git-svn`, `svn-remote.*` config | read | Presence and names |
| `git svn info`, `git svn log` | read + network | May contact the SVN server |
| `git svn fetch`, `rebase`, `dcommit`, `init`, `clone` | network + mutates | Update refs, `.git/svn/`, and the SVN server (`dcommit`) |
| `git svn gc` | mutates | Compresses `unhandled.log`, removes `index` files `[doc]` |
| `git svn reset -r <n>` | mutates | Moves `refs/remotes/git-svn` and the rev_map `[doc]` |

## Options that matter

- Config `[doc]`: `svn-remote.<name>.url`, `.fetch`, `.branches`, `.tags`, `.ignore-paths`,
  `.ignore-refs`, `.include-paths`, `.pushurl`, `.commiturl`, `.noMetadata`, `svn.authorsFile`.
- Files `[doc]`: `$GIT_DIR/svn/**/.rev_map.*` (SVN revision to commit map),
  `$GIT_DIR/svn/<refname>/unhandled.log`, `index`.
- Commits carry `git-svn-id:` lines unless `noMetadata` was used.

## Verified recipes

```sh
ls -d "$(git rev-parse --git-common-dir)/svn" 2>/dev/null
git --no-pager for-each-ref --format='%(refname)' 'refs/remotes/git-svn' 'refs/remotes/svn' | head -n 20
git --no-pager config --show-scope --show-origin --get-regexp '^(svn-remote\.|svn\.)' \
  | sed -E 's#(://)[^/@[:space:]]+@#\1***@#g'
git --no-replace-objects --no-pager log --all --grep='^git-svn-id:' --format=%h | wc -l
```

`[observed]`: all four ran on the fixture with empty results (no bridge); none contacts a
server.

## Footprint it leaves when interrupted or misused

`.git/svn/` (maps, logs, indexes), `refs/remotes/git-svn` or `refs/remotes/svn/*`,
`svn-remote.*` config, `git-svn-id:` lines in messages, and an `authors` file.

## Gotchas

- Removing `.git/svn` breaks further `git svn` use but not Git history; confirm the
  migration is final with the user.
- SVN URLs in config may embed a username: redact.
