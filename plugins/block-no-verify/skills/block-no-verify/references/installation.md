# Installation contract

Read this after the user has approved installation and chosen a scope. Every
write goes through `scripts/manage.sh`; this file documents what it does so
the result can be explained and audited.

## Commands

| Command | Writes | What it does |
| --- | --- | --- |
| `assess` | nothing | Environment (surface, OS, bash and jq versions), repository, hook tooling, signing config, policy state per scope, every existing `PreToolUse` group (project, local, user, managed, installed plugins), verdict |
| `status` | nothing | Per scope: group state (`present`, `absent`, `missing`, `mixed`, `invalid`), installed handler version vs bundled |
| `preflight --scope S` | nothing | Fails on: Cowork, bash < 3.2 or missing, jq < 1.6 or missing, project/local outside a Git repository, settings that are not a JSON object with an array `hooks.PreToolUse`, a hand-edited group mixing this handler with others, no write permission, `disableAllHooks: true` in any scope, managed `allowManagedHooksOnly`/`disableAllHooks`, or a handler that does not deny a bypass and allow `git status` on this machine |
| `install --scope S` | settings, handler, backups, `.git/info/exclude` (local) | Preflight, then install (below) |
| `verify --scope S` | nothing | Test suite against the installed copy, plus live payload decisions |
| `uninstall --scope S` | settings, handler, backups, `.git/info/exclude` (local) | Removes only this policy (below) |

Exit codes: `0` success, `1` failed check or error, `2` usage, `3` Cowork.

## Install, step by step

1. **Up-to-date check.** If the installed handler is byte-identical to the
   bundled one and the settings hold exactly one identical group, nothing is
   written; the script only verifies.
2. **Backups.** The existing settings file and any existing handler are copied
   to `<git common dir>/block-no-verify-backups/` (project, local) or
   `~/.claude/backups/block-no-verify/` (user), named
   `<file>.<UTC timestamp>.<pid>.bak`. Backups never land in the working tree.
3. **Handler.** `assets/block-no-verify.sh` is copied to a temporary file,
   made executable, moved into place, and compared with `cmp`. The installed
   copy is standalone: updating or removing the plugin does not change it.
4. **Merge.** Exactly one group from `assets/settings-fragment.json` (with the
   scope's command) is merged into `hooks.PreToolUse`:
   - no group yet: appended at the end (hooks run in parallel, so order is irrelevant);
   - an older group of this policy: replaced in place, extra copies dropped;
   - every other key, hook, matcher, and permission is preserved.
   The file is written to a temporary file, checked to be a JSON object, then
   moved into place. `jq` normalizes whitespace to two-space indentation; key
   order and values are unchanged. Report this to the user.
5. **Verify.** The bundled suite runs against the installed handler, then four
   live payloads are fed through it. Any failure restores the backups (or
   deletes files that did not exist before) and exits 1.
6. **Git exclusions** (only after verification passes). Local scope appends
   marked lines to `.git/info/exclude` for the handler and
   `settings.local.json` when they are neither ignored nor tracked. Project
   scope removes a local exclusion of the shared handler so it can be committed.

## Group identity

A group belongs to this policy when every handler in it has a `command`
containing `block-no-verify.sh`. A group mixing this handler with other
handlers is never modified automatically: preflight and uninstall stop and
ask for a manual fix.

## Uninstall, step by step

1. Refuse on invalid JSON or a mixed group.
2. Back up the settings file (same location as install).
3. Remove only this policy's groups. Remove `hooks.PreToolUse` and `hooks`
   only if that removal emptied them. For project and local scope,
   delete the settings file if it became `{}` (the backup is kept).
4. Delete the handler unless the other project/local scope still references
   it; remove the empty `hooks/` directory.
5. Local scope: remove this policy's lines from `.git/info/exclude`.

## What the skill must report

Scope, settings path, handler path and version, backup path, test-suite
summary, the live payload decisions, the `/hooks` check still owed by the
user, and the rollback. Separate what was verified (files, tests, payloads)
from what was not (live loading in the session).
