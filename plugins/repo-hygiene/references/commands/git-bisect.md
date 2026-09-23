# git bisect

Official: https://git-scm.com/docs/git-bisect · Areas: G2, G15, G17, G21 · Floor: any
(old/new and custom terms 2.7, `--first-parent` 2.29 `[doc]` RelNotes)

## Purpose in an audit

Find the commit that changed a behavior by binary search, and (with `--no-checkout`)
localize damage in the object graph. Detect and end sessions someone left running.

## Safety class

| Form | Class | Why |
| --- | --- | --- |
| `git bisect log`, `git bisect terms` | read | Print the session; `log` exits 1 with `error: We are not bisecting.` when idle `[observed]` |
| `start`, `good`/`bad`/`old`/`new`/`<term>`, `skip`, `replay` | mutates | Check out commits, write `refs/bisect/*` and `BISECT_*` |
| `start --no-checkout` | mutates | Moves `BISECT_HEAD`, writes refs and files; tree untouched |
| `run <cmd>` | mutates + executes-config | Runs a program at each step |
| `visualize` / `view` | executes-config | Starts `gitk` or `git log` with a pager |
| `reset [<commit>]` | mutates | Checks out the original branch (or `<commit>`) and removes the state |

## Options that matter

- `start [--term-(bad|new)=<t> --term-(good|old)=<t>] [--no-checkout] [--first-parent]
  [<new> [<old>…]] [--] [<pathspec>…]` `[doc]`.
- `run` exit codes `[doc]` `[observed]`: 0 old/good; 1-127 except 125 new/bad; 125 skip;
  126/127 on the first run trigger a re-run on a known-good commit and abort if repeated
  (`builtin/bisect.c`); 128-255 abort (`exit(-1)` is 255).
- `skip <rev>…` and ranges `A..B`.
- `replay <logfile>` re-applies a saved `bisect log`.

## Verified recipes

```sh
git bisect start --term-old=fast --term-new=slow main good-point --
git bisect run /absolute/outside/path/probe.sh
git bisect log > <evidence>/bisect-log.txt
git bisect reset
```

`[observed]`: found the planted first "slow" commit in 3 steps; `bisect run` exited 1 on a
script exit of 255, 128 on 128, 2 when every commit was skipped (125), and 1 with
`bogus exit code 127 for 'good' revision` on 127; `--no-checkout` kept `HEAD` on `main`
and created `BISECT_HEAD`; `skip main~9..main~6` skipped 3 commits; `replay` reproduced the
result; `--first-parent` ran on a merge history. The full procedure and the damaged-object
probe are in `areas/tracing.md` checks 12-20.

## Footprint it leaves when interrupted or misused

`[observed]` during a session: `refs/bisect/<term>` and `refs/bisect/<old-term>-<sha>`,
`BISECT_ANCESTORS_OK`, `BISECT_EXPECTED_REV`, `BISECT_LOG`, `BISECT_NAMES`, `BISECT_RUN`,
`BISECT_START`, `BISECT_TERMS`, `BISECT_HEAD` (with `--no-checkout`), and a detached `HEAD`.
`git bisect reset` removed all of them. Bisect refs are per worktree (since 2.7 `[doc]`).

## Gotchas

- `git bisect reset -q` is invalid: `error: '-q' is not a valid commit`, and the session
  stays active `[observed]`.
- Relative revisions (`HEAD~9`) during a session resolve from the checked-out bisect commit;
  use the branch name `[observed]`.
- A script inside the repository changes with each checkout; keep it outside and absolute.
- `bisect run` in the official damaged-repository example writes `tmp.$$` in the current
  directory; use `mktemp` instead (`areas/tracing.md` check 20).
- Starting a bisection is always an approved item (`audit-contract.md` section 1).
