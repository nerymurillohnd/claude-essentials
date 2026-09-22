# ruff-quality 0.2.0 — design

**Status:** approved by the maintainer on 2026-09-22 (plan `agile-growing-hejlsberg`), built
in the same branch. **Decision record:** [ADR-0007](../../decisions/adr-0007-gates-ship-as-plugin-hooks.md).
**Canonical user-facing contract:** [`plugins/ruff-quality/README.md`](../../../plugins/ruff-quality/README.md)
(hooks table, Requirements, Limitations). This spec records why the plugin looks the way it
does and how that was verified; it does not repeat the README's tables.

## Goal

Every Python file Claude writes or edits passes Ruff before Claude finishes, using the Ruff
the user already has and the configuration Ruff already finds, without the plugin ever
installing, downloading or configuring anything.

## What changed from 0.1.x, and why

0.1.x installed its gate through a skill: `manage.sh` copied a handler into the user's
`.claude/hooks/`, merged hook groups into a `settings.json`, and could write a bundled
`ruff.toml`. Measured on 2026-09-21 and 2026-09-22 (ADR-0007, Context):

- the copied handler froze at the version installed; a plugin update never reached it;
- the bundled profile was silently replaced by any nearer `pyproject.toml` with
  `[tool.ruff]` or `.ruff.toml` (Ruff's own discovery, reproduced on 0.16.8);
- the maintainer tooling installed CPython 3.8 globally, and a hook running `uvx ruff` would
  do the same, or exit 127 (a non-blocking error: the edit passes unchecked) without `uv`.

0.2.0 removes the `ruff-hooks` skill, its installer and its profile, and ships the gate as a
plugin component. There is no migration: nothing of 0.1.x was ever installed by a user.

## Surfaces

| Surface | Decision | Why |
| --- | --- | --- |
| Skill `ruff` | Used | Knowledge Claude needs on any host: command routes, working order, discovery, migration, CI, diagnosing, suppressions never to add |
| Hooks (`hooks/hooks.json` + `scripts/ruff-gate.sh`) | Used | The only surface that runs after every edit without Claude choosing to; updates with the plugin |
| Command hooks vs prompt/agent hooks | Command | Every decision is deterministic (run Ruff, match a marker); the one judgment call, a suppression, goes to the user through `ask`. A model per edit adds cost, latency and variance for nothing |
| `userConfig.enabled` | Used | Turns the hooks off without uninstalling the skill |
| Agents, commands, MCP, LSP, output styles, workflows | Rejected | Nothing to delegate or expose; the Ruff language server belongs to the editor |
| Bundled configuration | Rejected | A configuration is project policy; Ruff's discovery or defaults decide |
| `uv` / `uvx` in the hook | Rejected | Can download an interpreter or Ruff on a per-edit hook; B1 forbids it |

### Hook design

- **PreToolUse** (`Write|Edit`, one handler per `if` pattern, plus `Bash`): asks before an
  edit adds `noqa`, `ruff: noqa|ignore|disable|file-ignore`, `fmt: off|skip`,
  `yapf: disable` or `isort: skip`, before `ruff check --add-noqa`/`--add-ignore`, and before
  a change to `ruff.toml`, `.ruff.toml` or the `[tool.ruff*]` tables of `pyproject.toml`.
  Each replacement is compared with its own `old_string` by marker text (marker to end of line),
  so a marker that already existed does not ask again, a widened one (another code, a bare
  `# noqa`, line-level made file-level) does, and removing one never offsets adding another.
  `# flake8: noqa` counts. Harmless redirects (`2>&1`, `>/dev/null`) are not writes.
- **PostToolUse** (`Write|Edit` on `.py`, `.pyw`, `.pyi`): `ruff check --fix
  --no-unsafe-fixes --unfixable F401`, `ruff format`, `ruff check --no-fix`, all with
  `--force-exclude --no-cache`, on the whole file. `F401` is unfixable so an import added in
  one edit and used in the next survives. Findings left → top-level `decision: "block"` with
  the findings as `reason` (reaches Claude) and a one-line `systemMessage` (reaches the user).
- **Stop**: re-fixes, re-formats and re-checks every file the session touched; findings →
  `additionalContext` "attempt N of 7". It gives up, with a message to the user, after 7
  attempts or as soon as the findings are unchanged since the previous attempt (Claude asked
  the user, or cannot fix what is left), and then forgets those files until they are edited
  again, so the next turn is not pushed into the same loop. The report is capped at 8,000
  characters (Claude Code keeps 10,000 of `additionalContext`). Claude Code itself ends a turn
  after 8 consecutive Stop continuations.
- **Claude sees what it must act on**: a missing Ruff and a file the hook rewrote reach
  Claude through `additionalContext` as well as the user's `systemMessage`, which Claude
  never sees. A file the project excludes is reported as not checked, never as clean.
- **`if` twins** `[observed]`: in a hook `if`, `Edit(P)` fires for the Edit tool only and
  `Write(P)` for the Write tool only (probe plugin, Claude Code 2.1.278, 2026-09-22; unlike
  permission rules, where `Edit` covers every file-editing tool). Every file condition
  therefore has a `Write(...)` twin; invariant H7 enforces it.
- **Tool resolution**: `.venv/bin`, `venv/bin`, `.venv/Scripts` walking up from the file to the
  project root (`CLAUDE_PROJECT_DIR`, else `cwd`), only executables the user owns, then `PATH`, then `~/.local/bin`, `/opt/homebrew/bin`, `/usr/local/bin` (GUI-launched
  sessions get a minimal `PATH`).
- **State**: one file per session under `${CLAUDE_PLUGIN_DATA}/sessions` (TMPDIR fallback),
  pruned after 7 days.

## Requirements

The README's 📋 Requirements table is canonical: Claude Code 2.1.222 (2.1.269 for the
`/config` row), Ruff 0.16, Bash 3.2, jq 1.6, and Git Bash on Windows. Platforms: macOS,
Linux, WSL, Windows with Git Bash. Not Cowork (hooks may not run there).

