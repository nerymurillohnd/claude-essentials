# git ls-remote

Official: https://git-scm.com/docs/git-ls-remote · Areas: G5, G6, G7, G19 · Floor: any
(`--branches` 2.46)

## Purpose in an audit

The authoritative read of what a remote has right now, without changing any local ref or
object: pin the ladder base, find stale tracking refs, local-only / remote-only / moved
tags, dead remotes, and namespaces nobody fetches (`refs/pull/*`).

## Safety class

| Form | Class | Why |
| --- | --- | --- |
| `git ls-remote [<options>] <remote> [<patterns>]` | network, executes-config | contacts the remote; runs the credential helper, `core.sshCommand`/`GIT_SSH_COMMAND`, remote helpers, `url.*.insteadOf` rewriting; writes nothing locally |

The contract counts it as a read. In `deep`, run it after the trust preflight: an untrusted
repository's `core.sshCommand` or credential helper executes.

## Options that matter

- `--branches` / `-b` (2.46), `--tags` / `-t`. `--heads` and `-h` are deprecated synonyms;
  `-h` alone prints help `[doc]`.
- `--refs`: drop peeled `^{}` lines and pseudo-refs.
- `--symref`: show what `HEAD` points to (`ref: refs/heads/main HEAD`).
- `--exit-code`: exit 2 when no ref matched.
- `--get-url`: print the resolved URL (after `insteadOf`) without contacting the remote;
  redact it.
- `-o`/`--server-option`: protocol v2 options.
- Patterns match the tail of the ref name.

## Verified recipes

```sh
git --no-pager ls-remote --symref origin HEAD
git --no-pager ls-remote --branches origin
git --no-pager ls-remote --tags --refs origin | awk '{print $2, $1}' | sort
git --no-pager ls-remote origin | awk '{print $2}' | awk -F/ '{print $1"/"$2}' | sort | uniq -c
GIT_TERMINAL_PROMPT=0 git -c http.lowSpeedLimit=1 -c http.lowSpeedTime=15 --no-pager \
  ls-remote --branches backup 2>&1 | sed -E 's#(://)[^/@[:space:]]+@#\1***@#g' | head -n 5
```

`[observed]`: `ref: refs/heads/main HEAD`; the server's `main` at `aa2face` while the local
`origin/main` was `ffde723` (stale base); the dead remote exited 128 with "repository …
not found", and Git removed the credential from its own message.

## Footprint it leaves when interrupted or misused

None locally. On the server: an access-log entry, and the credential helper may cache or
prompt (set `GIT_TERMINAL_PROMPT=0`).

## Gotchas

- Name the remote (`origin`), not a URL typed from memory: the remote name applies the
  configured `insteadOf` and credential helper exactly as a fetch would.
- A 403, 404 or authentication failure is `blocked`, never "the branch does not exist".
- `--heads` still works on 2.55 without a warning `[observed]`; prefer `--branches` on
  Git ≥ 2.46.
- macOS has no `timeout(1)`; bound HTTP with `http.lowSpeedLimit`/`http.lowSpeedTime` and SSH
  with `ssh -o ConnectTimeout=…`.
- Output is `<oid> TAB <ref>`; the `awk` defaults split on the tab.
