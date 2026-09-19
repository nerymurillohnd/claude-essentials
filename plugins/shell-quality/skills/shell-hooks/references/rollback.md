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
recommended `.shellcheckrc` and the marked `[[shell]]` block in `.editorconfig`
(between the `shell-quality recommended shfmt style` markers), because the
editor and CI may rely on them; the user deletes them if they want. Then open `/hooks` to confirm.

Uninstalling the plugin does not remove an installed gate: the handler is a
standalone copy. Uninstall the gate first.

By hand: delete the five groups whose command contains
`shell-quality-gate.sh` from the settings file, delete the handler, or restore
the backup the installer printed (backups live in
`<git dir>/shell-quality-backups/` or `~/.claude/backups/shell-quality/`).

## Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| `shell-quality: shellcheck not found` / `shfmt not found` on every edit | The tool is not on the hook's `PATH` or in the usual locations | Install it (`brew install shellcheck shfmt`, a release binary), or set `SHELLCHECK_BIN` / `SHFMT_BIN` |
| `jq is required` | jq missing | Install jq (`brew install jq`, `apt install jq`, `winget install jqlang.jq`) |
| `shellcheck failed … (exit 3/4)` | An invalid rc file or `SHELLCHECK_OPTS` | Fix the rc file; unset `SHELLCHECK_OPTS` |
| Nothing happens after edits | Groups not loaded, the handler path is wrong, or `disableAllHooks` is set | `/hooks`; `manage.sh status` warns when the handler is missing |
| Scripts reformatted with tabs although the project uses spaces | `defaults` mode (`shfmt -i 0` ignores EditorConfig) | Reinstall with `own` or `recommended` |
| The Stop gate blocks on "configuration changed" | Claude changed `.shellcheckrc`, EditorConfig shfmt keys, or the gate's settings during the turn | Revert the change; configuration changes are made by the user between turns, which the gate accepts |
| The user changed configuration mid-turn and the gate blocks | The gate cannot tell who changed it during a turn | Let the turn end (the Stop gate releases after the max-blocks limit with a warning); the next prompt accepts the new configuration |
| An edit that keeps an existing directive is denied | The new text has more directives than the text it replaces | Include the existing directive in the replaced text, or leave it untouched |
| A Bash command is denied though it only reads | It contains a write construct and a protected file name | Split the read into its own command |
