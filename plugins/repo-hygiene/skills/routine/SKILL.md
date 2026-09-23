---
name: routine
description: Audit a Git repository and its hosting provider the way a senior Git expert would, then clean it only with the user's approval of each item. Inspect every area without waiting to be told which commands to run, since read-only inspection needs no permission. Areas include working tree and index, hidden local changes, ignore rules, branches (merged, squash-merged, gone, unique), remotes, tags, stashes, worktrees, submodules, symlinks and outside influence, config, aliases and hooks, identity, secrets and large files in history, hidden refs, reflogs, object store, leftovers from interrupted operations, third-party references, and pull requests, reviews, settings and CI on the provider. Deliver one complete report with detailed recommendations a non-expert can decide on, and execute only the approved IDs.
when_to_use: The user asks to audit, review, clean, tidy or prune a Git repository or its branches, stashes, worktrees, leftover files, old or abandoned pull requests, or repository drift, in English or Spanish (limpia el repo, revisa las ramas, audita el repositorio, borra lo que sobra). Also when the user asks which commit introduced or removed a file, a line, a string or a regression, and before deleting branches, stashes or files in bulk. Not for writing commits, resolving a merge conflict in progress, or explaining Git concepts.
---

# Repository hygiene — routine

Audit the repository the way the top few percent of Git experts would, report everything in
one pass, and change nothing the user has not approved by ID. "Routine" means everyday use,
not a shallow audit: cover every area below at its routine depth.

## Rules

1. **Read freely; mutate only by approval.** Every read-only command is already authorized.
   Run it without asking. Asking before a read is a defect. Everything else needs an approved
   item ID. A request such as "clean it up" is not an approval.
2. **Follow the audit contract** at `${CLAUDE_PLUGIN_ROOT}/references/audit-contract.md`.
   Read it before the first command. It covers safety flags, command form, secrets, findings,
   recommendations, execution and false positives.
3. **Count and walk with `git --no-replace-objects`.** A replace ref silently falsifies
   counts. Measured: an audit reported 4 commits ahead where the truth was 5.
4. **Redact in the same command that prints** remote URLs and config. Never read
   secret-shaped files, and never `cat` unknown payloads.
5. **Finish the coverage before reporting.** An area is `inspected`, `not applicable` (with
   the reason) or `blocked` (with the command and error). Nothing is skipped silently.

## Procedure

1. **Preflight.**
   - `git rev-parse --show-toplevel --absolute-git-dir --git-common-dir`. Exit 128 means this
     is not a repository: stop and say so.
   - Before the first `git status`, list the config keys that run programs (filter, textconv,
     fsmonitor, external diff, pager). The list is in `areas/config-links-identity.md`, G12.
     `git status` runs a configured clean filter, so if one exists, say so and avoid the
     commands that would run it.
   - Check for an operation in progress (`areas/repository-and-operations.md`). If one exists,
     report it first, and recommend nothing that touches the index or `HEAD` until the user
     decides.
2. **Evidence package.** Create it (`audit-contract.md`, section 10) and save each command's
   output and exit code there.
3. **Coverage.** Run the Routine checks of each area file under
   `${CLAUDE_PLUGIN_ROOT}/references/areas/`, and the provider recipes in
   `${CLAUDE_PLUGIN_ROOT}/references/provider.md`:

   | Areas | File |
   | --- | --- |
   | G1 identity and format · G2 interrupted operations and leftovers | `areas/repository-and-operations.md` |
   | G3 working tree, index, **hidden assume-unchanged/skip-worktree edits** · G4 ignore and attributes · G20 editor/OS noise | `areas/worktree-index-rules.md` |
   | G5 local branches and the integration ladder · G6 remotes · G7 tags, including **lightweight local-only** | `areas/branches-remotes-tags.md` |
   | G8 stashes · G9 worktrees · G10 submodules and nested repositories | `areas/stashes-worktrees-submodules.md` |
   | G11 links and outside influence · G12 config, aliases, hooks, tool footprints · G13 identity and signing | `areas/config-links-identity.md` |
   | G14 **secrets and large blobs in history** (paths only) | `areas/history-and-secrets.md` |
   | G15 ref namespaces · G16 reflogs and recovery | `areas/refs-reflogs-recovery.md` |
   | G17 object store and maintenance | `areas/object-store.md` |
   | G18 **server and export footprints** · G19 third-party repository references · G22 copies elsewhere (registered worktrees and the agent worktree folders) | `areas/footprints-and-references.md` |
   | G21 tracing, only when the request asks where code or a behavior came from | `areas/tracing.md` |
   | P1–P9 provider: settings, branches and rulesets, PRs and review threads, issues, CI, releases, access, alerts, workspaces | `provider.md` |

   The areas in bold were missed by every unguided audit measured while building this plugin.
   Check them explicitly. For any command's options and safety class, read
   `${CLAUDE_PLUGIN_ROOT}/references/commands/git-<command>.md`. To locate any Git command or
   topic, use `${CLAUDE_PLUGIN_ROOT}/references/git-command-map.md`.
4. **Tripwires.** These need `deep`. Report each as a finding that recommends the user run
   `/repo-hygiene:deep`, and say why:
   - any ref outside heads, remotes, tags and stash;
   - replace refs or grafts;
   - `core.hooksPath` set, or command-executing config keys in repository scope;
   - alternates;
   - `count-objects` garbage above 0, or a `gc.log`;
   - embedded credentials;
   - secret-shaped paths in history;
   - migration footprints;
   - closed-unmerged PRs;
   - merged PRs whose branch advanced after the merge;
   - more unresolved review threads than one session can adjudicate.
5. **Report.** Use `${CLAUDE_PLUGIN_ROOT}/references/report-template.md`. Present one report
   after the coverage is complete. Every recommendation is detailed per
   `audit-contract.md`, section 6: what, why, steps, what changes and what stays, risk,
   preconditions, literal command, undo, the cost of doing nothing, and the approval scope.
   End with one approval request.
6. **Execute approved IDs** per `audit-contract.md`, section 8: re-check, record the
   pre-state, run the literal command, verify, report.

## Scale

When the work exceeds one session, recommend `/repo-hygiene:deep plan`. That is the case for
hundreds of review threads, hundreds of unreachable commits, integration of preserved
histories, a "only main should remain" goal, or history rewriting. Present everything found
so far in the same report. Never stop early without saying what remains.

## Non-interactive runs

In `claude -p` and SDK runs nobody can approve, so deliver the report and recommendations
only.
