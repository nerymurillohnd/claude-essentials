# git name-rev

Official: https://git-scm.com/docs/git-name-rev · Areas: G16, G21 · Floor: any
(`--annotate-stdin` 2.36, replaces `--stdin`)

## Purpose in an audit

Give a symbolic name (`feat/squashed`, `tags/v0.2~3`) to an OID: tells whether a commit is
reachable from any ref and from which one. `undefined` means no ref reaches it.

## Safety class

| Form | Class | Why |
| --- | --- | --- |
| every form | read | walks from refs |

## Options that matter

- `--name-only`: print only the name.
- `--no-undefined`: exit non-zero instead of printing `undefined`.
- `--tags`, `--refs=<pattern>`, `--exclude=<pattern>`: restrict the naming refs.
- `--annotate-stdin`: rewrite every OID found in stdin text as `<oid> (<name>)`.
- `--all`: name every commit (large output; bound it).

## Verified recipes

```sh
git --no-replace-objects name-rev --name-only faafec8
git --no-replace-objects name-rev --name-only --no-undefined faafec8; echo "exit=$?"
printf 'x 65bacac9cd862bcb4a697ade1b5749096ee0c294 y\n' | git --no-replace-objects name-rev --annotate-stdin
```

`[observed]` `undefined` (reachable only from a reflog); "fatal: cannot describe …", exit
128; `x 65bacac… (feat/squashed) y`.

## Footprint it leaves when interrupted or misused

None.

## Gotchas

- Reflog entries do not name commits: a commit reachable only from a reflog is `undefined`
  (but not lost; see `areas/refs-reflogs-recovery.md`).
- A stash entry below the top is also `undefined` `[observed]` (`5e272dc`).
- Names use the shortest path found, which may go through `refs/original` or tool refs;
  restrict with `--refs='refs/heads/*'` when that matters.
