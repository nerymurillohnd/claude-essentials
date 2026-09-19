# Scope guide

Hooks from every settings scope merge; they never replace each other. Pick
the narrowest scope that covers who must be protected.

| Scope | Settings file | Handler copy | Who is protected | Committed |
| --- | --- | --- | --- | --- |
| `project` | `<repo>/.claude/settings.json` | `<repo>/.claude/hooks/block-no-verify.sh` | Everyone who runs Claude Code in this repository, after they pull | Yes, both files |
| `local` | `<repo>/.claude/settings.local.json` | `<repo>/.claude/hooks/block-no-verify.sh` | This user, this repository | No: the script adds both paths to `.git/info/exclude` unless already ignored or tracked (the handler is not excluded when project scope already commits it) |
| `user` | `~/.claude/settings.json` | `~/.claude/hooks/block-no-verify.sh` | This user, every repository on this machine | No |

When `CLAUDE_CONFIG_DIR` is set, Claude Code reads user settings from there, so
user scope uses `$CLAUDE_CONFIG_DIR/settings.json` and
`$CLAUDE_CONFIG_DIR/hooks/block-no-verify.sh`, and the hook command references
`$CLAUDE_CONFIG_DIR` instead of `$HOME/.claude`.

## Recommending a scope

- **project**: the team relies on hooks or signing (husky, pre-commit,
  lefthook, required signed commits) and wants the same guard for everyone.
  The handler and settings must be committed together; a committed group
  whose handler is missing errors on every shell call and blocks nothing.
  Teammates need bash and jq (see the plugin README).
- **local**: one person wants the guard in a shared repository without
  changing what the team commits.
- **user**: one person wants the guard everywhere. It also covers
  repositories that have no `.claude/` directory. It does not apply to cloud
  sessions, which do not read `~/.claude/settings.json`.
- **none**: `assess` found no hooks and no required signing, and the user
  does not want user scope. Say so; installing would protect nothing.

Installing in two scopes is allowed and harmless. Project and local use the
same command, which Claude Code deduplicates to one run; project or local plus
user runs twice, with the same result. `assess` and `status` show where it
already exists.

## Environments

The handler is one Bash script for every supported environment. Only the
hook command's path variable differs by scope, never by operating system.

| Environment | Hook shell | Supported | Notes |
| --- | --- | --- | --- |
| macOS | `sh -c` | Yes | Stock `/bin/bash` is 3.2; the handler supports it. `jq` ships with macOS 15+ at `/usr/bin/jq`; older versions need `brew install jq` |
| Linux | `sh -c` | Yes | Install `jq` from the distribution (`apt install jq`, `dnf install jq`) |
| WSL | `sh -c` | Yes | Same as Linux, inside the WSL distribution |
| Windows with Git for Windows | Git Bash | Yes, not yet verified on a live machine | `jq` must be on the Git Bash `PATH` (`winget install jqlang.jq`) |
| Windows without Git Bash | PowerShell | No | `preflight` fails: a Bash handler cannot run |
| Claude Cowork | n/a | No | Settings hooks do not run in Cowork's sandbox |

## Settings snippets (what the script merges)

Project and local scope, any OS:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash|PowerShell",
        "hooks": [
          {
            "type": "command",
            "command": "bash \"$CLAUDE_PROJECT_DIR/.claude/hooks/block-no-verify.sh\"",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

User scope, any OS:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash|PowerShell",
        "hooks": [
          {
            "type": "command",
            "command": "bash \"$HOME/.claude/hooks/block-no-verify.sh\"",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

Why these choices:

- `bash "<path>"` runs Bash explicitly, so the handler never depends on its
  exec bit or on `/bin/sh` being Bash.
- `$CLAUDE_PROJECT_DIR` keeps committed files free of absolute paths from any
  machine; the double quotes survive spaces in the path.
- No `if` filter: a `Bash(git *)` filter would miss wrapped and chained
  commands. The handler filters internally and exits in well under 100 ms.
- `timeout: 10`: a timed-out `PreToolUse` hook does not block, so the budget is
  generous compared with the handler's real cost.

## Manual procedure (without the script)

Prefer the script: it backs up, merges idempotently, and verifies. If the user
insists on doing it without the script, give them these steps to run
themselves; do not perform them with file-edit tools.

1. Back up the target settings file.
2. Copy `assets/block-no-verify.sh` byte-for-byte to the scope's handler path
   (`cp`, then `cmp` to confirm). Do not retype it.
3. Append the group above to `hooks.PreToolUse` (create the keys if absent).
   Do not reorder or rewrite other entries.
4. Run `bash "<skill dir>/scripts/test-handler.sh" <installed handler path>`
   (the same skill directory `SKILL.md` uses for `manage.sh`); it must end with `PASS`.
5. Open `/hooks` to confirm the group is listed.
