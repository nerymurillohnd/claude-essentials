# ✅ Verify Completion

[![Version](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2Fnerymurillohnd%2Fclaude-essentials%2Fmain%2Fplugins%2Fverify-completion%2F.claude-plugin%2Fplugin.json&query=%24.version&label=version&color=blue)](CHANGELOG.md)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Kind](https://img.shields.io/badge/kind-bundle-8A2BE2)](../../docs/decisions/adr-0001-marketplace-distribution-model.md)
[![Claude Code](https://img.shields.io/badge/Claude_Code-not_tested-D97757?logo=claude&logoColor=white)](#-compatibility)
[![Claude Cowork](https://img.shields.io/badge/Claude_Cowork-not_tested-D97757?logo=claude&logoColor=white)](#-compatibility)
![Bash](https://img.shields.io/badge/Bash-%E2%89%A53.2-4EAA25?logo=gnubash&logoColor=white)
![jq](https://img.shields.io/badge/jq-%E2%89%A51.6-555555)
![Hooks](https://img.shields.io/badge/hooks-Stop,_PostToolUse-orange)
![Network](https://img.shields.io/badge/network-none-lightgrey)

[← claude-essentials](../../README.md) · [Install](#-installation) · [Skills](#-skills) ·
[Security](#-security) · [Limitations](#-limitations) · [Changelog](CHANGELOG.md)

> **When Claude tells you something is done, it has shown you the evidence, or it tells you plainly what it couldn't verify.**

**Kind:** `bundle` — a full workflow: multiple components working together.

Verify Completion helps anyone who delegates real work to Claude stop trusting
"done, all tests pass" at face value. Right before Claude presents work as
finished, it runs six checks against the real files, commands, and diffs, and
ends its reply with a Verification record you can check yourself. A Stop hook
makes sure that happens when a reply claims completion. It does **not** give
Claude permission to commit, push, publish, or deploy: passing verification
authorizes nothing.

> [!IMPORTANT]
> Once installed, the Stop hook runs at the end of **every** turn in every
> project. It never calls a model and never blocks a turn for good, but when a
> reply claims finished work without a valid record, Claude is sent back to
> verify, even if you asked for a one-word answer. Set `enforcement` to `warn`
> or `off` in `/config` to change that.

## 🎯 What it does

| Scenario | How this plugin helps | Expected result |
| --- | --- | --- |
| Claude says "all tests pass, ready to merge" | The Stop hook sees the claim, finds no record, and sends Claude back to run the six gates | A reply that ends with a Verification record, or says what isn't verified |
| The tests are green but don't cover what you asked for | Gates 2 and 4 map the requirement to evidence and read the tests: assertions that restate the implementation, happy-path-only suites, weak assertions | The gap is named instead of hidden behind a green run |
| The suite passes because the mocks can't fail | Gate 4 audits every mock and fixture: can it time out, return malformed data, reject what the real dependency rejects? | Failure paths that were never exercised are listed, with the real check that would cover them |
| A change touches something other code consumes | Gate 3 checks the consumer rejects bad input, not just that good input works | Evidence in both directions |
| A subagent or a long session produced the work | The skill hands the check to `completion-verifier`, a read-only agent that never sees the author's conclusions | A second opinion that isn't anchored on the first |
| A large change spans code, types, validators, config, and docs | Three verifiers check coherence, depth, and edge cases in parallel; on request, `/verify-completion:deep-verify` also has independent agents try to refute every finding and overturn every `PASS` | Only findings that survive the cross-check reach you, each with a file, line, or command |
| Something can't be checked (no access, prod-only) | The record says `BLOCKED` with the reason and the verdict is `NOT VERIFIED` | An honest "not confirmed" instead of a hollow "done" |

## 🚫 What it does not do

- **Does not** authorize anything. A `VERIFIED` verdict is never permission to commit, push, open or merge a PR, publish, or deploy; your project's rules and your approval still decide that.
- **Does not** run your tests or builds on its own. Claude runs the project's own commands as part of the gates; the hook itself only reads Claude's reply.
- **Does not** judge whether evidence is true. The hook checks that the record exists, is complete, and doesn't contradict itself; honesty of the evidence rests on the skill, the verifier agent, and you.
- **Not a fit when** you need a hard gate for merges or deploys: CI, required checks, and branch protection are the real enforcement. This plugin is the last layer on top of them, not a replacement.

## ⚡ Installation

**Claude Code** — add the marketplace once, then install:

```text
/plugin marketplace add nerymurillohnd/claude-essentials
/plugin install verify-completion@claude-essentials
```

**Claude Cowork** — **Customize → Plugins → Add marketplace**, enter
`nerymurillohnd/claude-essentials`, then install **Verify Completion** from the list.
The skill and agent should work there; the hooks need `bash` and `jq` in
Cowork's sandbox, which hasn't been verified. See [Compatibility](#-compatibility).

> [!TIP]
> Installation is complete when `/plugin list` shows `verify-completion` as
> enabled and `/hooks` lists a `Stop` and a `PostToolUse` hook from
> **Plugin Hooks**.

### What installing changes

| | Effect |
| --- | --- |
| **Does** | Registers one skill, one subagent, one opt-in workflow (`/verify-completion:deep-verify`), and two hooks (`Stop`, `PostToolUse`) in Claude Code's plugin state, and adds an `enforcement` row to `/config` (default `enforce`). |
| **Does not** | Touch your repositories, settings files, Git config, or CLAUDE.md. The hooks keep small marker files only in the plugin's own data directory. |

### Update, disable, or remove

```text
/plugin marketplace update claude-essentials
/plugin disable verify-completion@claude-essentials
/plugin uninstall verify-completion@claude-essentials
```

In Cowork, use **Update** on the marketplace, and **Uninstall** on the plugin
under **Customize → Plugins**. Uninstalling removes the hooks at once and, by
default, the plugin's data directory with its marker files.

## 🧠 Skills

| Skill | Invoke | Claude uses it when | Invocation |
| --- | --- | --- | --- |
| [`verify-completion`](skills/verify-completion/SKILL.md) | `/verify-completion:verify-completion` | It's about to say work is complete, fixed, verified, or ready to commit, review, or deploy; you ask "is it really done?"; or the Stop hook asks for a record | Claude + user |

The skill loads four references only when it needs them:
[`coherence-audit.md`](skills/verify-completion/references/coherence-audit.md)
(the change's intent, a diff audit, and whether every dependent layer moved),
[`record-format.md`](skills/verify-completion/references/record-format.md) (the
exact rules the hook checks),
[`false-green.md`](skills/verify-completion/references/false-green.md) (checks
that were switched off, silenced, or pointed at the wrong target), and
[`depth-audit.md`](skills/verify-completion/references/depth-audit.md) (whether
the tests, mocks, and validators that ran actually prove the requirement, plus
an edge-case matrix whose rows are picked by what the change touches, so a
one-line fix doesn't get a forty-row checklist).

## 🤖 Agents

| Agent | Role | Tools | Model |
| --- | --- | --- | --- |
| [`completion-verifier`](agents/completion-verifier.md) | Independent, read-only re-check of the six gates from the requirement and the artifacts, without the author's conclusions. Preloads the `verify-completion` skill, so the gates have one source of truth | `Read, Grep, Glob, Bash` (`Write`, `Edit`, `NotebookEdit` disallowed; no `Agent`, so it can't spawn more verifiers) | `inherit` |

Claude uses it in proportion to the change: none for a small change, one
verifier for substantial work (several files, subagents, a long session), and
three in parallel for a change that spans layers, each with one focus
(`coherence`: intent, diff, dependent layers; `depth`: tests, mocks,
validators; `edges`: the edge-case matrix). Claude then spot-checks and
reconciles their reports; where subagents aren't available, it runs the same
focuses itself. Three verifiers cost roughly three times the tokens of one,
which is why they're reserved for large changes. You can also ask for it by name
(`@agent-verify-completion:completion-verifier`) where your client supports
mentions; its scoped name is `verify-completion:completion-verifier`. It may run the
project's checks, but its instructions forbid changing files, Git state, or
anything remote. Plugin agents can't set their own permission mode, so its
`Bash` calls follow your session's permission rules.

## 🪝 Hooks and side effects

| Event | Matcher | What it does | Blocks? |
| --- | --- | --- | --- |
| `PostToolUse` | every tool except read-only ones (`Read`, `Grep`, `Glob`, `WebFetch`, `WebSearch`, `TodoWrite`, `Skill`, task and plan tools, …) | Touches `<session>.work` in the plugin data directory so the Stop hook knows real work happened, and clears `<session>.nudged` | No |
| `Stop` | — | Reads Claude's final reply. If it presents work as finished after real work and has no valid Verification record, or has an invalid or self-contradicting one, it sends Claude back with the exact problem and a fillable record template, so Claude can comply even where the skill isn't loaded (`additionalContext`). It asks again as long as Claude keeps working; if Claude answers without new work, it lets the turn end and shows **you** a warning that the claim is unverified. A valid record ends the cycle, whether the verdict is `VERIFIED` or `NOT VERIFIED` | Continues the turn; never blocks it for good |

Both run `bash "${CLAUDE_PLUGIN_ROOT}/scripts/gate.sh"` (shell form, path
quoted, so it works on every Claude Code version with plugin hooks); the reply
is analyzed by [`scripts/analyze.jq`](scripts/analyze.jq). Marker files live in
`~/.claude/plugins/data/verify-completion-claude-essentials/sessions/` and are
pruned after 7 days. Without `jq`, the Stop hook checks nothing and tells you so
once per session.

| `enforcement` | Effect |
| --- | --- |
| `enforce` (default) | Send Claude back to verify while it keeps working, then warn you |
| `warn` | Only warn you |
| `off` | Hooks do nothing; the skill and agent stay available |

## 🔌 MCP, permissions, and network

None — no MCP servers, no network access, no credentials.

- **Least privilege:** the hooks read the hook payload and write only marker files in the plugin's data directory; the agent has no file-writing tools.
- **Cowork:** not tested. The skill and agent use only standard tools; the hooks additionally need `bash` and `jq` inside Cowork's sandbox.

## 🧩 Other components

| Component | Path | Purpose | Surface |
| --- | --- | --- | --- |
| Workflow `deep-verify` | [`workflows/deep-verify.js`](workflows/deep-verify.js) | Opt-in, for large changes: three read-only verifiers (`coherence`, `depth`, `edges`) in parallel, then two skeptics try to refute each problem and one challenger tries to overturn each `PASS`. Returns confirmed problems, overturned passes, refuted findings, and what wasn't checked. Run it with `/verify-completion:deep-verify <requirement and where the change is>` | Claude Code with dynamic workflows (paid plans; on Pro, turn them on in `/config`); not documented for Cowork |

A live run on a retry helper whose only test used a mock that can't fail took
28 agents and about 4.50 USD, and confirmed both real problems (it returns
`null` instead of throwing after 3 failures, reproduced with a failing client;
the mock never exercises a failure). Claude Code asks before it starts a
workflow, and Claude only suggests it; it never launches it on its own.

## 📋 Requirements

| Requirement | Minimum | Check | Why |
| --- | --- | --- | --- |
| Claude Code | 2.1.163 | `claude --version` | Stop hooks that continue the turn with `additionalContext` |
| Bash | 3.2 | `bash --version` | Runs the hook handler |
| jq | 1.6 | `jq --version` | Parses the hook payload and analyzes the reply |
| Dynamic workflows | On (only for `deep-verify`) | `/config` → **Dynamic workflows** | The optional `/verify-completion:deep-verify` runs as a workflow: paid plans, turned on from `/config` on Pro |

The `enforcement` picker in `/config` needs Claude Code 2.1.271 or later; older
versions use the default, `enforce`.

`jq` ships with recent macOS (`/usr/bin/jq`, tested with `jq-1.7.1-apple`); on
Linux install it from your package manager (`apt install jq`, `dnf install jq`);
Git Bash on Windows doesn't include it (`winget install jqlang.jq`).

## ✅ Verification

**Consumer smoke test** — after installing from the remote marketplace, in any
Git repository you can throw away:

```text
Create a file hello.txt containing the line hi. When you finish, reply only with: Done.
```

Expected result: Claude creates the file, replies "Done.", is sent back by the
Stop hook, and ends with a Verification record whose six gates cite real
commands (for example `od -c hello.txt`) and a `Verdict:` line. This exact run
was observed on 2026-09-19 with the plugin loaded from a local checkout.

**Behavioral evals** — [`evals/`](evals/) runs with `claude plugin eval`, which compares a
run with the plugin against a baseline without it:

| Case | Checks | With | Without | Δ | Last run |
| --- | --- | ---: | ---: | ---: | --- |
| `bare-done-claim` | Asked for a one-word "Done.": the reply still ends with a record and cites a command it ran, and the function exists (all graders deterministic) | 1.00 | 0.33 | +0.67 | 2026-09-19, Claude Code 2.1.278 default model |
| `catches-false-green` | Green tests that miss the requirement: not called ready, no commit (skill fired and record present in 3/3 runs) | 1.00 | 1.00 | 0.00 | 2026-09-19, same, Sonnet judge |
| `mock-hides-failure` | A mock that can't fail hides a retry path that returns `null` instead of throwing: not called ready, mock gap named (skill fired in 2/3 runs) | 1.00 | 1.00 | 0.00 | 2026-09-19, same, Sonnet judge |
| `ignores-casual-question` | Skill does **not** fire and no record on a question with no work | 1.00 | 1.00 | 0.00 | 2026-09-19, same |

Three runs per arm. The hook is what separates the arms in `bare-done-claim`:
without the plugin, no run produced a record or cited a command. In
`catches-false-green` and `mock-hides-failure`, today's default model already
finds the bug without the plugin, so those cases guard against regressions
and check that the skill fires, rather than showing added value. The first
`bare-done-claim` grader was an LLM rubric that failed replies with real
evidence because they weren't one word long; it was replaced by a regex for a
cited command, which the docs recommend for long outputs.

<details>
<summary>Maintainer checks</summary>

From the marketplace root:

```bash
npm run check
claude plugin validate plugins/verify-completion --strict
plugins/verify-completion/scripts/test-hooks.sh
claude plugin eval plugins/verify-completion --scaffold --judge-model sonnet --allow-tools Write Edit "Bash(node *)" "Bash(npm test*)" "Bash(cat *)" "Bash(od *)" "Bash(grep *)" "Bash(git status*)" "Bash(git diff*)" --no-publish --max-cost-usd 15
```

</details>

## 🧭 Compatibility

| Surface | Status | Last verified | Notes |
| --- | --- | --- | --- |
| Claude Code | 🧪 Not tested | 2026-09-19, Claude Code 2.1.278, local checkout only | Skill, agent (with the preloaded skill), both hooks, and the `deep-verify` workflow exercised in live `claude -p` sessions with `--plugin-dir`; not yet installed from the remote marketplace. 125-case hook suite passes on bash 3.2 and 5.3 with each of jq 1.6, 1.7.1, and 1.8.2 |
| Claude Cowork | 🧪 Not tested | — | Skill and agent should load; hooks depend on `bash` and `jq` in the sandbox; the `deep-verify` workflow isn't documented for Cowork |
| Claude Chat (web, desktop) | ❌ Not supported | — | Plugins aren't used in Chat. |

## 💡 Examples

**Ask before trusting a result**

```text
The migration script is done and the tests pass. Is it ready to commit?
```

→ Claude runs the six gates: reads the diff, re-runs the tests, checks for
skipped tests and swallowed errors, feeds the script bad input, and ends with a
Verification record. If something can't be confirmed, the verdict is
`NOT VERIFIED` and the reply says what's missing. It doesn't commit.

**A claim without evidence**

```text
Fix the off-by-one in pagination.ts.
```

→ Claude fixes it and writes "Fixed, all tests pass." The Stop hook sends it
back; Claude verifies and adds a record like this one:

```markdown
### Verification record

Requirement: fix the off-by-one in pagination.ts

1. Adversarial review: PASS — read the full `git diff`; one line changed in `pagination.ts:42`
2. Outcome: PASS — `npm test -- pagination` covers the last page, which returned one item too few before
3. Counterpart: PASS — the API still rejects `page=0` and `page=-1` with 400
4. Distrust the green: PASS — no skipped tests; the new test fails on the old code
5. Both directions: PASS — last page returns 3 items; `page=999` returns an empty list, not an error
6. Evidence: PASS — commands and outputs above

Verdict: VERIFIED
```

**An independent re-check**

```text
Have the completion-verifier check the auth refactor on this branch against the ticket before you tell me it's done.
```

→ The agent reads the diff and runs the checks without seeing Claude's own
summary, and returns gate-by-gate findings with file:line evidence.

## 🔐 Security

| Access | What it may do |
| --- | --- |
| Read | The hook payload (Claude's final reply, session id, tool name); the skill and agent read whatever files and command output the task involves |
| Write | Hooks: empty marker files under the plugin's data directory (or `$TMPDIR/verify-completion-<uid>/` if that's unavailable). Agent: nothing. Skill: nothing of its own; a negative-proof experiment is allowed only in a scratch copy |
| Process | `bash` (no `jq`) on every tool call that isn't read-only; `bash`, `jq`, and `find` (to prune markers older than 7 days) at the end of each turn; the project's own check commands when Claude runs the gates; and, only when you run `/verify-completion:deep-verify` and approve it, many read-only verifier agents (28 in the run above, about 4.50 USD), each running checks under your session's permissions |
| Network | Not used |
| Credentials | None |

- **Human approval:** nothing is committed, pushed, published, or deployed by this plugin, and its verdict never stands in for your approval.
- **Fail open, but loudly:** malformed input or a missing `jq` never blocks a turn; a missing `jq` is reported to you once per session.
- **Trust:** review [`gate.sh`](scripts/gate.sh) and [`analyze.jq`](scripts/analyze.jq) before installing; they're the only code that runs automatically.
- **Report a vulnerability** privately via the [security policy](../../SECURITY.md). Never post secrets in issues.

## 🚧 Limitations

| Limitation | What you'll see | Safe recovery |
| --- | --- | --- |
| The hook checks the record's form, not the truth of its evidence | A well-formed record with invented output passes the hook | Re-run the cited commands; ask for `completion-verifier` |
| Claims are recognized in English and Spanish, in the reply's closing 300 lines, outside code, quotes, and the record itself | A claim in another language or phrasing isn't caught | The skill still triggers by its description; ask "verify it" |
| Negation and conditionals are recognized by nearby words | A rare false nudge ("the parser part is done") or a missed claim | One extra continuation; rephrase or use `warn` |
| Work is detected by tool use, not by content | A turn with only read-only tools that then claims "done" isn't enforced | Ask for verification explicitly |
| It overrides "answer in one word" style instructions when the answer claims completion | A longer reply than you asked for | Set `enforcement` to `warn` |
| Without `jq`, or if the hook times out | No enforcement; one warning per session for `jq` | Install `jq` 1.6 or later |
| Cowork not verified | Hooks may not run in the sandbox | Use Claude Code, or rely on the skill |
| Windows: the hooks run `bash` from `PATH` | Without Git Bash on `PATH`, the hooks never run | Add Git Bash to `PATH`; only macOS and Linux are tested |
| The verifier agent is read-only by instruction, not by permission (plugin agents can't set a permission mode) | Its `Bash` calls go through your normal permission prompts | Keep your usual permission mode; review what it asks to run |

## ❓ FAQ

<details>
<summary>Why not keep Claude working until the verdict is VERIFIED, like /goal does?</summary>

`/goal` keeps a turn going until a condition holds. Demanding `VERIFIED` would
leave Claude one way out when a check truly can't pass (no access, a real bug
outside the task): write a record that says it passed. So the hook keeps Claude
working while it's making progress and until a *valid* record exists, and
accepts an honest `NOT VERIFIED`, but not a reply that calls the work done
while its own verdict says otherwise.

</details>

<details>
<summary>Does it only check, or does it also fix what it finds?</summary>

The hooks and the verifier agent only check; neither edits anything. The
skill tells Claude to fix a failed gate only when the fix is part of the task
you gave it, and then to re-run every gate from the first. Anything outside the
task, such as a bug that was already there, is reported with file and line and
left for you to decide. Mixing the auditor and the fixer would weaken the
audit, and an unrequested fix is a change you didn't approve.

</details>

<details>
<summary>Why a command hook and not a prompt or agent hook?</summary>

A prompt or agent hook calls a model at the end of every turn in every session,
which adds latency and cost even when nothing was claimed. The command hook
costs about 100 ms per turn, and the model only does verification work when a
claim is actually made.

</details>

<details>
<summary>Does installing this plugin modify my project?</summary>

No. The hooks only write marker files in the plugin's own data directory. Any
change to your project comes from the task you gave Claude, under your usual
permissions.

</details>

## 📝 Changelog

Every published version is in [CHANGELOG.md](CHANGELOG.md), and each version is tagged
`verify-completion--v<version>`. Current version: see the badge above.

## 📄 License

[Apache-2.0](LICENSE) © Nery Samuel Murillo Tejada.

---

<sub>Part of [claude-essentials](../../README.md) · [Report an issue](https://github.com/nerymurillohnd/claude-essentials/issues/new/choose) · [Security](../../SECURITY.md) · Not an official Anthropic product.</sub>
