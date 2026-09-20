---
name: shell-hooks
description: Make every shell script Claude edits pass shfmt and ShellCheck before Claude can move on, by installing the shell-quality gate through its own script only, never by writing the settings, the handler, .shellcheckrc or .editorconfig by hand. The gate is four hooks — PreToolUse denies edits that add shellcheck disable directives or change the rc, the shfmt keys of .editorconfig, or the gate itself; PostToolUse formats and checks each touched script; Stop reblocks until the session's scripts are clean, up to a configurable limit. Show the exact configuration of each of the three modes and install nothing until the user picks a scope and a mode. It lives in one scope at a time, fails closed without shellcheck, shfmt or jq, skips zsh, and looks only at scripts Claude touched. Once installed it denies Claude changing or removing it. For using the tools themselves, use the shell-lint skill.
when_to_use: When the user asks to add a ShellCheck hook, run shfmt and ShellCheck after every edit, stop Claude from adding disable directives, or install, check, update or remove the gate.
compatibility: Claude Code (CLI, Desktop, IDE) on macOS, Linux, WSL, or Windows with Git Bash. Needs bash >= 3.2, jq >= 1.6, git, shellcheck >= 0.10 (0.11 for the recommended profile), and shfmt >= 3.12. Not supported in Claude Cowork, where settings-based hooks do not run.
license: Apache-2.0
---

# Shell hooks

Install, inspect, and remove the **shell-quality gate**: Claude Code hooks that
make every shell script Claude creates or edits pass shfmt and ShellCheck
before Claude can move on or finish, without ever silencing a check. Installing
the plugin wires nothing; the gate exists only after the user asks, chooses a
scope and a configuration mode, and this workflow installs it.

Every state change goes through one deterministic script:

```bash
bash "${CLAUDE_SKILL_DIR}/scripts/manage.sh" <command> [options]
```

Commands: `assess`, `show-config --config-mode MODE [--config-path FILE]`,
`status`, `preflight`, `install`, `verify`, and `uninstall`, each with
`--scope project|local|user` where it applies. Never write the settings JSON,
the handler, `.shellcheckrc`, or `.editorconfig` with file tools for this gate.
If the script cannot run (no Bash tool, missing `jq`), say so and stop.

## Guard: Claude Cowork

If `assess` reports `surface: Claude Cowork`, or any command exits 3, explain
that Cowork does not run settings-based hooks, that nothing was installed, and
stop. The `shell-lint` skill still works there.

## What the gate does (explain this before installing)

| Event | What happens | Effect on Claude |
| --- | --- | --- |
| `UserPromptSubmit` | Records the ShellCheck/EditorConfig configuration and each touched script's suppression count as accepted (only the user changes files between turns) | None |
| `PreToolUse` on `Write`, `Edit`, `Bash` | Denies an edit that adds `# shellcheck disable=…` or `# shellcheck source=/dev/null`, or that changes `.shellcheckrc`/`shellcheckrc`, the user-level rc, the shfmt keys of `.editorconfig`, the gate's handler, or its settings (including `disableAllHooks`); denies Bash commands that do the same | The edit does not happen; Claude is told to fix the script |
| `PostToolUse` on the same tools | For each edited `.sh`, `.bash`, `.bats`, or extensionless sh/bash/dash/ksh script: `shfmt -w`, then `shellcheck -f gcc`, then suppression and configuration checks | Clean: the user sees `shell-quality ✓ …`. Anything left: exit 2, Claude sees every finding and must fix it now |
| `Stop` | Re-checks every script edited this session (ShellCheck, `shfmt -d`, suppressions) and the configuration | Anything left: exit 2, Claude keeps working. After the chosen number of consecutive blocks (default 5), the turn may end with a visible warning |

It fails closed: without `shellcheck`, `shfmt`, or `jq`, with a broken rc file,
or on an unreadable payload it exits 2 with the reason. It only looks at
scripts Claude touched, never the whole repository. zsh scripts are ignored
(ShellCheck does not support them). Details and verified Claude Code behavior:
[`references/hook-contract.md`](references/hook-contract.md).

## How the skill was triggered

- **Explicit request** to add, check, update, or remove the gate: run the
  matching workflow below.
- **Incidental** (the user is working on shell scripts and did not ask for a
  hook): do not run anything. At most once per session, if the user complains
  that Claude left ShellCheck findings behind or added `disable` directives,
  offer the gate in one sentence; never repeat the offer.

## Install workflow

