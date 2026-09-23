# git maintenance

Official: https://git-scm.com/docs/git-maintenance · Areas: G11, G17 · Floor: 2.29
(`start` and `register` present by 2.31, `geometric` strategy 2.52, default for manual
runs 2.54, `is-needed` 2.53)

## Purpose in an audit

Audit how the repository is maintained: whether it is registered for background
maintenance (a **global** config entry), which strategy and tasks apply, whether the OS
scheduler entry exists, and whether scheduled `prefetch` writes `refs/prefetch/*`.

## Safety class

| Form | Class | Why |
| --- | --- | --- |
| `is-needed [--auto] [--task=…]` | read | exit 0 = maintenance needed, 1 = not (2.53) |
| `run [--task=<t>] [--auto] [--schedule=…]` | mutates, executes-config | runs gc, repack, prefetch (network), reflog-expire, worktree-prune … |
| `register` | mutates | adds to global `maintenance.repo`, sets `maintenance.strategy=incremental` if unset, sets `maintenance.auto=false` in the repository |
| `unregister [--force]` | mutates | removes from `maintenance.repo` only; the scheduler keeps running |
| `start [--scheduler=…]` | mutates | `register` + installs launchd / cron / systemd / schtasks entries |
| `stop` | mutates | removes the scheduler entries; keeps the registration |

## Options that matter

- Tasks `[doc]`: `commit-graph`, `prefetch` (fetches into `refs/prefetch/`, never updates
  tags or tracking refs), `gc`, `loose-objects` (deletes loose objects already packed, then
  packs a batch), `incremental-repack` (MIDX `expire` then `repack`), `pack-refs`,
  `reflog-expire`, `rerere-gc`, `worktree-prune`.
- Strategies `[doc]`: `none` (default for scheduled maintenance), `gc`, `geometric`
  (default for manual maintenance since 2.54; expires reflogs, prunes missing worktrees,
  may write a cruft pack), `incremental` (prefetch and commit-graph hourly,
  loose-objects and incremental-repack daily, pack-refs weekly, never gc).
- `maintenance.<task>.enabled`, `maintenance.<task>.schedule`, `maintenance.auto`,
  `maintenance.autoDetach` (falls back to `gc.autoDetach`).
- `remote.<n>.skipFetchAll` excludes a remote from `prefetch`.

## Verified recipes

```sh
git --no-pager config --global --get-all maintenance.repo
git --no-pager config --show-scope --show-origin --get-regexp '^maintenance\.'
ls ~/Library/LaunchAgents/org.git-scm.git* 2>/dev/null
crontab -l 2>/dev/null | grep -c 'for-each-repo'
systemctl --user list-timers 2>/dev/null | grep -c git-maintenance
git maintenance is-needed --auto; echo "exit=$?"
```

`[observed]` on the maintainer's macOS machine: no `maintenance.repo` entries, no
`org.git-scm.git*` agents, no cron line; `is-needed --auto` exited 0 on the fixture.

## Footprint it leaves when interrupted or misused

Global `maintenance.repo` entries for deleted repositories; `maintenance.auto=false` left
after `unregister` (automatic maintenance then never runs); `refs/prefetch/*`; scheduler
files (`~/Library/LaunchAgents/org.git-scm.git.{hourly,daily,weekly}.plist`, crontab lines,
`~/.config/systemd/user/git-maintenance@.*`); `gc.log` from failed runs.

## Gotchas

- Scheduled runs use `git for-each-repo --config=maintenance.repo`: a stale path fails
  every hour, silently.
- `gc` and `loose-objects` together fight each other `[doc]`; flag both enabled.
- Scheduled `prefetch` contacts every remote hourly with the stored credentials.
- The page on git-scm.com tracks the newest release; check `git --version` before quoting a
  default strategy.
