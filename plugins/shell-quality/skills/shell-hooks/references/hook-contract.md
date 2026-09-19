# The gate's hook contract

Verified on 2026-09-19 against Claude Code 2.1.278, the
[hooks reference](https://code.claude.com/docs/en/hooks), and live sessions
with the plugin family's gate installed. Live documentation wins over this
page; re-check it and the [changelog](https://code.claude.com/docs/en/changelog)
if a user reports different behavior.

## Claude Code behavior the gate relies on

| Fact | Consequence for the gate |
| --- | --- |
| Exit `2` is the only exit code that blocks by itself; `1` and other codes are non-blocking errors (the action proceeds, stderr goes to the debug log) | Every failure path exits `2`, never `1`. A hook that just runs `shellcheck` (exit 1 on findings) never reaches Claude |
| Hooks receive their input as JSON on stdin (`tool_input.file_path`, `tool_response.filePath`); there is no file-path environment variable | The handler parses stdin with jq |
| `PreToolUse` exit `2`, or JSON `permissionDecision: "deny"`, blocks the tool call, even in `bypassPermissions` mode | The guard emits both |
| `PostToolUse` cannot undo the tool call; on exit `2` Claude sees stderr next to the tool result | Findings go to stderr with an instruction to fix them now |
| `systemMessage` in JSON stdout is shown to the user | Every result, clean or not, tells the user in one line (`shell-quality ✓ …` / `✗ …`) |
| `Stop` exit `2` prevents Claude from stopping and delivers stderr as the reason | The Stop gate keeps Claude working until the edited scripts are clean |
| Claude Code overrides a Stop hook after 8 consecutive blocks; `stop_hook_active` is `true` on those continuations | `--max-blocks` (1–7, default 5) ends the loop first, with a visible warning |
| All matching hooks run in parallel | The gate refuses to live in two scopes at once |
| A timed-out command hook renders no decision | Timeouts: 30 s (baseline, guard), 60 s (post), 120 s (Stop) |
| `PostToolUse` on `Bash` receives `tool_response.bashEditDiff` (Claude Code ≥ 2.1.269, public beta): `{files: [{filePath, hunks, created}], moreFiles, changedFiles}` | Scripts Claude writes through Bash are formatted and checked too, when Claude Code records the diff (auto and `bypassPermissions` mode, or `bashEditDiffEnabled: true` in user settings) |
| Cowork does not load settings-based hooks | The skill refuses to install there |

## Per event

### `UserPromptSubmit` → `baseline`

Records a fingerprint of every file that decides what the gate enforces: each
`.shellcheckrc`/`shellcheckrc` in the repository, `~/.shellcheckrc`, the XDG
rc, a pinned `--rcfile`, the shfmt-relevant lines (section headers and shfmt
keys) of each `.editorconfig`, and this gate's groups plus `disableAllHooks`
in the three settings files. It recounts suppression directives in scripts
already touched this session. Anything the user changed between turns becomes
the accepted state.

### `PreToolUse` → `guard`

| Input | Denied when |
| --- | --- |
| `Write`/`Edit` on `.shellcheckrc`, `shellcheckrc` (any directory), the XDG rc, the pinned rc, or `shell-quality-gate.sh` | Always |
| … on `.editorconfig` | A section header or an shfmt key (`indent_style`, `indent_size`, `shell_variant`, `binary_next_line`, `switch_case_indent`, `space_redirects`, `keep_padding`, `function_next_line`, `simplify`, `minify`, `ignore`, `root`) would change; other keys are allowed |
| … on `settings.json` / `settings.local.json` | This gate's groups or `disableAllHooks` would change |
| … on a shell script (by extension, shebang on disk, or the shebang of new content) | The new text has more suppression directives than the text it replaces |
| `Bash` | Any mention of `disableAllHooks`; running this skill's `manage.sh install`/`uninstall`; a write construct (redirection, `sed -i`, `perl -i`, `tee`, `cp`, `mv`, `rm`, `ln`, heredoc, `python -c`) together with a suppression directive, or with an rc file, `.editorconfig`, the handler, or a settings file |

Suppression directives counted: `# shellcheck disable=…` (including
`disable=all`) and `# shellcheck source=/dev/null`, case-insensitive. Other
directives (`shell=`, `source=path`, `source-path=`, `enable=`) are allowed.

### `PostToolUse` → `post`

For each script in `tool_input.file_path`, `tool_response.filePath`, or
`bashEditDiff` (`.sh`, `.bash`, `.bats`, or a `sh`/`bash`/`dash`/`ksh` shebang;
zsh is skipped because ShellCheck does not support it):

1. `shfmt --apply-ignore -w` (plus `-i 0` in `defaults`, or the recommended
   flags with `--style-fallback` when no `.editorconfig` governs the script).
2. `shellcheck -f gcc` (plus `--norc` or `--rcfile FILE` by mode).
3. A shfmt parse error is reported with ShellCheck's parse findings.
4. Suppression count against the session baseline (for scripts first seen
   after a Bash write, the committed version is the baseline).
5. Configuration fingerprint against the turn's baseline.

Tools are resolved from `SHELLCHECK_BIN`/`SHFMT_BIN`, then `PATH`, then
`~/.local/bin`, `/opt/homebrew/bin`, `/usr/local/bin`, `/usr/bin`.

### `Stop` → `stop`

Read-only: `shellcheck` and `shfmt -d` on every script edited this session that
still exists, plus the suppression and configuration checks. Counts
consecutive blocks per session; a new turn starts at zero.

## State

Per session, in `${TMPDIR:-/tmp}/shell-quality-gate-<uid>/` (mode `0700`,
owner-checked). Files older than two days are removed automatically. Nothing
is written in the project.

## What the gate cannot see

- Files changed by a process outside Claude's tools, or by Bash when Claude
  Code does not record `bashEditDiff`.
- A directive or configuration change hidden from the Bash heuristics (for
  example a script Claude wrote earlier and then ran). The post and Stop checks
  still catch directive growth in scripts the gate knows, and any
  configuration drift.
- Bash version compatibility: ShellCheck does not check it; a script that
  passes can still fail on macOS `/bin/bash` 3.2 (see the shell-lint skill).
