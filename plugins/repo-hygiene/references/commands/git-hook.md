# git hook

Official: https://git-scm.com/docs/git-hook · Areas: G12 · Floor: `run` 2.36; config-defined
hooks (`hook.<name>.command`) 2.54 `[doc]` RelNotes 2.54.0; `list` present in 2.55 `[observed]`

## Purpose in an audit

List which programs Git would run for each hook event, from the hooks directory
(`core.hooksPath` or `.git/hooks`) and from config (`hook.<name>.command`), with their scope.

## Safety class

| Form | Class | Why |
| --- | --- | --- |
| `git hook list [--show-scope] [-z] <event>` | read | Prints hook names; runs nothing |
| `git hook run <event>` | executes-config | Runs every configured hook for the event |
| `git hook run --ignore-missing …` | executes-config | Same, silent when none |

## Options that matter

- `list <event>`: prints one line per hook; exits 1 with `warning: no hooks found for event
  '<event>'` when none `[observed]`.
- `--show-scope`: prefixes config-defined hooks with `local`/`global`/`system`; hooks from
  the hooks directory print as `hook from hookdir` `[observed]`.
- `--allow-unknown-hook-name`: needed for wrapper-defined events.
- Config `[doc]`: `hook.<name>.command` (last one wins), `hook.<name>.event` (multi-valued;
  an empty value resets), `hook.<name>.enabled`, `hook.<name>.parallel`,
  `hook.<event>.enabled` (false disables every hook for the event), `hook.jobs`,
  `hook.<event>.jobs`. A friendly name equal to a known event name is a fatal error.
- Order `[doc]`: config hooks in config-parse order, the hooks-directory hook last.

## Verified recipes

```sh
git rev-parse --git-path hooks
git hook list --show-scope pre-commit
bash -c 'for e in pre-commit prepare-commit-msg commit-msg post-commit pre-merge-commit \
  pre-rebase post-checkout post-merge pre-push post-rewrite reference-transaction \
  pre-auto-gc post-index-change sendemail-validate pre-applypatch post-applypatch \
  applypatch-msg push-to-checkout fsmonitor-watchman; do
  out=$(git hook list --show-scope "$e" 2>/dev/null) && printf "%s: %s\n" "$e" "$out"; done; true'
```

`[observed]`: with `core.hooksPath=.hooks-alt`, `--git-path hooks` printed `.hooks-alt`;
`list pre-commit` printed `hook from hookdir`; `list post-checkout` found nothing although
`.git/hooks/post-checkout` existed (the hooks path replaces `.git/hooks`); a hook defined
with `hook.probe.command` and `hook.probe.event=pre-push` printed `pre-push: local<TAB>probe`.

## Footprint it leaves when interrupted or misused

`list` leaves nothing. `run` does whatever the hooks do (edits, network, commits).

## Gotchas

- `list` does not show the hook's content or path for config hooks; read the value with
  `git config --show-origin --get hook.<name>.command` (redacted) in `deep`.
- Server-side events (`pre-receive`, `update`, `post-receive`, `proc-receive`) matter only
  for repositories that receive pushes.
- Never run `git hook run` during an audit (`audit-contract.md` section 2).
