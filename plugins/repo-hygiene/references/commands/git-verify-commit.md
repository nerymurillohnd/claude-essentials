# git verify-commit

Official: https://git-scm.com/docs/git-verify-commit · Areas: G13 · Floor: any (SSH
signatures 2.34 `[doc]` RelNotes 2.34.0)

## Purpose in an audit

Check that signed commits on protected branches verify against the keys the project trusts.

## Safety class

| Form | Class | Why |
| --- | --- | --- |
| `git verify-commit <commit>…` | read + executes-config | Runs `gpg.program`, `gpg.ssh.program` or `gpg.x509.program` |
| `-v` / `--verbose` | read + executes-config | Also prints the commit object |
| `--raw` | read + executes-config | Raw status output on stderr |

## Options that matter

- Exit 0 when the signature is good, non-zero otherwise (unsigned included) `[observed]`.
- The signing program comes from `gpg.format` (`openpgp`, `x509`, `ssh`) and the matching
  `gpg.*.program`; SSH verification needs `gpg.ssh.allowedSignersFile` `[doc]`.
- `git log --format='%G? %GS %GK'` gives the same verdict for many commits and also runs the
  program `[doc]`.

## Verified recipes

Before verifying, count signature headers without running any program:

```sh
git --no-replace-objects rev-list --max-count=50 --header HEAD | tr '\0' '\n' | grep -c -E '^gpgsig'
git cat-file commit <commit> | grep -c -E '^gpgsig(-sha256)? '
```

Then, only after `areas/config-links-identity.md` check 7 shows the `gpg.*program` keys unset
or standard:

```sh
git verify-commit <commit>
git --no-replace-objects --no-pager log --max-count=50 --format='%G? %h %ae'
```

`[observed]` with an SSH-signed commit: `Good "git" signature for dev@example.com with
ED25519 key SHA256:…`, exit 0; the unsigned commit exited 1. Without
`gpg.ssh.allowedSignersFile`, `%G?` printed `N` for the signed commit and
`error: gpg.ssh.allowedSignersFile needs to be configured and exist` on stderr.

## Footprint it leaves when interrupted or misused

None in the repository; GnuPG may update its own trust database under `~/.gnupg`.

## Gotchas

- `N` from `%G?` is not proof of an unsigned commit (see above) `[observed]`.
- A repository can set `gpg.program` in `.git/config` to any program: never verify in an
  untrusted repository before reading that key.
- History rewrites (filter-repo, rebase) drop signatures; count them before a rewrite.
