---
name: ruff-hooks
description: Make every Python file Claude edits pass Ruff before Claude can move on, by installing the ruff-quality gate through its own script only, never by writing the settings, the handler or a Ruff configuration by hand. The gate is four hooks — PreToolUse denies edits that add noqa, ruff directives or fmt and isort skips or that change the Ruff configuration or the gate itself; PostToolUse fixes, formats and rechecks each touched file; Stop reblocks until the session's Python is clean, up to a configurable limit. Show the exact configuration of each of the three modes and install nothing until the user picks a scope and a mode. It lives in one scope at a time, fails closed without ruff or jq, and looks only at files Claude touched. Once installed it denies Claude changing or removing it; that command is the user's to run. For using Ruff itself, use the ruff skill.
when_to_use: When the user asks to add a Ruff hook, lint and format Python after every edit, stop Claude from adding noqa, or install, check, update or remove the gate.
compatibility: Claude Code (CLI, Desktop, IDE) on macOS, Linux, WSL, or Windows with Git Bash. Needs bash >= 3.2, jq >= 1.6, git, and ruff >= 0.16. Not supported in Claude Cowork, where settings-based hooks do not run.
license: Apache-2.0
---

# Ruff hooks

Install, inspect, and remove the **ruff-quality gate**: Claude Code hooks that
make every Python file Claude creates or edits pass Ruff before Claude can move
on or finish, without ever silencing a rule. Installing the plugin wires
nothing; the gate exists only after the user asks, chooses a scope and a
configuration mode, and this workflow installs it.

Every state change goes through one deterministic script:

```bash
bash "${CLAUDE_SKILL_DIR}/scripts/manage.sh" <command> [options]
```

Commands: `assess`, `show-config --config-mode MODE [--config-path FILE]`,
`status`, `preflight`, `install`, `verify`, and `uninstall`, each with
`--scope project|local|user` where it applies. Never write the settings JSON,
the handler, or a Ruff configuration with file tools for this gate. If the
script cannot run (no Bash tool, missing `jq`), say so and stop.

## Guard: Claude Cowork

If `assess` reports `surface: Claude Cowork`, or any command exits 3, explain
that Cowork does not run settings-based hooks, that nothing was installed, and
stop. The `ruff` skill still works there.

## What the gate does (explain this before installing)

| Event | What happens | Effect on Claude |
| --- | --- | --- |
| `UserPromptSubmit` | Records the Ruff configuration and each touched file's suppression count as accepted (only the user changes files between turns) | None |
| `PreToolUse` on `Write`, `Edit`, `NotebookEdit`, `Bash` | Denies an edit that adds `noqa`, `ruff: noqa/ignore/disable/file-ignore`, `fmt: off/skip`, or `isort: skip/off`, or that changes `ruff.toml`, `.ruff.toml`, `[tool.ruff]`, the user-level Ruff configuration, the gate's handler, or its settings (including `disableAllHooks`); denies Bash commands that do the same | The edit does not happen; Claude is told to fix the code |
| `PostToolUse` on the same tools | For each edited `.py`, `.pyi`, or `.ipynb`: `ruff check --fix` (safe fixes only; unused imports are left for the Stop gate), `ruff format`, `ruff check`, then suppression and configuration checks | Clean: the user sees `ruff-quality ✓ …`. Anything left: exit 2, Claude sees every finding and must fix it now |
| `Stop` | Re-checks every Python file edited this session (lint, format, suppressions) and the configuration | Anything left: exit 2, Claude keeps working. After the chosen number of consecutive blocks (default 5), the turn may end with a visible warning |

It fails closed: without `ruff` or `jq`, with a broken configuration, or on an
unreadable payload it exits 2 with the reason, so a change is never reported
as verified when it was not. It only looks at files Claude touched, never the
whole repository. Details and verified Claude Code behavior:
[`references/hook-contract.md`](references/hook-contract.md).

## How the skill was triggered

- **Explicit request** to add, check, update, or remove the gate: run the
  matching workflow below.
- **Incidental** (the user is working on Python and did not ask for a hook):
  do not run anything. At most once per session, if the user complains that
  Claude left Ruff errors behind or added `noqa`, offer the gate in one
  sentence; never repeat the offer.

## Install workflow

