# The gate's hook contract

Verified on 2026-09-19 against Claude Code 2.1.278, the
[hooks reference](https://code.claude.com/docs/en/hooks), and live sessions
(`claude -p`) with the gate installed. Live documentation wins over this page;
re-check it and the [changelog](https://code.claude.com/docs/en/changelog) if a
user reports different behavior.

## Claude Code behavior the gate relies on

| Fact | Consequence for the gate |
| --- | --- |
| Exit `2` is the only exit code that blocks by itself; `1` and other codes are non-blocking errors (the action proceeds) | Every failure path exits `2`, never `1` |
| `PreToolUse` exit `2`, or JSON `permissionDecision: "deny"`, blocks the tool call, even in `bypassPermissions` mode | The guard emits both, so shell-profile noise cannot turn a deny into an allow |
| `PostToolUse` cannot undo the tool call; on exit `2` Claude sees stderr next to the tool result | Findings go to stderr with an instruction to fix them now |
| `systemMessage` in JSON stdout is shown to the user (in `-p` stream output as an informational event) | Every result, clean or not, tells the user in one line (`ruff-quality ✓ …` / `✗ …`) |
| With exit `2` Claude Code still reads the JSON fields | The `systemMessage` accompanies the blocking exit |
| `Stop` exit `2` prevents Claude from stopping and delivers stderr as the reason | The Stop gate keeps Claude working until the edited files are clean |
| Claude Code overrides a Stop hook after 8 consecutive blocks; `stop_hook_active` is `true` on those continuations | `--max-blocks` (1–7, default 5) ends the loop first, with a visible warning |
| All matching hooks run in parallel | The gate refuses to live in two scopes at once, so two copies never rewrite one file |
| A timed-out command hook renders no decision | Timeouts: 30 s (baseline, guard), 60 s (post), 120 s (Stop); measured runs take well under a second per file |
| `PostToolUse` on `Bash` receives `tool_response.bashEditDiff` (Claude Code ≥ 2.1.269, public beta) listing files a Bash command changed in a Git repository: `{files: [{filePath, hunks, created}], moreFiles, changedFiles}` | Files Claude writes through Bash are fixed, formatted, and checked too, when Claude Code records the diff |
| `bashEditDiff` is recorded in auto and `bypassPermissions` mode, or in every mode when the user sets `bashEditDiffEnabled: true` in user settings | In the default permission mode, Bash writes are only caught by the guard's heuristics and the Stop gate's suppression and configuration checks on files it already knows |
| Cowork does not load settings-based hooks | The skill refuses to install there |

## Per event

### `UserPromptSubmit` → `baseline`

Records a fingerprint of every file that decides what the gate enforces: each
`ruff.toml`, `.ruff.toml`, and the `[tool.ruff]` tables of each
`pyproject.toml` in the repository; the user-level Ruff configuration; a pinned
`--config`; and this gate's groups plus `disableAllHooks` in the three settings
files. It also recounts suppression comments in files already touched this
session. Anything the user changed between turns becomes the accepted state.
Always exits `0` unless the state directory is unusable.

### `PreToolUse` → `guard`

| Input | Denied when |
| --- | --- |
| `Write`, `Edit`, `NotebookEdit` on `ruff.toml`, `.ruff.toml`, anything under the user-level Ruff directory, the pinned config, or `ruff-quality-gate.sh` | Always |
| … on `pyproject.toml` | The `[tool.ruff*]` tables would change (other tables are allowed) |
| … on `settings.json` / `settings.local.json` | This gate's groups or `disableAllHooks` would change (other settings are allowed) |
| … on a `.py`, `.pyi`, `.ipynb` file | The new text has more suppression comments than the text it replaces |
| `Bash` | `--add-noqa` or `--add-ignore`; any mention of `disableAllHooks`; running this skill's `manage.sh install`/`uninstall`; a write construct (redirection, `sed -i`, `perl -i`, `tee`, `cp`, `mv`, `rm`, `ln`, heredoc, `python -c`) together with a suppression comment, or with a Ruff configuration file, `pyproject.toml`, the handler, or a settings file |

Suppression comments counted: `# noqa`, `# ruff: noqa`, `# ruff: ignore`,
`# ruff: disable`, `# ruff: file-ignore`, `# fmt: off`, `# fmt: skip`,
`# isort: skip`, `# isort: off` (case-insensitive).

### `PostToolUse` → `post`

For each `.py`, `.pyi`, or `.ipynb` path in `tool_input.file_path`,
`tool_input.notebook_path`, `tool_response.filePath`, or `bashEditDiff`:

1. `ruff check --fix --unfixable F401 --force-exclude --no-cache` — safe fixes
   only; an import added one edit before its first use is not deleted.
2. `ruff format --force-exclude --no-cache`.
3. `ruff check --force-exclude --no-cache --output-format concise` — findings,
   except `F401`, which the Stop gate checks once the change is complete.
4. Suppression count against the session baseline (for files first seen after
   a Bash write, the committed version is the baseline).
5. Configuration fingerprint against the turn's baseline.

Ruff is resolved per file: `RUFF_BIN`, then the nearest `.venv/bin/ruff` or
`venv/bin/ruff` above the file, then `PATH`, then `~/.local/bin`,
`/opt/homebrew/bin`, `/usr/local/bin`. A file excluded by the configuration is
skipped and reported as skipped.

### `Stop` → `stop`

Read-only: `ruff check` and `ruff format --check` on every Python file edited
this session that still exists, plus the suppression and configuration checks.
Counts consecutive blocks per session; a new turn starts at zero.

## State

Per session, in `${TMPDIR:-/tmp}/ruff-quality-gate-<uid>/` (mode `0700`,
owner-checked): `<session>.files`, `.supp`, `.config`, `.blocks`. Files older
than two days are removed automatically. Nothing is written in the project.

## What the gate cannot see

- Files changed by a process outside Claude's tools, or by Bash when Claude
  Code does not record `bashEditDiff`.
- A suppression or configuration change hidden from the Bash heuristics (for
  example a script file Claude wrote earlier and then ran). The post and Stop
  checks still catch suppression growth in files the gate knows, and any
  configuration drift.
- Semantics: Ruff passing is not proof the code is correct.
