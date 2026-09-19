# Rollback and troubleshooting

## Rollback

The fastest path is the script, which backs up first and removes only this
policy: run `uninstall --scope <project|local|user>` with the same `manage.sh`
path `SKILL.md` uses. A path printed by an earlier install may point at an
older plugin version in the cache; prefer the current skill's path.

By hand, for the chosen scope:

1. In the settings file (`.claude/settings.json`, `.claude/settings.local.json`,
   or `~/.claude/settings.json`), remove the `hooks.PreToolUse` group whose
   command is `bash "$CLAUDE_PROJECT_DIR/.claude/hooks/block-no-verify.sh"`
   (project/local) or `bash "$HOME/.claude/hooks/block-no-verify.sh"` (user).
2. Delete the handler file, unless the other project/local scope still uses it.
3. Or restore the settings backup the install printed (this discards any
   settings edits made after the install), from
   `<git common dir>/block-no-verify-backups/` or
   `~/.claude/backups/block-no-verify/`.
4. Local scope: delete the lines under `# block-no-verify (local scope)` in
   `.git/info/exclude`.
5. Open `/hooks` to confirm the group is gone.

Uninstalling the plugin does not remove an installed policy; the policy is a
standalone copy by design. Remove it first if that is the intent.

## Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| `/hooks` does not list the group | File watcher missed the change, or `disableAllHooks`/managed policy | Restart the session; run `assess` and read its warnings |
| Every Bash call shows a hook error, nothing is blocked | The group points at a missing handler (teammate pulled settings without the handler, or it was deleted) | Commit the handler with the settings, or reinstall/uninstall; `status` flags this |
| A deny names `jq is not installed` | `jq` was removed after install | Install `jq`; the handler blocks only `git` commands meanwhile |
| A deny names "a command built from variables" or "nested too deeply" | Conservative check on a construct the parser cannot resolve | Run the `git` command directly with literal arguments |
| A legitimate command is denied | Report it with the exact command | Open an issue on the marketplace repository; do not weaken the handler locally |
| `preflight` fails on Windows | No Git Bash, so hooks run in PowerShell | Install Git for Windows and `jq`, or do not use this policy there |
| The policy seems inactive in Cowork | Cowork does not run settings hooks | Expected; use Claude Code |
