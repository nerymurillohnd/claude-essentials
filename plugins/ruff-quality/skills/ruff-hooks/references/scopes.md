# Scopes

| Scope | Settings file | Handler copy | Who is gated | Committed |
| --- | --- | --- | --- | --- |
| `project` | `<repo>/.claude/settings.json` | `<repo>/.claude/hooks/ruff-quality-gate.sh` | Everyone who runs Claude Code in this repository, after they pull | Yes: commit the settings, the handler, and a new `ruff.toml` together |
| `local` | `<repo>/.claude/settings.local.json` | `<repo>/.claude/hooks/ruff-quality-gate.sh` | This user, this repository | No: the handler, `settings.local.json`, and a written `ruff.toml` are added to `.git/info/exclude` unless already ignored or tracked |
| `user` | `~/.claude/settings.json` | `~/.claude/hooks/ruff-quality-gate.sh` | This user, every project on this machine | No |

With `CLAUDE_CONFIG_DIR` set, user scope uses `$CLAUDE_CONFIG_DIR/settings.json`
and `$CLAUDE_CONFIG_DIR/hooks/`, and the hook command references
`$CLAUDE_CONFIG_DIR`.

The gate lives in **one scope at a time**: hooks from every scope run in
parallel, and two copies would fix and format the same file simultaneously.
`preflight` refuses a second scope.

## Recommending a scope

- **project** — the team wants every Claude Code session in the repository to
  meet the same bar. Teammates need bash, jq, and ruff; a committed hook whose
  tools are missing fails closed (exit 2 with the reason).
- **local** — one person wants the gate in a shared repository without changing
  what the team commits.
- **user** — one person wants the gate in every Python project. Cloud sessions
  do not read `~/.claude/settings.json`; only project scope reaches them.

## The groups the script merges

For project and local scope, `P` is
`bash "$CLAUDE_PROJECT_DIR/.claude/hooks/ruff-quality-gate.sh"`; for user
scope it is `bash "$HOME/.claude/hooks/ruff-quality-gate.sh"`. `A` is
`--config-mode <mode> --max-blocks <n>` plus `--config "<path>"` when pinned.

```json
{
  "hooks": {
    "UserPromptSubmit": [
      { "hooks": [{ "type": "command", "command": "P baseline A", "timeout": 30 }] }
    ],
    "PreToolUse": [
      { "matcher": "Write|Edit|NotebookEdit|Bash", "hooks": [{ "type": "command", "command": "P guard A", "timeout": 30 }] }
    ],
    "PostToolUse": [
      { "matcher": "Write|Edit|NotebookEdit", "hooks": [{ "type": "command", "command": "P post A", "timeout": 60, "statusMessage": "ruff-quality: fixing, formatting, and linting the edited Python file" }] },
      { "matcher": "Bash", "hooks": [{ "type": "command", "command": "P post A", "timeout": 60 }] }
    ],
    "Stop": [
      { "hooks": [{ "type": "command", "command": "P stop A", "timeout": 120, "statusMessage": "ruff-quality: Stop gate re-checking edited Python files" }] }
    ]
  }
}
```

Why these choices:

- `bash "<path>"` runs Bash explicitly, so the handler never depends on its
  exec bit or on `/bin/sh` being Bash.
- `$CLAUDE_PROJECT_DIR` keeps committed files free of machine-specific paths.
- The `Bash` post group has no status message, so ordinary shell commands do
  not flash a spinner; the handler exits at once when no Python file changed.
- Exact-match matchers (`Write|Edit|NotebookEdit`) never match other tools.

## Manual installation (only if the user insists)

Prefer the script: it backs up, merges idempotently, and verifies. If the user
wants to do it by hand, give them these steps to run themselves:

1. Back up the settings file.
2. Copy `assets/ruff-quality-gate.sh` byte for byte to the handler path
   (`cp`, then `cmp`).
3. For `recommended`, copy `assets/ruff.toml` to the path in
   [config-modes.md](config-modes.md), only if no configuration exists there.
4. Merge the groups above into the settings file without reordering other
   entries.
5. Run `bash "<skill dir>/scripts/test-gate.sh" <installed handler>`; it must
   end with `PASS`.
6. Open `/hooks` to confirm the groups are listed.
