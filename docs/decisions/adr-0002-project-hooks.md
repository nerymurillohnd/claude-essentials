---

status: accepted
date: 2026-09-18
decision-makers: Nery Samuel Murillo Tejada
consulted: Claude Code (Opus 5) — live docs and changelog research
informed: Contributors to this repository
supersedes: none
superseded-by: none

---

# Project-level Claude Code hooks for session context, catalog integrity, and post-edit hygiene

## Context and Problem Statement

Every Claude Code session in this repo starts without knowing the state that
matters most for a public plugin marketplace: the git state, whether the
toolchain matches CI, which `claude plugin` subcommands the installed CLI
actually has, what's open in `docs/maintenance/`, whether the catalog
validates, and which upstream Claude Code changes since the last session touch
plugins, hooks, skills, or subagents. Two repo rules — "never hand-edit
`marketplace.json`'s `plugins` array" and "format/lint after every edit" —
were enforced only by CI or by memory.

The initial request listed `claude plugin` subcommands (`info`, `search`,
`refresh`, `doctor`) and `marketplace` subcommands (`refresh`, `info`) that do
not exist in Claude Code 2.1.276. The actual sets, from `--help`, are
`details, disable, enable, eval, init, install, list, marketplace, prune, tag,
uninstall, update, validate` and `add, list, remove, update`. That drift is
itself a reason to read the CLI at runtime rather than hardcode it.

How should this repo give each session that context, and enforce those two
rules, without slowing sessions down or bloating context?

## Decision Drivers

- Context must be accurate at session start, derived from the live CLI and
  repo — never from a hardcoded list.
