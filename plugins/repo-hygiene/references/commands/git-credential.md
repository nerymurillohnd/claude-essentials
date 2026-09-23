# git credential

Official: https://git-scm.com/docs/git-credential · Areas: G11, G12 · Floor: any
(`capability` action present in 2.55 `[observed]`)

## Purpose in an audit

Understand, never exercise, how Git obtains credentials for this repository. The audit
inventories helper **names** from config (`areas/config-links-identity.md` check 4); it does
not call this command to fetch or store anything.

## Safety class

| Form | Class | Why |
| --- | --- | --- |
| `git credential capability` | read | Prints the protocol capabilities of Git itself |
| `git credential fill` | executes-config | Runs every `credential.helper`, may prompt, and **prints the password** |
| `git credential approve` | mutates | Sends the credential to helpers, which may store it (outside the repository) |
| `git credential reject` | mutates | Asks helpers to erase matching credentials |
| `git credential-cache exit` / `git credential-store` | mutates | Stop the cache daemon / write `~/.git-credentials` |

## Options that matter

- Input is a `key=value` description ending with a blank line (`protocol`, `host`, `path`,
  `username`, `password`, `url`) `[doc]`.
- Config that decides which helpers run `[doc]`: `credential.helper` (multi-valued; an
  empty value resets the list), `credential.<url>.helper`, `credential.useHttpPath`,
  `credential.username`, `credential.interactive`. A value starting with `!` is a shell
  command. Cache socket: `$XDG_CACHE_HOME/git/credential/socket`, or
  `~/.git-credential-cache/socket` when that folder exists `[doc]`. Store file:
  `~/.git-credentials` or `$XDG_CONFIG_HOME/git/credentials` `[doc]`.
- `GIT_TERMINAL_PROMPT=0` stops terminal prompts for network reads; `-c credential.helper=`
  clears the helper list for one command `[doc]`.

## Verified recipes

```sh
git credential capability </dev/null
git --no-pager config --show-scope --show-origin --get-regexp '^credential\..*helper' \
  | sed -E -e 's#^(([^[:blank:]]+[[:blank:]]+){2}credential\.[^ ]*helper) !.*#\1 !<inline shell, redacted>#' \
           -e 's#(://)[^/@[:space:]]+@#\1***@#g'
GIT_TERMINAL_PROMPT=0 git -c credential.helper= ls-remote --exit-code ../origin.git refs/heads/main
```

`[observed]`: `capability` printed `version 0`, `capability authtype`, `capability state`;
the helper listing showed `system … credential.helper osxkeychain` and masked an inline `!`
helper; the `ls-remote` read succeeded with helpers cleared.

## Footprint it leaves when interrupted or misused

- `fill` output in a transcript is a leaked secret: rotate it.
- `credential-store` writes plaintext `~/.git-credentials` (or `--file`); report its
  presence, size and mode, never its content.
- `credential-cache` leaves a daemon socket at the paths listed above.

## Gotchas

- Any network read (`ls-remote`, `fetch`) can trigger helpers and prompts; clear helpers and
  prompts for audit reads to a third-party URL.
- Helpers in system scope (Homebrew's `osxkeychain`) are normal; inline `!` helpers in local
  scope are a finding.
