# Claude Code hook behavior this policy depends on

Verified 2026-09-18 against Claude Code 2.1.277, the
[hooks reference](https://code.claude.com/docs/en/hooks), the
[hooks guide](https://code.claude.com/docs/en/hooks-guide), and the
[changelog](https://code.claude.com/docs/en/changelog). If a user reports
behavior that contradicts this page, re-check those sources before acting;
live documentation wins.

## Where hooks come from

- Sources merge: user (`~/.claude/settings.json`), project
  (`.claude/settings.json`), local (`.claude/settings.local.json`), managed
  policy settings, enabled plugins' `hooks/hooks.json`, and skill/agent
  frontmatter. None replaces another.
- An identical handler definition in several settings files runs once. The
  same handler at different paths (for example project and user scope) runs
  once per copy.
- `disableAllHooks: true` turns off user, project, local, and plugin hooks.
  Managed `allowManagedHooksOnly: true` blocks every non-managed hook. Either
  one silences this policy, which is why preflight refuses.
- File edits to settings are normally picked up by a file watcher; if `/hooks`
  does not show a change after a few seconds, restart the session.
- Cloud sessions do not read `~/.claude/settings.json`; they use the
  repository's `.claude/settings.json` and managed settings. Only project scope
  protects cloud sessions.

## How a PreToolUse command hook runs

- Shell-form commands run with `sh -c` on macOS and Linux, Git Bash on
  Windows, or PowerShell when Git Bash is not installed.
- All matching hooks run in parallel. For `PreToolUse`, the most restrictive
  decision wins: `deny` > `defer` > `ask` > `allow`. Another hook's `allow`
  cannot override this policy's `deny`.
- `PreToolUse` runs before any permission-mode check. A `deny` blocks the tool
  even in `bypassPermissions` mode or with `--dangerously-skip-permissions`.
- Exit `0` with JSON on stdout: the decision in `hookSpecificOutput` applies.
- Exit `2`: blocks regardless of stdout; the reason comes from the JSON or stderr.
- Any other exit code (`1`, `127`, ...): a non-blocking error; the tool call
  proceeds. A missing interpreter or a deleted handler therefore fails open.
- A timed-out `PreToolUse` command hook does not block.
- A shell profile that prints text before the JSON makes stdout unparseable;
  exit `2` still blocks.

## Consequences for this handler

- It denies with JSON **and** exit `2`, so profile noise cannot turn a deny
  into an allow.
- The command invokes `bash` explicitly. Bash is present wherever Claude Code
  runs shell-form hooks except Windows without Git Bash, where the hook would
  fail open; that is why preflight refuses that setup. If `jq` disappears, the
  handler denies only payloads that mention `git`.
- It matches `Bash|PowerShell` without an `if` filter and filters inside,
  because `if` rules are best-effort for wrapped and chained commands.
- `status` warns when a group points at a missing handler, because that state
  blocks nothing.

## Claude Cowork

Cowork runs sessions in a Linux sandbox that loads plugin skills but does not
load settings-based hooks from the user's machine (open issue
[anthropics/claude-code#40495](https://github.com/anthropics/claude-code/issues/40495);
duplicate #63360 closed as not planned). `/hooks` does not exist there. The
script detects Cowork through the `CLAUDE_CODE_IS_COWORK` environment variable,
which is documented only in that issue, not in the official docs; re-verify it
if Cowork behavior changes. The skill refuses to install in Cowork and never claims protection there.
