# git verify-tag

Official: https://git-scm.com/docs/git-verify-tag · Areas: G7, G13 · Floor: any

## Purpose in an audit

Check that release tags meant to be signed carry a valid signature.

## Safety class

| Form | Class | Why |
| --- | --- | --- |
| `git verify-tag <tag>…` | read + executes-config | Runs the configured signing program |
| `--format=<fmt>` | read + executes-config | Prints tag fields after verifying |
| `-v`, `--raw` | read + executes-config | Tag object / raw status output |

## Options that matter

- Exit 0 only for a good signature; an unsigned annotated tag prints
  `error: no signature found` and exits 1 `[observed]`.
- Lightweight tags have no tag object and cannot be signed: `git verify-tag v0.1` printed
  `error: v0.1: cannot verify a non-tag object of type commit.` and exited 1 `[observed]`.
- `--format` uses `for-each-ref` placeholders.

## Verified recipes

Count signed tags without running any program:

```sh
git --no-pager for-each-ref refs/tags --format='%(refname:short) %(objecttype) %(contents:signature)' \
  | grep -c 'BEGIN'
git --no-pager for-each-ref refs/tags --format='%(objecttype)' | sort | uniq -c
```

Then, after the signing-program check in `areas/config-links-identity.md` check 7:

```sh
git verify-tag v0.2
```

`[observed]`: `error: no signature found`, exit 1, for the fixture's unsigned annotated tag
`v0.2`; `for-each-ref` counted 0 signed tags and `1 commit` + `1 tag` object types (one
lightweight, one annotated).

## Footprint it leaves when interrupted or misused

None in the repository.

## Gotchas

- A tag moved on the remote (`areas/branches-remotes-tags.md`) can verify locally and still
  differ from the published one; compare object IDs too.
- Same program-execution caveat as `commands/git-verify-commit.md`.
