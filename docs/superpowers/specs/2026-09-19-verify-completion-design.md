# verify-completion plugin — design

- **Date:** 2026-09-19
- **Status:** built from the maintainer's `/goal` brief; component plan
  decisions confirmed by the maintainer on 2026-09-19 (size-scaled verifier
  orchestration, `enforce` as the default mode, one skill + one agent +
  references). Repository tooling from this work landed on `main` in 37ac3e5
  (Knip MCP server, discovery of new scripts, DEBT-0013); the plugin ships
  through its own PR.
- **Kind:** `bundle` ([ADR-0001](../../decisions/adr-0001-marketplace-distribution-model.md))
- **Reference consulted, not copied:** `codex-essentials/plugins/verify-completion`
  1.0.0 (a skills-only, advisory six-gate protocol for Codex)

## Goal

When an agent is about to present work as complete, correct, verified, ready to
hand off, ready to commit, or ready for review, and not before, it must run
six checks in order and leave evidence someone else can review:

1. **Adversarial review:** re-inspect the real files, outputs, and diffs; treat
   its own summary and any subagent's report as claims, not proof.
2. **Outcome:** the path that actually ran is exactly the one that was asked for.
3. **Counterpart:** where something consumes the work, show that it rejects
   incomplete, wrong, or malicious input.
4. **Distrust the green:** look for disabled, skipped, or weakened checks,
   untested paths, swallowed failures, and tests that only prove their mocks.
5. **Both directions:** what should work works, and what should fail fails.
6. **Evidence:** leave it where the user can reach the same conclusion without
   trusting the summary.

Passing is **never** authorization to commit, push, publish, deploy, or change
anything permanently. A check that can't be completed is reported as a
limitation with its exact reason, and then the work is not called done.

## Why not a port of the Codex reference

The reference is one advisory skill. Whether it runs depends on the model
choosing to load it at the right moment, which is exactly the habit the
maintainer does not trust. Claude Code has three mechanisms Codex's version
does not use, and each one closes a specific gap:

| Gap in an advisory skill | Claude Code mechanism | Component |
| --- | --- | --- |
| Nothing makes the protocol run when the claim is made | `Stop` hooks see the final reply (`last_assistant_message`) and can keep the turn going (`hookSpecificOutput.additionalContext`) | `gate.sh stop` |
| "Not on every intermediate step" is left to judgement | `Stop` fires only when Claude ends its turn; `PostToolUse` can record whether any work happened | `gate.sh mark` + `gate.sh stop` |
| Gate 1 asks the same context that did the work to review it | A plugin subagent starts with a fresh context and receives no conclusions | `completion-verifier` agent |
| Gate 6 evidence is free-form, so its absence is invisible | A fixed, machine-checkable record the hook validates | Verification record format |

## Verified constraints (live docs + changelog, 2026-09-19, Claude Code 2.1.278)

