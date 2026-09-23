# git tag

Official: https://git-scm.com/docs/git-tag · Areas: G7 · Floor: any

## Purpose in an audit

List tags with filters, verify signatures, and, as approved items, create archive tags
(preservation) or delete and move tags. For typed inventories use
`commands/git-for-each-ref.md` on `refs/tags`.

## Safety class

| Form | Class | Why |
| --- | --- | --- |
| `-l`, `--list`, `--contains`, `--no-contains`, `--merged`, `--no-merged`, `--points-at`, `--format`, `-n<num>` | read | lists refs |
| `-v <tag>` | executes-config | runs `gpg.program` / `gpg.ssh.program` to verify |
| `<name> [<commit>]` (lightweight) | mutates | creates a ref |
| `-a`/`-m`/`-F` | mutates | writes a tag object and a ref; `-e` opens the editor |
| `-s`/`-u <key>` | mutates, executes-config | signs via the configured program |
| `-f` | mutates | moves an existing tag |
| `-d <tag>` | mutates | deletes a tag ref (the tag object stays until gc) |

## Options that matter

- `--no-merged <commit>`: tags whose target is not reachable from `<commit>`.
- `--points-at <object>`: tags on a given commit.
- `--sort=version:refname` or `--sort=-creatordate`.
- `--create-reflog`: tags normally have no reflog; this records one.
- `tag.gpgSign`, `tag.forceSignAnnotated`: signing policy in config.

## Verified recipes

```sh
git --no-pager tag --no-merged origin/main
git --no-pager for-each-ref --format='%(refname:short) %(objecttype) sig=%(if)%(contents:signature)%(then)yes%(else)no%(end)' refs/tags
git --no-pager tag -v v0.2 2>&1 | tail -n 1
```

`[observed]` `v0.2`, `v0.3` not merged into the stale `origin/main`; unsigned annotated tag
→ "error: no signature found" (exit 1); a lightweight tag → "cannot verify a non-tag object
of type commit". Approved items, literal:

```sh
git tag archive/wip-unique f35123d1dcf5518d29f085532fd29528b733651d
git tag -d local-only
```

Undo for `-d`: `git tag local-only e13d5701110373cb06adec8baa1d46d26ce421e5` (for an
annotated tag, re-point to the **tag object** OID recorded from `%(objectname)`, not the
commit).

## Footprint it leaves when interrupted or misused

`-a` with an editor left open leaves `TAG_EDITMSG`. A deleted annotated tag leaves an
unreachable tag object until gc.

## Gotchas

- A lightweight tag has no tagger, date or message: `%(taggerdate)` is empty.
- Deleting a tag locally does not delete it on the server, and the next fetch with tag
  auto-following may bring it back.
- `tag -v` prints the tag's content before the verdict; harmless for tag objects, but it
  executes GPG: `deep` only, after the trust preflight.