- SessionStart delays Claude's first response until it finishes
  ([hooks reference](https://code.claude.com/docs/en/hooks#sessionstart)), so
  it has to be fast and must not depend on the network to succeed.
- Hook output is capped at 10,000 characters; context has a cost every session.
- Claude Code wiring is kept separate from project wiring. Hooks are harness
  glue, written as idempotent shell scripts: repeated runs converge on the same
  result and only write to their own cache. The project's own toolchain (Node
  scripts in `scripts/`, run by npm and CI) stays independent of them.
- Plugin lifecycle: with an explicit `version` in `plugin.json`, installed
  users receive a change only after a version bump
  ([version management](https://code.claude.com/docs/en/plugins-reference#version-management)).
  The hooks must catch that failure mode without assuming a strategy. The
  templates currently hardcode `"version": "0.1.0"`, which is misaligned with
  live docs (no stated strategy, non-standard tag links) and tracked as
  DEBT-0002. The hooks report both explicit-version and commit-SHA plugins, so
  resolving DEBT-0002 either way doesn't require changing them.

## Considered Options

- Bash hooks in `.claude/hooks/*.sh`, registered in the tracked `.claude/settings.json`
- Node.js hooks in `.claude/hooks/*.mjs`
- No hooks; rely on CLAUDE.md instructions and CI

## Decision Outcome

Chosen option: "Bash hooks". This keeps Claude Code wiring separate from the
project's Node wiring, matches the user-wide shell standard (`#!/usr/bin/env
bash`, ShellCheck with all optional checks enabled, shfmt), and produces small
idempotent scripts that call the project's own tools (`npm`/`node` scripts,
local Biome, `claude`, `git`) instead of reimplementing them.

The three hooks:

| Event | Matcher | Script | Behavior |
| --- | --- | --- | --- |
| `SessionStart` | `startup\|clear` | `session-start.sh` | Injects a snapshot of at most 9,000 characters (the cap is 10,000). It contains git branch/ahead-behind/dirty files (local refs, no fetch); node, npm, git, gh, and local Biome versions, the hook dependencies (bash, jq, curl), and any Node major mismatch against CI; `claude --version`; `plugin` and `marketplace` subcommands parsed from `--help`, with drift against the last session; open and latest resolved debt items; `npm run validate` and `claude plugin validate .` results; per-plugin release state against `{name}--v{version}` tags; and changelog bullets that mention hooks, plugins, marketplaces, skills, subagents, MCP, `settings.json`, `CLAUDE.md`, or frontmatter, taken from releases newer than the last one reported. Bullets for other surfaces (`[VSCode]`, `[Claude Tag]`, …) are skipped. A `systemMessage` shows warnings to the user. |
| `PreToolUse` | `Edit\|Write` | `guard-marketplace-catalog.sh` | Pure. Resolves the target path (`..`, symlinks), simulates the edit on `.claude-plugin/marketplace.json` with jq using literal `split`/`join` replacement, and returns `permissionDecision: "deny"` only if the `plugins` array would change. Other fields stay editable. |
| `PostToolUse` | `Edit\|Write` | `post-edit.sh` | Runs local `biome check --write` on the edited file; returns `decision: "block"` with the diagnostics when unfixable issues remain. For edits under `plugins/<name>/` whose current `version` is already tagged, adds a once-per-session reminder to bump the version, add a CHANGELOG entry, and tag the release with `claude plugin tag`. |

The changelog is fetched only from GitHub's raw `CHANGELOG.md` with `curl
--max-time 5` and cached for 24 hours. The dated docs page
(<https://code.claude.com/docs/en/changelog>) is linked in the output rather
than fetched too: both carry the same release notes. The GitHub file has no
dates, so the window is "releases newer than the last one reported" (the last
5 on the first run) rather than "last 30 days". Hook state lives in
`.claude/.cache/hooks/`, which the existing `.cache/` gitignore pattern
already covers.

The scripts run on bash 3.2 as well as bash 5.x (no `mapfile` or associative
arrays; BSD `awk`, `sed`, and `stat` compatible), so stock macOS works.

### Consequences

- Good, because each session starts with verified state, including CLI drift
  and upstream changes, without anyone asking for it.
- Good, because the generated-catalog rule and the format/lint rule are now
  enforced locally when Claude edits, instead of only in CI.
- Good, because the lifecycle failure mode "content changed, version not
  bumped, users never get it" is detected both at session start and at edit time.
- Bad, because contributors now need `jq` (and `curl` for the changelog). Without
  `jq`, all three hooks exit 0 as a no-op, and SessionStart says why.
- Bad, because `session-start.sh` spawns about 20 short subprocesses and may
  make one HTTP request. Measured cost is 2–3 s on the first run and faster once
  the changelog is cached, bounded by the 30 s hook timeout.
- Bad, because changelog entries count as "seen" once reported, even if the
  session that saw them is discarded.
- Neutral: PreToolUse and PostToolUse only see Claude's `Edit`/`Write` calls.
  A shell command or an external editor bypasses them; CI remains the
  authoritative gate.
- Neutral: `npm run check` and CI don't lint `.claude/hooks/*.sh` yet (DEBT-0003).

### Risks and mitigations

| Risk | Likelihood or condition | Impact | Mitigation or response | Owner |
| --- | --- | --- | --- | --- |
| `--help` output format changes and subcommand parsing breaks | CLI release reformats help | Empty lists in context | Section prints `UNAVAILABLE`; drift warning surfaces the change | Maintainer |
| GitHub raw URL unavailable or offline | Network failure | No fresh changelog | Falls back to stale cache and says so; never fails the hook | Maintainer |
| `biome check --write` rewrites a file mid-edit sequence | Every Edit/Write on a Biome-covered file | Claude's next edit sees changed content | Harness reports on-disk changes; formatting is deterministic and idempotent | Maintainer |
| Guard blocks a legitimate change | Someone needs a hand-edit of `plugins[]` | Blocked edit | By design: change `plugin.json` and run `npm run generate` | Maintainer |
| `jq` missing on a contributor machine | Fresh machine | Hooks silently no-op | SessionStart prints the reason; documented in CLAUDE.md | Maintainer |

### Confirmation

| Criterion or claim | Verification method | Evidence or result | Responsible party | Review condition |
| --- | --- | --- | --- | --- |
| Scripts are lint-clean | `shellcheck -x .claude/hooks/*.sh` with the user-wide rc (all optional checks), `shfmt -d` | rc=0 for both, 2026-09-18 | Maintainer | Any hook change |
| SessionStart emits valid JSON under the cap, detects drift, and windows the changelog | First run, cached second run, and simulated drift in a scratch clone, under bash 5.3.20 and 3.2.57 | Pass on both, 2026-09-18 (about 5.4 KB on first run) | Maintainer | Any change to `session-start.sh` |
| Guard denies `plugins[]` changes and allows everything else | Seven cases (Edit add, Edit other field, Write changed, Write other, unrelated file, `..` path, `replace_all`) under both bash versions | Pass on both, 2026-09-18 | Maintainer | Any change to the guard or catalog layout |
| Post-edit formats, blocks on unfixable lint, and reminds once per session | Seven cases (format fix, lint block, tagged plugin first/repeat/new session, bumped untagged, outside project) under both bash versions | Pass on both, 2026-09-18 | Maintainer | Any Biome major upgrade |
| Hooks load in a real session | `/hooks` menu lists all three; next session shows the snapshot | pending — first session after merge | Maintainer | After merge |

## Pros and Cons of the Options

### Bash hooks

- Good, because they keep Claude Code wiring separate from project wiring.
- Good, because the user-wide shell standard and linters apply (ShellCheck with every optional check, shfmt).
- Good, because they orchestrate existing tools (`claude`, `git`, local Biome, `node scripts/…`) rather than reimplementing them.
- Bad, because they add `jq`/`curl` as contributor dependencies, and JSON logic lives in jq programs.

### Node.js hooks

- Good, because they need no extra binaries beyond Node.
- Bad, because they mix harness wiring into the project's runtime and duplicate logic that belongs in the project's own scripts.

### No hooks

- Good, because there's nothing to maintain.
- Bad, because the state and rules above depend on Claude or the contributor remembering them; violations surface only in CI.

## More Information

- Hooks reference (matchers, SessionStart, PreToolUse and PostToolUse decision
  control, 10,000-character output cap): <https://code.claude.com/docs/en/hooks>
- Plugin lifecycle sections: installation scopes, caching and file resolution,
  version management, release channels, and tag-based dependency resolution.
  They are indexed in [CLAUDE.md](../../CLAUDE.md#reference-documentation).
- Changelog entries corroborated on 2026-09-18 (2.1.265–2.1.276). SessionStart
  hooks run in the background and Claude's first response waits for them
  (2.1.268, 2.1.271). `claude plugin eval` (2.1.269) and `--json` on plugin
  commands (2.1.268) are recent and not yet used here.
- Follow-ups in [pending-debt.md](../maintenance/pending-debt.md): DEBT-0001
  (official validator in the CI gate), DEBT-0002 (versioning misalignment),
  DEBT-0003 (shell hooks not linted in CI).
- Revisit when Claude Code changes SessionStart blocking semantics, the hook
  output cap, or plugin version resolution.

### Amendment — 2026-09-18: shell lint enforced by the hook; hooks removed from CLAUDE.md

- `post-edit.sh` now picks the linter by file kind. For `.sh` files, or files
  with an `sh`/`bash` shebang, it runs `shfmt -w` and then `shellcheck -x`
  (under the user-wide or repo rc), and returns `decision: "block"` with the
  findings. Everything else still goes through `biome check --write`. A
  missing `shfmt` or `shellcheck` adds a context note instead of failing.
  This replaces the CLAUDE.md instruction "after editing a hook, run
  shellcheck/shfmt". A rule that must always hold is enforced by a hook, not
  written as an instruction, because CLAUDE.md is context rather than
  enforced configuration ([memory docs](https://code.claude.com/docs/en/memory)).
  Verified under bash 5.3.20 and 3.2.57: misformatted-but-clean scripts are
  fixed silently, ShellCheck findings block (SC2086, SC2161), extensionless
  shebang scripts are detected, non-shell text is ignored, and the Biome and
  version-reminder paths are unchanged. The hook also blocked its own first
  draft, on SC2310.
- The "Project hooks" section was removed from CLAUDE.md. Hooks run from
  `settings.json` whether or not Claude knows about them. This ADR, the script
  headers, and `/hooks` are the documentation. The risk-table mitigation
  "documented in CLAUDE.md" for a missing `jq` now reads: SessionStart prints
  the reason.
- CI still doesn't lint shell scripts; DEBT-0003 stays open for that part.

### Amendment — 2026-09-18: post-edit also gates edits made through Bash

- Edits made with shell commands (`sed`, heredocs, scripts) bypassed the
  PostToolUse `Edit|Write` gate, so Biome and ShellCheck only caught them later
  in `npm run check` or CI. The matcher is now `Edit|Write|Bash`.
- A Bash tool call carries no `file_path`, so a new PreToolUse hook,
  `bash-stamp.sh` (matcher `Bash`), touches a per-session stamp in
  `.claude/.cache/hooks/` before each command. After the command,
  `post-edit.sh` lints every modified or new non-ignored repo file that is not
  older than the stamp (`git ls-files --modified --others --exclude-standard`).
  It uses the same shfmt + ShellCheck or `biome check --write` logic as for
  `Edit`/`Write`, aggregates all blocking findings into one `decision:
  "block"`, and caps a single command at 50 files.
- Same-second changes are kept (`! stamp -nt file`), because bash 3.2 compares
  whole seconds. Dirty files older than the stamp are left alone.
- Verified 2026-09-18 in a scratch clone under bash 5.3.20 and 3.2.57, for
  these cases, all passing:
  - no stamp yet means no action;
  - a dirty file older than the stamp is ignored;
  - JS written by a command is auto-formatted;
  - a shell script with a ShellCheck finding is blocked;
  - the `Edit` path is unchanged.
- Follow-up fix: `bash-stamp.sh` first shipped without the executable bit
  (git mode `100644`). Claude Code runs hook commands by path, so every call
  failed with exit 126, as a non-blocking error, and the Bash gate never fired.
  The scratch tests had missed it because they invoked the scripts through
  `bash`. With mode `100755`, the gate was verified live on 2026-09-18 in the
  running session: hook edits apply immediately. The stamp was written, and a
  file written through Bash was auto-formatted by Biome.
- Limits: a command that also commits its own edits (`git commit` in the same
  call) leaves nothing modified to find, and parallel Bash calls share one
  stamp. CI remains the authoritative gate (DEBT-0003 for shell).

- Resolved 2026-09-18 (DEBT-0003): `npm run check` and CI now lint every
  tracked shell script (`npm run lint:sh`, repo-local `.shellcheckrc`, pinned
  ShellCheck 0.11.0 and shfmt 3.14.1 in CI), so hook edits made outside
  Claude are gated too.

### Amendment — 2026-09-18: Biome at gate strictness in hooks; commit guard

- `post-edit.sh` now runs `biome check --write --error-on-warnings`. The gate
  (`npm run check`, CI) fails on warnings via `npm run biome:ci`. Before this
  change, a warning, such as a complexity limit, passed the edit hook and only
  failed later in CI.
- New `PreToolUse` hook `guard-commit-biome.sh` (matcher `Bash`). When a
  command runs `git commit`, including with global options such as
  `git -C <dir> commit`, it checks every file the commit could include with
  `biome check --error-on-warnings`, and denies the commit when anything
  fails. The file set is staged + modified + untracked non-ignored files,
  because at `PreToolUse` time a chained `git add … && git commit` hasn't
  staged anything yet. A dirty file with Biome issues therefore blocks the
  commit even if it wouldn't be committed. The hook is read-only. It fails
  closed: if `git` can't list files, the commit is denied rather than waved
  through unchecked.
- Verified under bash 3.2.57 and 5.3.20: non-commit commands are silent; a
  clean tree is allowed; a staged file deleted from disk is allowed; a
  complexity warning is denied; a `git` failure is denied (fail-closed).
  Temporary files are cleaned up.
- Limits: only commits made through Claude's Bash tool are checked. A human
  commit outside Claude isn't, and CI remains the authority. `npm run
  biome:staged` gives the same check by hand.


### Amendment — 2026-09-18: checklist gate for maintenance skills

- New `Stop` hook `checklist-gate.sh`, registered by a maintenance skill's
  frontmatter (`hooks:`), not by `.claude/settings.json`: Claude Code adds it
  for the rest of the session once the skill is invoked. The first user is
  `.claude/skills/plugin-release-review/`.
- The skill starts a checklist from its `checklist.json` template with
  `.claude/hooks/lib/checklist.sh`, and marks each item with evidence as it
  goes. While this session's checklist is in progress, the gate exits 2 and
  lists the open items, so the turn cannot end. Once every item is marked, it
  re-runs each item's `verify` command (for example `npm run validate`) and
  reopens failing items. Items marked `needs-user` let the turn end so the user
  can decide. Other sessions and finished checklists never block.
- Exit 2 was chosen over `hookSpecificOutput.decision` because it blocks a stop
  regardless of JSON placement. Claude Code lifts a Stop hook after eight
  consecutive blocks without progress (`CLAUDE_CODE_STOP_HOOK_BLOCK_CAP`), so a
  genuinely stuck checklist cannot loop forever.
- State lives in `.claude/state/checklists/` (gitignored). The gate never
  writes outside that folder. `scripts/lib/checklist-gate.test.mjs` covers:
  no checklist, another session, open items, a failing verify, completion,
  and an item waiting on the user.
- Limits: the evidence is text Claude writes, so the gate proves that each step
  was claimed and that the mechanical verifications pass, not that the
  judgment was good; the review itself remains the check on quality.

### Amendment — 2026-09-19: push guard and delivery checklist

- New `PreToolUse` hook (Bash) `guard-push-merged-branch.sh`, registered in
  `.claude/settings.json`. On `git push`, for each pushed branch that was
  published before (it has an upstream or a remote-tracking ref), it asks the
  remote with `git ls-remote --exit-code --heads`. If the remote answers that the
  branch is gone, which is what GitHub does after a merge, it denies the push.
  New branches, deletions, and tags pass. It is read-only, uses only `git`, and
  fails open when the remote can't be reached (exit 128), so it's a guardrail
  against recreating merged branches, not a control. Tests:
  `scripts/lib/push-guard.test.mjs`, under `bash` and `/bin/bash`.
- A second checklist skill, `.claude/skills/pr-delivery/`, registers the same
  `checklist-gate.sh` Stop hook. Its template verifies the finish of a change on
  the real remote: every plugin version is tagged on origin, the feature branch
  is deleted locally and on origin, `main` equals `origin/main`, and the tree is
  clean with `npm run validate` passing.
- `checklist-gate.sh` now exports the checklist's subject to verify commands as
  `$CHECKLIST_SUBJECT`. An item marked `needs-user` now lets the turn end even
  while other items are open, because later steps often depend on the answer
  (nothing after a merge can run before it is approved). The question is asked
  in the conversation, so this exit is visible to the user. `checklist.sh start` refuses while another checklist is
  in progress, so one skill can't silently drop another's gate.
- Limits: the delivery verifies need network access to `origin`, and while
  offline the gate keeps the items open until Claude Code's block cap. Merge and
  CI status are recorded as evidence, not re-run, so the hook needs no GitHub
  credentials.
- Fix, 2026-09-19: the gate read verify commands through jq `@tsv`, which
  escapes backslashes, so any command containing `\` failed with a bash syntax
  error inside the gate while passing when run by hand. The gate now reads each
  command verbatim by id. `checklist-gate.test.mjs` runs a command with
  backslashes and quotes through the gate, and checks that every committed
  `checklist.json` verify command parses with `bash -n`.

### Amendment — 2026-09-19: push guard renamed and gates direct pushes to main

- `guard-push-merged-branch.sh` is now `guard-push.sh`. It keeps the merged-branch
  check and adds a second one. On a push whose destination is `main`, it denies
  the push unless the working tree is clean, `npm run check:versions` reports
  `bump: none` (runtime changes go through a PR, ADR-0003 amendment of the same
  date), and `npm run check` passes. It runs only on pushes to `main`, and its
  timeout is 300 s because `npm run check` takes about a minute.
- The gate commands can be replaced only through the hook's own environment
  (`GUARD_PUSH_VERSIONS_CMD`, `GUARD_PUSH_CHECK_CMD`), which the tests use; the
  command Claude runs can't change them. `scripts/lib/push-guard.test.mjs`
  covers a clean pass, a runtime change, failing version rules, a failing check,
  and a dirty tree.
