# Rollback and troubleshooting

## Remove the gate

While the gate is installed, it denies Claude running the installer or
uninstaller: changing the gate is the user's decision. The user runs:

```text
! bash "<skill dir>/scripts/manage.sh" uninstall --scope <project|local|user>
```

`uninstall` backs up the settings file, removes only this gate's groups,
removes emptied `hooks` keys (and a project or local settings file left as
`{}`), deletes the handler unless the other project/local scope still uses it,
and removes this gate's lines from `.git/info/exclude`. It **keeps** a
recommended `ruff.toml` it wrote, because the editor and CI may rely on it; the
user deletes it if they want. Then open `/hooks` to confirm.

Uninstalling the plugin does not remove an installed gate: the handler is a
standalone copy. Uninstall the gate first.

By hand: delete the five groups whose command contains
`ruff-quality-gate.sh` from the settings file, delete the handler, or restore
the backup the installer printed (backups live in
`<git dir>/ruff-quality-backups/` or `~/.claude/backups/ruff-quality/`).

## Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| `ruff-quality: ruff not found` on every edit | No Ruff on the hook's `PATH` or in the project's venv | Install Ruff (`uv tool install ruff`), add it to the project's dev dependencies, or set `RUFF_BIN` |
| `jq is required` | jq missing | Install jq (`brew install jq`, `apt install jq`, `winget install jqlang.jq`) |
| `ruff check --fix failed … (exit 2)` | Invalid Ruff configuration, or `required-version` does not match | Run `ruff check --show-settings <file>` and fix the configuration or the Ruff version |
| Nothing happens after edits | Groups not loaded, the handler path is wrong, or `disableAllHooks` is set | `/hooks`; `manage.sh status` warns when the handler is missing |
| The Stop gate blocks on "configuration changed" | Claude changed Ruff configuration or the gate's settings during the turn | Revert the change; configuration changes are made by the user between turns, which the gate accepts |
| The user changed configuration mid-turn and the gate blocks | The gate cannot tell who changed it during a turn | Let the turn end (the Stop gate releases after the max-blocks limit with a warning); the next prompt accepts the new configuration |
| A denied edit for a comment that is not a suppression (e.g. the word `noqa` inside a string written as `# noqa`) | The guard matches comment syntax textually | Rephrase the string; the user can add the text themselves |
| Edits to pre-existing files with suppressions are denied | The edit adds more suppressions than the text it replaces | Include the existing comment in the replaced text, or leave it untouched |
| A Bash command is denied though it only reads | It contains a write construct and a protected file name | Split the read into its own command |
