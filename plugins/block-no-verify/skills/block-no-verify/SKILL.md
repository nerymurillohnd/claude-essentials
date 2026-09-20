---
name: block-no-verify
description: Stop Claude from bypassing local Git verification, and manage that policy only through its own script, never by editing settings JSON or transcribing the handler by hand. The policy denies --no-verify, -n, --no-gpg-sign, -c core.hooksPath=, HUSKY=0 and their variants across Bash and PowerShell, and never touches the user's own terminal or CI. Install nothing until the user picks a scope, which is the only approval; the script assesses, preflights, backs up outside the work tree, merges one hook group idempotently, runs its suite and restores itself on failure. Report that Claude Cowork runs no settings hooks and stop. When the policy denies a command, fix the cause instead of reshaping the command to evade it.
when_to_use: When the user asks to block --no-verify, protect their Git hooks, enforce commit signing, or install, check, verify or remove the policy, and passively whenever a task involves committing, pushing, merging or rebasing — check status once per session and offer the policy at most once.
compatibility: Claude Code (CLI, Desktop, IDE). Needs bash >= 3.2, jq >= 1.6, and git. Not supported in Claude Cowork, where settings-based hooks do not run.
license: Apache-2.0
---

# Block No Verify

Install, inspect, and remove a Claude Code policy that denies Git commands
which skip local hooks or signing (`--no-verify`, `-n`, `--no-gpg-sign`,
`-c core.hooksPath=…`, `HUSKY=0`, and similar) when Claude runs them. The
plugin itself installs nothing: protection exists only after the user asks,
chooses a scope, and this workflow wires it.

All state changes go through one deterministic script:

```bash
bash "${CLAUDE_SKILL_DIR}/scripts/manage.sh" <assess|status|preflight|install|verify|uninstall> [--scope project|local|user]
```

Never edit settings JSON or transcribe the handler with file tools for this
policy. If the script cannot run (no Bash tool, permission denied, missing
`jq`), say so and stop; do not inspect or edit settings files as a substitute.

## Guard: Claude Cowork

If `assess` or `status` reports `surface: Claude Cowork`, or any command exits
3, state that Cowork does not run settings-based hooks, that no protection is
active in this session, and stop after reporting what `assess`/`status` showed.

## How the skill was triggered

- **Incidental** (the user is committing, rebasing, or fixing a hook failure,
  and did not ask for protection): run `status` at most once per session. If
  a scope shows a `WARNING`, mention it in one sentence. If the policy is
  present, say nothing. If it is absent and this is not Cowork, add one
  sentence offering to assess it; never repeat the offer after it was made or
  declined. Continue the user's task either way. If `status` cannot run, skip
  it silently.
- **Explicit request or accepted offer**: run the gated workflow below.
- **Status, verify, or uninstall request**: run that command only (see the end of this file).

## Gated workflow

Stop at every gate. Silence, "ok", "sure", or an ambiguous answer is not a
scope choice. The scope choice is the install approval: after a passing
preflight, install without asking again. A scope named in the user's request
counts as the choice, but still run `assess` and confirm that scope in one
sentence before preflight. "None" is a valid answer; accept it and stop.

1. **Assess.** Run `assess`. Summarize: Git repository or not; hook tooling
   found (`core.hooksPath`, `.husky/`, `.pre-commit-config.yaml`, lefthook,
   active `.git/hooks`); signing configuration; where the policy is already
   installed; every existing `PreToolUse` hook it listed; and any `WARNING`.
   - Verdict "nothing to protect": say so, recommend not installing (user
     scope may still cover other repositories), and stop until the user asks
     to continue.
   - Verdict "not a git repository": only user scope is possible; say so and
     offer only that.
2. **Recommend a scope and wait.** Read `references/scopes.md`. Recommend one
   scope with its trade-off (project = committed and shared with the team;
   local = only this user in this repository; user = every project on this
   machine) and mention where the policy already exists. Wait for the choice.
3. **Preflight.** Run `preflight --scope <choice>`. On any `FAIL`, report the
   exact reason and stop. For `invalid` or `mixed` settings, show the user the
   file and the problem and let them fix it; edit it only if they explicitly
   ask you to.
4. **Install.** Read `references/installation.md`, then run
   `install --scope <choice>`. The script backs up the settings file outside
   the working tree, copies the handler byte-for-byte, merges exactly one
   handler group idempotently, verifies, and restores the backup itself on
   failure. On failure, report it and stop.
5. **Verify.** Show the test-suite summary and the live payload decisions the
   script printed (a bypass → DENY, a clean commit → ALLOW). Never report
   success that the output does not show.
6. **Hand off.** Tell the user to open `/hooks` (or restart the session) to
   confirm the group is loaded; the skill cannot observe live loading itself.
   Relay the rollback exactly as the script printed it. For project scope,
   remind the user to commit `.claude/settings.json` and
   `.claude/hooks/block-no-verify.sh` together: a committed group whose handler
   is missing blocks nothing.

## Status, verify, and uninstall (on request only)

- **Status**: run `status`; report each scope's group state, handler
  version, and every `WARNING` (a group whose handler is missing blocks nothing).
- **Verify**: to re-check an existing install, run `verify --scope <scope>`.
- **Uninstall**: run `status` first. If the policy is in exactly one scope,
  confirm that one; if several, ask which (or all); if none, say so and stop.
  Then run `uninstall --scope <scope>` per chosen scope and report the backup
  path. Suggest `/hooks` to confirm.

## When a command is denied by this policy

Do not retry with another bypass or reshape the command to evade the check.
Run the command without the bypass, read the hook or signing failure, and fix
the cause. If the hook itself is wrong or slow, ask the user; skipping it is
their decision, made in their own terminal. If the reason names a construct
the parser cannot resolve, rerun the same command directly with literal
arguments and no bypass. If it says `jq` is not installed, ask the user to
install `jq`. See the troubleshooting table in `references/rollback.md`.

## Additional resources

- **`references/scopes.md`** — scope trade-offs, per-environment settings
  snippets, and the manual steps to give a user who insists on doing it themselves.
- **`references/installation.md`** — the installation contract: what each
  script command reads and writes, merge and backup rules, failure handling.
- **`references/hook-lifecycle.md`** — verified Claude Code hook behavior
  (parallel execution, decision precedence, exit codes, timeouts, Cowork, cloud).
- **`references/bypass-catalogue.md`** — everything the handler denies, and
  what it cannot see.
- **`references/rollback.md`** — rollback and troubleshooting.
- **`assets/block-no-verify.sh`** — the handler (copied, never edited in place).
- **`assets/settings-fragment.json`** — the handler group the script merges.
- **`scripts/test-handler.sh`** — behavioral suite; pass a handler path.
