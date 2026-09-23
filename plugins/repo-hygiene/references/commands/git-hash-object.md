# git hash-object

Official: https://git-scm.com/docs/git-hash-object · Areas: G14, G16, G17 · Floor: any

## Purpose in an audit

Fingerprint a file without printing it: compute the Git object ID of an unknown payload
(`lost-found` files, `rr-cache` preimages, hook scripts) and check it against the object
store or a file name, as the contract requires (`audit-contract.md` section 4, D14 X4).

## Safety class

| Form | Class | Why |
| --- | --- | --- |
| `git hash-object --stdin <file` | read | No filters unless `--path` is given `[doc]`; no clean filter ran `[observed]` |
| `git hash-object --no-filters <file>` | read | Filters and EOL conversion skipped `[doc]` `[observed]` |
| `git hash-object <file>` | executes-config | Applies the attribute-selected clean filter `[observed]` |
| `git hash-object --stdin --path=<p>` | executes-config | Applies the filter chosen for `<p>` `[observed]` |
| `-t <type>` without `-w` | read | Validates the content as that type |
| `-w` | mutates | Writes the object into the object store |
| `--literally` | mutates with `-w` | Writes malformed objects; never use |

## Options that matter

- `-t commit|tree|blob|tag` (default blob); invalid content for the type is refused with
  exit 128 `[observed]`.
- `--stdin`, `--stdin-paths`, `--path=<p>`, `--no-filters`, `-w`, `--literally` `[doc]`.

## Verified recipes

```sh
git hash-object --stdin --no-filters < .git/lost-found/other/<name>
wc -c < .git/lost-found/other/<name>
file -b .git/lost-found/other/<name>
git cat-file -e <printed-id> && echo present || echo absent
git hash-object -t commit --stdin < <file>
```

`[observed]`: a 7-byte ASCII file hashed to a blob ID without printing its content;
`-t commit` on it failed with `error: object fails fsck: missingTree` and
`fatal: refusing to create malformed object` (exit 128); `-t commit` on real commit content
returned the same ID as `git rev-parse HEAD`. A `lost-found/other/<name>` file whose blob
hash equals its name is intact.

## Footprint it leaves when interrupted or misused

`-w` adds a loose object (it counts in `count-objects` and survives until `gc` prunes it).
Never use `-w` during an audit.

## Gotchas

- `git hash-object <path>` ran a `filter.<driver>.clean` program configured for that path
  `[observed]`: always use `--stdin` without `--path`, or `--no-filters`.
- A type trial reads the content into Git but prints only an ID or an error; it never prints
  the content.
