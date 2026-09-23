# git update-ref

Official: https://git-scm.com/docs/git-update-ref · Areas: G15, G16 · Floor: any

## Purpose in an audit

The precise tool for approved ref items: pin a recovery candidate under
`refs/recovered/<date>/…`, delete one exact ref only if it still has the recorded value,
or apply several ref changes atomically. It never touches the index or working tree.

## Safety class

| Form | Class | Why |
| --- | --- | --- |
| `update-ref <ref> <new> [<old>]` | mutates, executes-config | writes a ref; runs the `reference-transaction` hook |
| `update-ref -d <ref> [<old>]` | mutates | deletes a ref and its reflog |
| `update-ref --stdin [-z] [--batch-updates]` | mutates | transaction of `create`/`update`/`delete`/`verify` lines |
| `--no-deref` | mutates | acts on a symbolic ref itself, not its target |

## Options that matter

- `<old>` = `''` (empty): the ref must **not** exist (create-only).
- `<old>` = `<sha>`: compare-and-swap; the command fails if the ref moved.
- `-m <reason>`: reflog message (only written if the ref has or gets a reflog).
- `--create-reflog`: force a reflog for refs outside heads/remotes/notes.
- `--stdin` lines: `create <ref> <new>`, `update <ref> <new> [<old>]`, `delete <ref>
  [<old>]`, `verify <ref> [<old>]`, plus `start`/`prepare`/`commit`/`abort`.

## Verified recipes

Approved items, literal, one per call:

```sh
git update-ref -m 'repo-hygiene R1' refs/recovered/2026-09-22/lost-commit faafec8f8fd4a95b9040be2fc2cc36f07c41a1a8 ''
git update-ref -d refs/recovered/2026-09-22/lost-commit faafec8f8fd4a95b9040be2fc2cc36f07c41a1a8
```

`[observed]` the first ran with exit 0; repeating it failed with "reference already
exists", exit 128; the pinned commit disappeared from `fsck --unreachable --no-reflogs`;
the pin had no reflog. Deleting a whole namespace through Git (not `rm`):

```sh
git for-each-ref --format='delete %(refname)' refs/original | git update-ref --stdin
```

`[observed]` exit 0 and `refs/original` empty afterwards (this pipeline is not a literal
single ref; list the refs in the item and verify the count after).

## Footprint it leaves when interrupted or misused

`<ref>.lock` files; with `--no-deref` misuse, a symbolic ref (such as HEAD) turned into a
regular ref.

## Gotchas

- Without `<old>` it overwrites silently; always pass the recorded value.
- It accepts any object type: a ref may end up pointing at a tree or blob (that is how tool
  refs like `refs/codex/*` exist) `[observed]` (`blob refs/tool/blobref`).
- It refuses an object that does not exist `[observed]` ("trying to write ref … with
  nonexistent object").
- `reference-transaction` hooks run on every update: G12 inventories them.