Stop at every gate. Silence, "ok", or an ambiguous answer is not a choice. A
scope or mode named in the user's request counts as the choice, but still run
`assess` and confirm it in one sentence. "None" is a valid answer; accept it.

1. **Assess.** Run `assess`. Summarize: ShellCheck and shfmt versions and
   paths; the shell scripts found; the rc file and EditorConfig that apply
   today; the baseline findings and unformatted scripts under each mode; where
   the gate is already installed; other `PostToolUse`/`Stop` hooks that run in
   parallel; any `WARNING`. If a tool is missing, tell the user how to install
   it and stop until they do.
2. **Explain the configuration modes and show each one.** Read
   [`references/config-modes.md`](references/config-modes.md). Run
   `show-config` for every mode that applies and show the user the **exact
   configuration** in fenced blocks (for `recommended`, the whole
   `.shellcheckrc` and the `[[shell]]` EditorConfig block; for `own`, the rc
   file and EditorConfig lines in use; for `defaults`, what `--norc` and
   `shfmt -i 0` mean). Explain what each changes for this project, using the
   baseline from step 1. Recommend one mode with the reason, and wait.
3. **Recommend a scope and wait.** Read
   [`references/scopes.md`](references/scopes.md). Recommend project, local,
   or user with the trade-off, and wait. Mention that the gate can live in only
   one scope at a time.
4. **Preflight.** Run `preflight --scope S --config-mode M [--config-path F]`.
   On any `FAIL`, report the exact reason and stop. If the recommended mode
   fails because an rc file already exists, offer `own` (keep theirs) or let
   the user merge the profile by hand; never overwrite theirs.
5. **Install.** Run `install` with the same options (add `--max-blocks N` if
   the user chose a limit other than 5). The script backs up the settings file
   and `.editorconfig` outside the working tree, writes the recommended rc only
   where none exists, appends the marked `[[shell]]` block only when
   EditorConfig sets no shell style, copies the handler byte for byte, merges
   five hook groups idempotently, runs the test suite against the installed
   copy, and restores everything itself on failure.
6. **Verify and hand off.** Show the test summary and the configuration the
   hook uses, exactly as printed. Tell the user to open `/hooks` (or restart
   the session) to confirm the groups are loaded. For project scope, remind
   them to commit `.claude/settings.json`, `.claude/hooks/shell-quality-gate.sh`,
   and a new `.shellcheckrc`/`.editorconfig` change together. Give the rollback
   exactly as printed.

## Status, verify, update, and uninstall

- **Status**: run `status`; report each scope, the installed command (mode,
  pinned rc, style fallback, max blocks), the handler version, and every
  `WARNING`.
- **Verify**: run `verify --scope S`.
- **Update or uninstall**: once the gate is installed it denies Claude running
  `manage.sh install` or `uninstall` itself, because changing the gate is the
  user's decision. Give the user the exact command to run with the `!` prefix,
  for example
  `! bash "<skill dir>/scripts/manage.sh" uninstall --scope project`, and
  explain what it will do. Uninstall keeps the recommended `.shellcheckrc` and
  the marked `[[shell]]` block, since the editor and CI may rely on them.

## When the gate blocks you

- **A finding after an edit (PostToolUse):** fix it in the script before any
  other change. Re-read the file first if the hook said it reformatted it.
- **A denied edit (PreToolUse):** do not look for another way to add the
  directive or change the configuration (a different spelling, Bash, a new rc
  file). Change the script. If a check seems wrong for the project, stop and
  tell the user which code, where, and why; changing it is their decision.
- **The Stop gate:** fix what it lists. If something truly needs the user's
  decision, say exactly what and why; do not claim the work is done.
- **`shellcheck not found`, `shfmt not found`, or a gate error:** tell the
  user; do not work around it.

## Additional resources

- [`references/hook-contract.md`](references/hook-contract.md) — each event,
  exit code, and message; what Claude and the user see; limits.
- [`references/config-modes.md`](references/config-modes.md) — recommended,
  own, and defaults: what each runs, where files go, how to explain them.
- [`references/scopes.md`](references/scopes.md) — project, local, and user
  scope; the exact settings groups; manual installation.
- [`references/rollback.md`](references/rollback.md) — removal, recovery, and
  troubleshooting.
- `assets/shell-quality-gate.sh` — the handler (copied, never edited in place).
- `assets/shellcheckrc`, `assets/editorconfig-shell` — the recommended profile.
- `scripts/test-gate.sh` — the behavioral suite; pass a handler path.
