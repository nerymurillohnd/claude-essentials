---
name: run-marketplace
description: Runs and drives a claude-essentials plugin the way a user would - starts a headless Claude Code session with only that plugin loaded (from the working tree, or installed from HEAD in a throwaway configuration) and checks what the plugin does. Use when asked to run, try, smoke-test or demo a plugin, to check that a plugin change works for users before a pull request, or to test the released copy of a plugin.
argument-hint: "<plugin> [--prompt TEXT] [--source checkout|head] [--expect REGEX]"
---

# Run the marketplace

The marketplace has no app to launch: its "running app" is a plugin inside a user's Claude Code session. Drive it with `scripts/drive_plugin.py`, which sends a prompt to a real headless session with only that plugin loaded and checks the reply. Paths are relative to the repository root.

Every run is a real model call billed to the maintainer's plan (about \$0.01 with the default `haiku`, about \$0.14 with the session's default model); `--budget` caps it at \$0.50.

## Run (agent path)

Smoke-test a plugin from the working tree (uncommitted changes included). The default prompt is the plugin's first skill as a slash command:

```bash
python3 scripts/drive_plugin.py hello-example --expect 'hello-example.*installed'
```

Exit 0 means the plugin loaded alone, the session ended without error, every `--expect` regex matched the reply and the real configuration is unchanged. The output shows the source, prompt, loaded plugins, reply and cost; each problem is a `✘` line and exit 1.

Test the copy a user receives (HEAD cloned bare, installed through a `git-subdir` marketplace in a throwaway config); commit first:

```bash
python3 scripts/drive_plugin.py hello-example --source head --prompt "/hello-example:hello Ada" --expect 'Ada'
```

| Option                | Use                                                                                  |
| --------------------- | ------------------------------------------------------------------------------------ |
| `--prompt TEXT`       | Any request a user would type; required for a plugin without skills                  |
| `--expect REGEX`      | Repeatable, case-insensitive; one per behaviour the change must show                 |
| `--source head`       | Before tagging a release, to drive the exact files users install                     |
| `--model`, `--budget` | Default `haiku` and `0.50`; use `--model sonnet` when the skill needs more reasoning |

For a change, write expectations for what the change adds, not only that the plugin answers.

## Install only (no model call)

Installing, listing and loading every plugin in place, from a cache copy and per session, without driving any:

```bash
python3 scripts/check.py test-install
```

## Test

```bash
python3 scripts/check.py
```

## Gotchas

- **An isolated `CLAUDE_CONFIG_DIR` has no login.** Credentials belong to the config directory, so a session there answers `Not logged in · Please run /login`. The driver isolates the install but runs the session with the real login under `--restricted`, which loads neither user nor project settings (none of the maintainer's plugins, hooks or permissions).
- **`--restricted` still loads the account's claude.ai connectors and the user CLAUDE.md.** `--strict-mcp-config` removes the connectors (the driver fails if any MCP server loads); the global CLAUDE.md still reaches the model, so a reply may use the maintainer's name or language. Expectations must not depend on either.
- **The macOS login is found through `USER`.** A stripped environment (`env -i`, cron, launchd) without `USER` gets `Not logged in` even with the real config; `LOGNAME` alone does not help. Run from a normal shell or export `USER`.
- **`-p` waits 3 seconds for stdin and warns** when nothing is piped; the driver passes an empty stdin.
- **No transcript is written** (`--no-session-persistence`): the session cannot be resumed or inspected afterwards; the reply printed by the driver is the record.
- **`timeout` does not exist on macOS.** Bound a run with `--budget`, not with a shell timeout.
- **Built-in plugins (`cc-plugin-*@builtin`) always load** next to the target; the driver ignores them and fails on any other plugin.
- **Temporary files use the prefix `claude-essentials-drive-`**, listed in `TEMP_PREFIXES` of `scripts/check.py`; `python3 scripts/check.py clean` removes orphans.

## Troubleshooting

- **`✘ plugins/<name> is not a plugin`**: the name is not a directory with `.claude-plugin/plugin.json` under `plugins/`.
- **`✘ <name> has no skills; pass --prompt`**: the plugin ships only agents, hooks or MCP servers; pass the request that should exercise them.
- **`✘ head: plugin install <name>@claude-essentials failed`**: HEAD does not contain the plugin yet; commit, then rerun.
- **`✘ USER is unset, so Claude Code cannot find the login; export USER`**: see the `USER` gotcha.
- **`✘ reply does not match '<regex>'`**: the plugin answered but not as expected; read the printed reply before changing the plugin or the expectation.
