# git remote

Official: https://git-scm.com/docs/git-remote · Areas: G6 · Floor: any
(`get-url` 2.7)

## Purpose in an audit

List remotes and their layout, find stale tracking refs (`show`, `prune --dry-run`), and, as
approved items, remove, rename or fix remotes.

## Safety class

| Form | Class | Why |
| --- | --- | --- |
| `git remote`, `-v` | read | prints URLs: redact in the same command |
| `get-url [--push] [--all] <n>` | read | prints URLs: redact |
| `show -n <n>` | read | config only, no network |
| `show <n>` | network, executes-config | queries the remote |
| `prune --dry-run <n>` | network | lists stale tracking refs, deletes nothing |
| `prune <n>`, `update --prune` | network, mutates | deletes tracking refs and their reflogs |
| `add`, `rename`, `remove`, `set-url`, `set-branches`, `set-head` | mutates | config and refs; `remove` deletes every `refs/remotes/<n>/*` |
| `set-head --auto` | network, mutates | queries the server's HEAD and writes `refs/remotes/<n>/HEAD` |
| `add -f`, `update` | network, mutates | fetch |

## Options that matter

- `-v`: URLs for fetch and push; `pushurl` shows on the push line.
- `get-url --push --all`: every push URL (a remote may have several).
- `show -n`: no network, still lists tracked-branch config.
- `set-url --delete`, `set-url --add --push`: multi-URL remotes.
- `--mirror=fetch|push` on `add`: mirror remotes delete on push.

## Verified recipes

```sh
git --no-pager remote -v | sed -E 's#(://)[^/@[:space:]]+@#\1***@#g'
git --no-pager remote get-url --all --push origin | sed -E 's#(://)[^/@[:space:]]+@#\1***@#g'
git --no-pager remote show -n origin | sed -E 's#(://)[^/@[:space:]]+@#\1***@#g' | head -n 20
git --no-pager remote prune --dry-run origin
git --no-pager remote show origin | sed -E 's#(://)[^/@[:space:]]+@#\1***@#g'
```

`[observed]`: `backup https://***@example.com/r.git`; `show -n` printed `HEAD branch: (not
queried)`; `prune --dry-run` printed `* [would prune] origin/feat/abandoned`; `show`
printed `refs/remotes/origin/feat/abandoned stale (use 'git remote prune' to remove)`.

## Footprint it leaves when interrupted or misused

`remove` and `rename` rewrite config sections and move or delete tracking refs;
`branch.<b>.remote` entries of removed remotes are cleaned for that remote, but refspecs
typed by hand elsewhere are not.

## Gotchas

- `git remote -v` prints embedded credentials verbatim; `[observed]` without the `sed` it
  showed the user name and token in clear (contract section 4).
- `prune` cannot be undone for branches the server deleted: the tracking ref was the last
  local copy of that tip.
- A remote name containing dots breaks naive `remote\.[^.]+\.` parsing of config keys.
