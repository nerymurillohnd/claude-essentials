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
