---
paths:
  - "scripts/drive_plugin.py"
  - ".claude/skills/run-marketplace/**"
---

# Driving a plugin

- `scripts/drive_plugin.py <plugin> [--prompt TEXT] [--source checkout|head] [--expect REGEX] [--model MODEL] [--budget USD] [--tools LIST] [--permission-mode MODE]` uses a plugin the way a user does.
- It sends a prompt (by default the plugin's first skill as a slash command) to a headless `claude -p` session with only that plugin loaded.
- It fails unless the plugin loaded alone, the session ended without error, every `--expect` regex matches the reply and the real configuration is unchanged.
- `--source head` drives the copy a user receives, installed from a bare clone of HEAD in a throwaway configuration.
- `--budget` caps the spend of the session (default $0.50).
- `--tools` (default `default,Bash,WebFetch`) restores Bash and WebFetch, which `--restricted` drops.
- The session runs with the maintainer's own login, because an isolated `CLAUDE_CONFIG_DIR` has no credentials.
- It runs under `--restricted` (no user or project settings), `--strict-mcp-config` (no claude.ai connectors) and `--no-session-persistence` (no transcript).
- It starts in an empty temporary directory, so neither the project `CLAUDE.md` nor the git snapshot reaches the model.
- It is a fast smoke test on the maintainer's login; `claude plugin eval plugins/<name> --no-publish` is the clean-room check.
- Each run is a real model call (about $0.01 with the default `haiku`), so it is not a CI gate; run it before a pull request that changes a plugin's behavior.
- The project skill `run-marketplace` documents it.
- `--restricted` drops Bash, the other code-running tools and WebFetch; the `default` preset of `--tools` does not bring them back, naming them does (`--tools default,Bash,WebFetch`; observed, not documented). It also ignores user, project and local settings files and refuses `bypassPermissions` (changelog 2.1.248).
- Credentials are keyed to `CLAUDE_CONFIG_DIR`, so a session with an isolated config is not logged in; `claude plugin eval` runs each case with a temporary home and configuration.