Stop at every gate. Silence, "ok", or an ambiguous answer is not a choice. A
scope or mode named in the user's request counts as the choice, but still run
`assess` and confirm it in one sentence. "None" is a valid answer; accept it.

1. **Assess.** Run `assess`. Summarize: Ruff version and where it was found;
   Python files; the Ruff configuration that applies today (project level,
   user level, and what Ruff resolves for a sample file); the baseline finding
   count under each mode; where the gate is already installed; other
   `PostToolUse`/`Stop` hooks that will run in parallel; any `WARNING`. If Ruff
   is missing, tell the user how to install it (`uv tool install ruff`, or add
   it to the project's dev dependencies) and stop until they do.
2. **Explain the configuration modes and show each one.** Read
   [`references/config-modes.md`](references/config-modes.md). Run
   `show-config` for every mode that applies and show the user the **exact
   configuration** in a fenced block (for `recommended`, the whole bundled
   `ruff.toml`; for `own`, the file Ruff discovers or the one they name; for
   `defaults`, the rule count and key settings). Explain in plain words what
   each changes for this project, using the baseline counts from step 1.
   Recommend one mode with the reason, and wait for the choice.
3. **Recommend a scope and wait.** Read
   [`references/scopes.md`](references/scopes.md). Recommend project, local,
   or user with the trade-off, and wait for the choice. Mention that the gate
   can live in only one scope at a time.
4. **Preflight.** Run `preflight --scope S --config-mode M [--config-path F]`.
   On any `FAIL`, report the exact reason and stop. If the recommended mode
   fails because a Ruff configuration already exists, offer `own` (keep theirs)
   or let the user merge the profile by hand; never overwrite theirs.
5. **Install.** Run `install` with the same options (add `--max-blocks N` if
   the user chose a limit other than 5). The script backs up the settings file
   outside the working tree, writes the recommended profile only where no
   configuration exists, copies the handler byte for byte, merges five hook
   groups idempotently, runs the test suite against the installed copy, and
   restores everything itself on failure.
6. **Verify and hand off.** Show the test summary and the configuration the
   hook uses, exactly as printed. Tell the user to open `/hooks` (or restart
   the session) to confirm the groups are loaded; the script cannot observe
   that. For project scope, remind them to commit `.claude/settings.json`,
   `.claude/hooks/ruff-quality-gate.sh`, and a new `ruff.toml` together. Give
   the rollback exactly as printed.

## Status, verify, update, and uninstall

- **Status**: run `status`; report each scope, the installed command (mode,
  pinned config, max blocks), the handler version, and every `WARNING`.
- **Verify**: run `verify --scope S`.
- **Update or uninstall**: once the gate is installed it denies Claude running
  `manage.sh install` or `uninstall` itself, because changing the gate is the
  user's decision. Give the user the exact command to run with the `!` prefix,
  for example
  `! bash "<skill dir>/scripts/manage.sh" uninstall --scope project`, and
  explain what it will do. Uninstall keeps the recommended `ruff.toml`, since
  the editor and CI may rely on it; say so.

## When the gate blocks you

- **A finding after an edit (PostToolUse):** fix it in the code before any other
  change. Re-read the file first if the hook said it rewrote it.
- **A denied edit (PreToolUse):** do not look for another way to add the
  suppression or change the configuration (a different comment spelling, Bash,
  a new config file). Change the code. If the rule itself seems wrong for the
  project, stop and tell the user which rule, where, and why; changing it is
  their decision.
- **The Stop gate:** fix what it lists. If something truly needs the user's
  decision, say exactly what and why; do not claim the work is done.
- **`ruff not found` or a gate error:** tell the user; do not work around it.

## Additional resources

- [`references/hook-contract.md`](references/hook-contract.md) — each event,
  exit code, and message; what Claude and the user see; limits.
- [`references/config-modes.md`](references/config-modes.md) — recommended,
  own, and defaults: what each runs, where files go, and how to explain them.
- [`references/scopes.md`](references/scopes.md) — project, local, and user
  scope; the exact settings groups; manual installation.
- [`references/rollback.md`](references/rollback.md) — removal, recovery, and
  troubleshooting.
- `assets/ruff-quality-gate.sh` — the handler (copied, never edited in place).
- `assets/ruff.toml` — the recommended profile.
- `scripts/test-gate.sh` — the behavioral suite; pass a handler path.