## Non-goals

- Installing Ruff, running `uv`/`uvx`, or using the network.
- Writing or changing any Ruff configuration.
- Unsafe fixes, or removing an import Claude just added.
- Checking files Claude did not touch, notebooks, or files written through Bash.
- Enforcement for humans and other tools: that is pre-commit and CI.

## Failure modes

| Failure | Behavior | Open or closed |
| --- | --- | --- |
| Ruff missing | One `systemMessage` per session with install routes; nothing checked | Open |
| jq missing | Same, naming jq | Open |
| Ruff exits 2 (bad config, `required-version`, unparsable file) | Reported as a tool break, not as findings; Claude is told to tell the user, and Stop never continues on it | Open for the edit, reported |
| Findings after an edit | `block` + findings to Claude | Closed on the file (Claude must act) |
| Findings at Stop | Up to 7 continuations, then a failure message | Closed, bounded |
| Suppression or config change | `ask`; in `-p` mode nobody answers, so it is refused | Closed pending the user |
| `enabled = false` | Every event exits 0 silently | Open by choice |
| Hook timeout (10/60/120 s) | Claude Code proceeds without the answer | Open |

## Verification

- Suite `scripts/plugin_validation/suites/ruff-quality/test-gate.sh`, run by `make test-slow`
  under `bash` and `/bin/bash`: 75 cases, both directions (suppression asks vs plain edit
  silent; config asks vs other `pyproject` table silent; fix, findings, tool break, Stop 7+1,
  missing tool, switch off).
- Static gates: H1–H7 and B1 in `make validate`; `claude plugin validate --strict` in
  `make validate-cli`.
- Live `[observed]`, 2026-09-22, Claude Code 2.1.278, `claude -p --plugin-dir` in a scratch
  project: Write of a failing file → `block` → Claude fixed it with Edit → `✓ calc.py: clean`
  → Stop `✓ 1 Python file(s) … pass Ruff`; an Edit adding `# noqa: F401` → `ask`. The first
  live run found the `if` twin gap above, which the suite could not see (it calls the
  handler directly).
- Evals: `plugins/ruff-quality/evals/` (01, 02, 04 kept; 03 "fixes what the hook reports"),
  run per the eval protocol; numbers go to the PR and `docs/audits/`.
- Not exercised live: the Stop cap (covered by the suite) and Windows.

## References

- Hooks reference and guide: https://code.claude.com/docs/en/hooks, https://code.claude.com/docs/en/hooks-guide
- Plugins reference (hooks, `userConfig`, `${CLAUDE_PLUGIN_DATA}`): https://code.claude.com/docs/en/plugins-reference
- Permission rule syntax: https://code.claude.com/docs/en/permissions
- Ruff configuration and formatter: https://docs.astral.sh/ruff/configuration/, https://docs.astral.sh/ruff/formatter/
- Field survey (GitHub, 2026-09-22): alexfazio/plankton (adopt: config protection + linter +
  Stop guardian), melodic-software ruff-format (adopt: `--unfixable F401`,
  `--no-unsafe-fixes`, `--force-exclude --no-cache`, notice once when missing; its rejection
  of `uvx`), TheBushidoCollective/han (reject: its own binary), astral-sh/claude-code-plugins
  (skills only; reject its unpinned `uvx ruff` route).