| Fact | Source | Design consequence |
| --- | --- | --- |
| `Stop` input carries `last_assistant_message`, `stop_hook_active`; the transcript may lag the final message | [hooks](https://code.claude.com/docs/en/hooks#stop-input) | Read the reply from the input, never from `transcript_path` |
| `Stop` can return `hookSpecificOutput.additionalContext` to continue the turn without it being labeled a hook error (added 2.1.163) | hooks, changelog 2.1.163 | The nudge uses `additionalContext`, not `decision: block` |
| Claude Code ends the turn after 8 consecutive Stop blocks | hooks, changelog | A second safety net; the gate itself nudges at most once per unit of work |
| Prompt and agent hooks run a model call on every event they match | hooks | Rejected for the gate: an LLM call on every turn costs latency and money in every session. A deterministic command hook decides; the model does the verification only when it is actually needed |
| `userConfig` options are exported to hooks as `CLAUDE_PLUGIN_OPTION_<KEY>`; `options` gives a `/config` picker (2.1.271+) | [plugins-reference](https://code.claude.com/docs/en/plugins-reference#user-configuration) | `enforcement` = `enforce` \| `warn` \| `off`, read from the environment |
| Hook matchers with other characters are JavaScript regular expressions | hooks | `PostToolUse` uses a negative lookahead to skip read-only tools |
| Exec form (`args`) is recommended for path placeholders, but only exists since 2.1.139 | hooks, changelog 2.1.139 | Shell form with the placeholder in double quotes (also documented). On an older version `args` would be ignored and a bare `bash` would read the payload, Claude's reply included, from stdin as a script |
| Plugin subagents ignore `hooks`, `mcpServers`, `permissionMode` | [sub-agents](https://code.claude.com/docs/en/sub-agents) | The verifier is read-only by `tools` + `disallowedTools` and by instruction; it inherits the session's permission mode |
| Skill frontmatter outside the Agent Skills spec can break packaging on claude.ai surfaces (Cowork) | [skills](https://code.claude.com/docs/en/skills) | `SKILL.md` frontmatter is `name` + `description` only |
| Cowork installs plugins with skills, agents, and hooks | [Cowork plugins](https://claude.com/docs/cowork/guide/plugins) | Skill and agent are expected to work; the hooks need `bash` and `jq` in Cowork's sandbox, which is **not verified** — Cowork is marked 🧪 |

## Decisions

1. **Enforcement is a command `Stop` hook, not a prompt or agent hook.** It
   costs about 100 ms per turn (process start-up: bash plus three jq calls) and
   never calls a model. It checks form and
   consistency; the substance comes from the skill and, when used, the
   verifier agent. The README says so plainly: the hook can prove a record
   exists and is internally consistent, not that its evidence is true.
2. **"Not before" is enforced three ways.** The gate only looks at the reply
   that ends a turn; it only reacts to a completion claim; and it only
   enforces after work happened (a mutating tool ran) since the last valid
   record. A pure Q&A turn is never nudged.
3. **Keep going while there is progress (like `/goal`), never demand
   `VERIFIED`.** A claim without a valid record gets an `additionalContext`
   nudge. New work (a non-read-only tool call) re-arms the nudge, so Claude is
   sent back as long as it keeps working; a reply with no new work and still no
   valid record ends the turn with a `systemMessage` telling the **user** the
   claim is unverified. Claude Code's 8-continuation cap is the outer bound.
   Any valid record ends the cycle, `NOT VERIFIED` included: demanding
   `VERIFIED` would leave faking it as the only exit when a gate truly can't
   pass, which is the failure this plugin exists to prevent.
4. **Machine-checkable record, human-readable.** Fixed tokens (`PASS`,
   `FAIL`, `N/A`, `BLOCKED`, `VERIFIED`, `NOT VERIFIED`), prose in any
   language, heading in English or Spanish. `VERIFIED` requires gates 1, 2, 4,
   and 6 to be `PASS` (they always apply), gates 3 and 5 to be `PASS` or `N/A`
   with a reason, a stated requirement, and at least one code span or block
   (a command, path, or output someone can re-run or open). `NOT VERIFIED` is
   acceptable if well formed, unless the rest of the reply still calls the work
   finished: honesty is never blocked, a contradiction is.
5. **Fail open, loudly where possible.** Malformed input or a missing `jq`
   never blocks a turn (a stuck `Stop` hook is worse than a missed check). A
   missing `jq` is reported to the user once per session.
6. **Claim detection is English + Spanish**, skips code blocks, quotes,
   questions, the record itself, and negated or conditional phrasing ("not
   ready", "no está listo", "if it works"). Other languages are not detected;
   the skill still triggers by its description. Documented as a limitation.
   jq compiles a regex on every call, so the reply gets one combined test and
   only its closing 300 lines are scanned, stopping at three claims: the worst
   adversarial 270 KB reply takes about 1.5 s (first draft: 8 s; hook timeout
   10 s).
7. **State** lives in `${CLAUDE_PLUGIN_DATA}/sessions/` (fallback
   `${TMPDIR}/verify-completion-<uid>/`), one marker per session for "work
   since last record" and one for "already nudged"; files older than 7 days
   are pruned by the gate.
8. **Independent verifier** (`completion-verifier`): `Read`, `Grep`, `Glob`,
   `Bash`; `Write`, `Edit`, `NotebookEdit` disallowed. It gets the requirement
   and where to look, never the main agent's conclusion, and returns gate
   findings with evidence. The skill requires it for work produced by
   subagents, multi-file changes, and long sessions, and treats its report as
   a claim to spot-check, too.
9. **Authority boundary is stated in every artifact:** skill, agent, hook
   messages, README. The record carries no authorization field on purpose.

10. **One skill, one agent, several references** (maintainer-confirmed). There
    is one trigger moment, so several skills would compete on their
    descriptions and the hook couldn't name the right one; references give the
    same modularity and load only when a gate needs them. One agent with a
    `focus` (`all`, `coherence`, `depth`, `edges`) keeps a single copy of its
    hard rules. The skill scales it to the change: none for a small change, one
    verifier for substantial work, three in parallel for a change that spans
    layers.
11. **Opt-in `deep-verify` workflow** (maintainer-approved after an evaluation
    of every orchestration option against live docs). Correction: an earlier
    draft claimed workflows aren't a plugin component; plugins do ship them in
    `workflows/`. It adds the one thing the in-skill path can't: every finding
    refuted by two independent skeptics and every `PASS` challenged once, with
    schema-bound outputs. It is opt-in (Claude suggests it for large changes;
    it runs only on request, with Claude Code's approval prompt) because it
    costs many agents (28, about 4.50 USD, in the live run) and needs dynamic
    workflows (paid plans; not documented for Cowork). Rejected with reasons:
    `context: fork` (loses the conversation that defines the requirement),
    several skills (compete for one trigger), skill-scoped hooks (the gate must
    act when the skill wasn't invoked), per-audit hooks (one checkpoint is
    enough), agent teams (experimental, off by default, interactive only), and
    a `SubagentStop` check on the verifier (low value; reports can arrive via
    `SubagentHandback`). The verifier preloads the skill (`skills:`), verified
    both ways live, so the gates have one source of truth.

## Non-goals

- Does not run tests, linters, or builds by itself; the project's own
  commands are the evidence.
- Does not commit, push, deploy, publish, or approve anything, ever.
- Does not replace code review, formatters, Git guards, CI, or branch
  protection; it is the last layer on top of them.
- Does not judge whether evidence is true; it forces it to exist, be
  specific, and be consistent.

## Failure modes

| Failure | Behavior |
| --- | --- |
| `jq` missing | Gate and marker exit 0; one `systemMessage` per session says claims aren't being checked |
| Malformed hook input | Exit 0 (fail open) |
| State directory not writable | Treat as "work happened"; nudge only when `stop_hook_active` is false |
| Hook timeout (10 s) | Claude Code treats it as non-blocking; measured runtime is far below |
| Claim in an undetected language or phrasing | Not enforced; skill description still triggers |
| Model writes a well-formed record with false evidence | Not detectable by the hook; mitigated by the verifier agent and by requiring re-runnable evidence |
| Cowork sandbox without `bash`/`jq` | Hooks inactive there; skill and agent still usable |

## Findings during the build

- **Empty stdin read as a claim.** jq printed nothing, the fields read as
  empty, and an empty claim count compared unequal to `0`. The gate now
  validates the analyzer's output and fails open. Test: "empty stdin fails open".
- **jq 1.6 and 1.7 compile errors.** `capture(...)?.field` is jq 1.8 syntax and
  `end` is a reserved word in jq 1.6. Rewritten; the suite passes on jq 1.6
  (built from the release tarball), 1.7.1 (release binary), and 1.8.2. CI only
  runs the runner's jq, recorded as debt.
- **The repo runner skips untracked suites.** `npm test` discovers
  `plugins/**/test-*.sh` with `git ls-files`, so the suite ran in CI only once
  committed; confirmed with `git add -N`.
- **Live session** (`claude -p --plugin-dir`, 2.1.278): a forced "Done." reply
  was sent back, the first record was rejected as incomplete, and Claude then
  ran real checks and closed with a valid record. In a second run the skill
  fired on its own before any claim.

- **Independent reviews** (code, skill, structure; none saw this design):
  a fenced block inside the record (for example `node --test` output, whose
  lines start with `#`) ended the record early and a valid record was rejected;
  "I'm done" was not recognized; a plain prose line starting "Verification
  record" hijacked the record; indented numbered sub-lists counted as gates;
  `Requirements:` and `Verdict — Verified` were rejected; and honest partial
  results in a `NOT VERIFIED` reply were flagged as contradictions. Each has a
  failing test first, then the fix; the contradiction check now uses only
  whole-work claims. Windows without Git Bash on `PATH` is documented.

- **Release review:** hooks moved from exec form to shell form with the
  placeholder quoted (exec form needs 2.1.139; on older versions a bare
  `bash` would read the payload as a script). A live run with the `Skill`
  tool denied showed Claude can't produce a valid record without the format,
  so both nudges now carry a fillable template (tested: the filled template
  validates). Typical latency re-measured at about 100 ms.
- **Depth audit (maintainer request):** the maintainer's list of test, mock,
  validator, and edge-case checks became `references/depth-audit.md`, wired
  into gates 3–5 and the verifier agent. Edge-case rows are chosen by what the
  change touches and every skipped row needs a reason, so the list stays
  universal without turning a one-line fix into a forty-row checklist. The
  hook still checks only the record's form; the substance is enforced by the
  skill and the context-free verifier.

## Verification plan

- `scripts/test-hooks.sh`: behavioral suite for both hook scripts, run by
  `npm test` under `bash` and `/bin/bash` 3.2: claim detection (EN/ES,
  negation, questions, code blocks), record validation (every rule, both
  verdicts), modes, work marker, nudge-once, missing `jq`, malformed input,
  timing.
- `npm run check`, `claude plugin validate --strict`.
- A live session with `--plugin-dir` to confirm the hooks load and the nudge
  reaches Claude.
- `claude plugin eval` suite: triggers on a completion request, does not
  trigger on an intermediate step, produces a record rather than an
  unbacked claim.
