# git push

Official: https://git-scm.com/docs/git-push · Areas: G5, G6, G7 · Floor: any
(`--force-if-includes` 2.30)

## Purpose in an audit

Never an inspection tool. It appears only in approved, outward-facing items (publish a tag,
delete a server branch) and in the project's own delivery flow. A push is not reversible for
people who already fetched.

## Safety class

| Form | Class | Why |
| --- | --- | --- |
| `git push <remote> <ref>` | network, mutates, executes-config | updates the server; runs `pre-push` hook, credential helper, SSH command |
| `--dry-run` / `-n` | network, executes-config | sends nothing, but **runs the `pre-push` hook** `[observed]` |
| `--delete <ref>`, `:<ref>` | network, mutates | deletes a server ref |
| `--force`, `+<refspec>` | network, mutates | overwrites server history |
| `--force-with-lease[=<ref>[:<expect>]]` | network, mutates | force only if the server ref is still what you expect |
| `--force-if-includes` | network, mutates | with lease: also require the remote tip to be in the local reflog (2.30) |
| `--mirror` | network, mutates | pushes and **deletes** every ref to match local |
| `--prune` | network, mutates | deletes server refs without a local counterpart |
| `--all`, `--branches`, `--tags` | network, mutates | pushes many refs at once |
| `--no-verify` | executes-config bypass | skips `pre-push`; never used by this plugin |

## Options that matter

- `--porcelain`: machine-readable result lines.
- `--atomic`: all refs or none.
- `--follow-tags`: annotated tags reachable from pushed commits.
- `remote.<n>.mirror=true` or `push.default=mirror`-style config turns a plain push into a
  mirror push: check it before any push item (`areas/branches-remotes-tags.md` check 9).
- `remote.pushDefault`, `branch.<b>.pushRemote`, `push.default`: where a bare `git push`
  goes.

## Verified recipes

Only as approved items, literal, one per call:

```sh
git push origin refs/tags/v0.1
git push origin --delete refs/heads/feat/abandoned
```

Not run on the fixture (the contract forbids pushing). `[observed]` on a scratch repository:
`git push --dry-run origin side` with a `pre-push` hook that exits 1 printed the hook's
output and failed; the remote received nothing.

## Footprint it leaves when interrupted or misused

Remote-tracking refs updated for pushed branches (and their reflogs, `update by push`); a
partially applied non-atomic push; on the server, reflog entries only if the server keeps
them.

## Gotchas

- `--dry-run` is not a safe read: it executes the repository's `pre-push` hook.
- Deleting a server branch that an open PR uses closes or breaks that PR.
- `--force-with-lease` without an explicit expected value trusts the local tracking ref,
  which a background fetch may have updated; give `--force-with-lease=<ref>:<sha>`.
- A tag deleted on the server stays in every clone that fetched it; say so in the risk line.
