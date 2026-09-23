# git daemon

Official: https://git-scm.com/docs/git-daemon · Areas: G18 · Floor: any

## Purpose in an audit

Explain what `git-daemon-export-ok` means and what a daemon would serve. The audit never
starts a daemon.

## Safety class

| Form | Class | Why |
| --- | --- | --- |
| `git daemon …` | network | Starts a server on port 9418 that serves repositories |
| checking `git-daemon-export-ok` and `daemon.*` config | read | File and config presence |

## Options that matter

- A directory is served only when it contains `git-daemon-export-ok`, unless the daemon runs
  with `--export-all` `[doc]`.
- `--base-path`, `--strict-paths`, `--user-path`, whitelist directories decide which paths
  are reachable `[doc]`.
- Services `[doc]`: `upload-pack` (fetch) on by default, disable with
  `daemon.uploadpack=false`; `upload-archive` off, enable with `daemon.uploadarch=true`;
  `receive-pack` (anonymous push) off, enable with `daemon.receivepack=true`.
- `--informative-errors` reveals whether a path exists.

## Verified recipes

```sh
ls -l "$(git rev-parse --git-common-dir)/git-daemon-export-ok" 2>/dev/null
git --no-pager config --show-scope --show-origin --get-regexp '^daemon\.'
```

`[observed]`: the fixture's empty `git-daemon-export-ok` was listed; no `daemon.*` keys
(exit 1).

## Footprint it leaves when interrupted or misused

`git-daemon-export-ok` itself (created by hand, by `git instaweb` setups or hosting scripts);
`daemon.receivepack=true` in a repository config enables anonymous pushes when served.

## Gotchas

- The marker does nothing unless a daemon serves the parent path; report it as exposure
  risk, with the evidence that a daemon runs (or that none was found), not as a leak.
- `git daemon` does no authentication: anything served is public to the network it listens on.
