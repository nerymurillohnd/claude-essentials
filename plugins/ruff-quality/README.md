# 🐍 Ruff Quality

[![Version](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2Fnerymurillohnd%2Fclaude-essentials%2Fmain%2Fplugins%2Fruff-quality%2F.claude-plugin%2Fplugin.json&query=%24.version&label=version&color=blue)](CHANGELOG.md)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Kind](https://img.shields.io/badge/kind-bundle-8A2BE2)](../../docs/decisions/adr-0001-marketplace-distribution-model.md)
[![Claude Code](https://img.shields.io/badge/Claude_Code-not_tested-D97757?logo=claude&logoColor=white)](#-compatibility)
[![Claude Cowork](https://img.shields.io/badge/Claude_Cowork-not_tested-D97757?logo=claude&logoColor=white)](#-compatibility)
![Ruff](https://img.shields.io/badge/Ruff-%E2%89%A50.16-D7FF64?logo=ruff&logoColor=black)
![Bash](https://img.shields.io/badge/Bash-%E2%89%A53.2-4EAA25?logo=gnubash&logoColor=white)
![jq](https://img.shields.io/badge/jq-%E2%89%A51.6-555555)
![Git](https://img.shields.io/badge/Git-%E2%89%A52.18-F05032?logo=git&logoColor=white)
![Hooks](https://img.shields.io/badge/hooks-4_events_(on_request)-orange)
![Network](https://img.shields.io/badge/network-none-lightgrey)

[← claude-essentials](../../README.md) · [Install](#-installation) · [Skills](#-skills) ·
[Security](#-security) · [Limitations](#-limitations) · [Changelog](CHANGELOG.md)

> **Claude writes Python that passes Ruff, and, when you ask for it, cannot finish until every file it touched is fixed, formatted, and clean, without silencing a single rule.**

**Kind:** `bundle` — a full workflow: multiple components working together.

Ruff Quality helps Python developers who use Claude Code keep Ruff green. Its
`ruff` skill teaches Claude the current Ruff workflow, configuration,
migration, and pipelines whenever it works on Python. Its `ruff-hooks` skill
installs, only after you choose a scope and a configuration, a gate that fixes,
formats, and lints every Python file Claude edits, denies suppression comments
and configuration changes, and blocks the end of the turn until everything
passes. Installing the plugin does **not** wire any hook.

> [!CAUTION]
> After you choose a scope and a mode, `ruff-hooks` writes five hook groups (four
> events) to a Claude Code settings file (`.claude/settings.json`, `.claude/settings.local.json`,
> or `~/.claude/settings.json`), copies one handler script next to it, and, for
> the recommended mode, writes a `ruff.toml` where none exists. From then on the
> hooks rewrite the Python files Claude edits (safe fixes and formatting). It
> backs up the settings file first and prints the exact rollback.

## 🎯 What it does

| Scenario | How this plugin helps | Expected result |
| --- | --- | --- |
| Claude writes or edits Python | The `ruff` skill loads: safe fixes, then format, then check; no suppressions; scope limited to changed files | Code that passes the project's Ruff configuration |
| You migrate from Black, isort, and Flake8, or bring an older configuration up to current defaults | Tool-by-tool mapping, the `select` vs `extend-select` trap, current pre-commit hook ids and order | One reviewed change, no two formatters fighting |
| You want Ruff enforced on every edit | `ruff-hooks` shows the exact configuration of each mode with today's finding counts, then installs the gate in the scope you pick | Every edited file is fixed, formatted, and linted; findings go straight back to Claude |
| Claude tries `# noqa`, `# ruff: ignore`, or relaxing `[tool.ruff]` to get green | The gate denies the edit before it happens, and re-checks suppression counts and configuration after edits and at Stop | The rule gets fixed in code; configuration stays your decision |
| Claude tries to finish with findings left | The Stop gate re-checks every Python file edited this session and blocks, up to a limit you choose | The turn ends clean, or with a visible list of what is unresolved |

## 🚫 What it does not do

- **Does not** install any hook when you install the plugin, or write any file until you choose a scope and a mode.
- **Does not** lint or format the whole repository: the gate only touches files Claude edits in the session.
- **Does not** install Ruff, use the network, or apply unsafe fixes.
- **Does not** overwrite an existing Ruff configuration: the recommended profile is written only where none exists.
- **Not a fit when** you need enforcement for everyone, including humans and other tools: use pre-commit and CI for that (the `ruff` skill shows how). The gate is a guardrail for Claude, not a security boundary.

## ⚡ Installation

**Claude Code** — add the marketplace once, then install:

```text
/plugin marketplace add nerymurillohnd/claude-essentials
/plugin install ruff-quality@claude-essentials
```

Then work on Python as usual, or ask for the gate, for example: `Lint and format every Python file you edit with Ruff, and don't finish with errors left.`

**Claude Cowork** — **Customize → Plugins → Add marketplace**, enter
`nerymurillohnd/claude-essentials`, then install **Ruff Quality** from the list.
The `ruff` skill works there; Cowork does not run settings-based hooks, so
`ruff-hooks` only reports and never installs the gate. See [Compatibility](#-compatibility).

> [!TIP]
> Installation is complete when `/plugin list` shows `ruff-quality` as enabled
> and `/ruff-quality:ruff` and `/ruff-quality:ruff-hooks` appear in the `/` menu.

### What installing changes

| | Effect |
| --- | --- |
| **Does** | Registers two skills (`ruff`, `ruff-hooks`) in Claude Code's plugin state. |
| **Does not** | Create or modify settings, hooks, `.claude/`, `~/.claude/`, a Ruff configuration, or your repository. |

### Update, disable, or remove

```text
/plugin marketplace update claude-essentials
/plugin disable ruff-quality@claude-essentials
/plugin uninstall ruff-quality@claude-essentials
```

In Cowork, use **Update** on the marketplace, and **Uninstall** on the plugin
under **Customize → Plugins**.

Uninstalling the plugin does **not** remove a gate the skill installed: the
installed handler is a standalone copy. Remove the gate first with
`! bash "<plugin dir>/skills/ruff-hooks/scripts/manage.sh" uninstall --scope <scope>`
(ask Claude for the exact command), or follow
[rollback](skills/ruff-hooks/references/rollback.md).

## 🧠 Skills

| Skill | Invoke | Claude uses it when | Invocation |
| --- | --- | --- | --- |
| [`ruff`](skills/ruff/SKILL.md) | `/ruff-quality:ruff` | It writes, edits, reviews, or fixes Python; or you ask about Ruff rules, configuration, migration from Black/isort/Flake8, pre-commit, CI, or the language server | Claude + user |
| [`ruff-hooks`](skills/ruff-hooks/SKILL.md) | `/ruff-quality:ruff-hooks` | You ask for a Ruff after-edit hook or gate, or to check, update, or remove it | Claude + user |

The `ruff-hooks` workflow, with a stop at each gate:

1. **Assess**: Ruff version and location, Python files, the configuration that applies today, finding counts under each mode, existing hooks.
2. **Show the configuration**: the exact recommended `ruff.toml`, your own configuration, or Ruff's defaults, explained with those counts; you choose the mode.
3. **Choose a scope**: project, local, or user.
4. **Preflight**: bash, jq, git, ruff ≥ 0.16, valid settings, no second scope, no `disableAllHooks`.
5. **Install**: backups, profile (recommended mode, only where none exists), handler copy, five hook groups, then the test suite against the installed copy; failure restores everything.
6. **Hand off**: you confirm in `/hooks`; you get the exact rollback.

## 🤖 Agents

None — this plugin ships two skills and no agents.

## 🪝 Hooks and side effects

The plugin registers **no** hooks. On your approval, `ruff-hooks` installs these
in the scope you chose:

| Event | Matcher | What the handler does | Blocks? |
| --- | --- | --- | --- |
| `UserPromptSubmit` | — | Records the Ruff configuration and suppression counts as accepted | No |
| `PreToolUse` | `Write\|Edit\|NotebookEdit\|Bash` | Denies adding `noqa`/`ruff:`/`fmt:`/`isort:` suppressions and changing `ruff.toml`, `.ruff.toml`, `[tool.ruff]`, the user-level Ruff configuration, the handler, or its settings | Yes: the edit |
| `PostToolUse` | `Write\|Edit\|NotebookEdit`, `Bash` | `ruff check --fix` (safe only), `ruff format`, `ruff check` on each edited `.py`/`.pyi`/`.ipynb`; rewrites those files | No (the tool already ran); findings go to Claude with exit 2 |
| `Stop` | — | Re-checks every Python file edited this session, suppressions, and configuration | Yes: the end of the turn, up to `--max-blocks` (1–7, default 5) |

| Scope | Settings file | Handler | Shared |
| --- | --- | --- | --- |
| project | `.claude/settings.json` | `.claude/hooks/ruff-quality-gate.sh` | Yes — commit both (and a new `ruff.toml`) |
| local | `.claude/settings.local.json` | `.claude/hooks/ruff-quality-gate.sh` | No — kept out of git via `.git/info/exclude` |
| user | `~/.claude/settings.json` | `~/.claude/hooks/ruff-quality-gate.sh` | No — applies to every project on this machine |

Every result tells you in one line (`ruff-quality ✓ …` or `✗ …`). Failures exit 2,
never 1, so Claude always sees them; missing tools and broken configuration fail
closed. Per-session state lives in `$TMPDIR/ruff-quality-gate-<uid>/`. Details:
[hook contract](skills/ruff-hooks/references/hook-contract.md).

## 🔌 MCP, permissions, and network

None — no MCP servers, no network access, no credentials.

## 📋 Requirements

| Requirement | Minimum | Check | Why |
| --- | --- | --- | --- |
| Claude Code | 2.1.222; 2.1.269 for Bash-edit coverage | `claude --version` | Loads the skills and runs the hooks; `plugin.json` carries `metadata`, a recognized manifest field from 2.1.222 — earlier versions treat it as unrecognized, which `claude plugin validate --strict` turns into an error; `ruff-hooks` locates its scripts through `${CLAUDE_SKILL_DIR}` (2.1.69); `bashEditDiff` needs 2.1.269 |
| Ruff | 0.16 | `ruff --version` | Every gate step; the recommended profile uses 0.16 defaults |
| Bash | 3.2 | `bash --version` | Runs the handler and installer (macOS's stock `/bin/bash` 3.2 works) |
| jq | 1.6 | `jq --version` | Parses hook payloads and merges settings |
| Git | 2.18 | `git --version` | Project and local scope, backups, and suppression baselines |
| Windows only | Git for Windows (Git Bash) | `bash --version` in Git Bash | Without Git Bash, hooks run in PowerShell and a Bash handler cannot run |

Only the gate needs these; the `ruff` skill works without them. With project
scope, everyone who runs Claude Code in the repository needs them too.

```bash
ruff --version
bash --version
jq --version
```

Install Ruff with `uv tool install ruff`, or add it to the project's dev
dependencies. The gate uses `RUFF_BIN` when you set it, then the nearest
`.venv/bin/ruff` or `venv/bin/ruff`, then `PATH`, then `~/.local/bin`,
`/opt/homebrew/bin`, and `/usr/local/bin`. The skill's `preflight` step
checks everything and never installs anything.

## ✅ Verification

**Consumer smoke test** — after installing from the remote marketplace, in a
Git repository with Python files:

```text
Assess whether this project should use the ruff-quality gate, and show me each configuration option.
```

Expected result: a report of the Ruff version, the configuration that applies,
finding counts per mode, and the three configurations, with no file changed.
After you choose a scope and a mode, the install output shows
`test suite: 99 passed, 0 failed`.

**Behavioral evals** — [`evals/`](evals/) runs with `claude plugin eval`, which compares a
run with the plugin against a baseline without it:

| Case | Checks | With | Without | Δ | Last run |
| --- | --- | ---: | ---: | ---: | --- |
| `fix-python-snippet` | `ruff` fires when cleaning up Python and fixes findings instead of silencing them | — | — | — | Pending re-measurement — the skill descriptions changed in this version |
| `migrate-black-isort` | `ruff` fires on a migration question and gives current hook ids and order | — | — | — | Pending re-measurement — the skill descriptions changed in this version |
| `hook-request-gated` | `ruff-hooks` fires, asks for scope and mode, writes no settings (the case grants no shell, so it tests the gate's wording, not an install) | — | — | — | Pending re-measurement — the skill descriptions changed in this version |
| `ignores-concept-question` | Neither skill fires on a conceptual Python question | — | — | — | Pending re-measurement — the skill descriptions changed in this version |

<details>
<summary>Maintainer checks</summary>

From the marketplace root:

```bash
npm run check
claude plugin validate plugins/ruff-quality --strict
plugins/ruff-quality/skills/ruff-hooks/scripts/test-gate.sh
plugins/ruff-quality/skills/ruff-hooks/scripts/test-manage.sh
RQ_TEST_BASH=/bin/bash plugins/ruff-quality/skills/ruff-hooks/scripts/test-gate.sh
RQ_TEST_BASH=/bin/bash plugins/ruff-quality/skills/ruff-hooks/scripts/test-manage.sh
claude plugin eval plugins/ruff-quality --no-publish --max-cost-usd 6
```

`npm test` runs both suites on every bash it finds, so CI covers them.

</details>

## 🧭 Compatibility

| Surface | Status | Last verified | Notes |
| --- | --- | --- | --- |
| Claude Code (CLI, Desktop, IDE) on macOS | 🧪 Not tested | 2026-09-19, Claude Code 2.1.278, local checkout only | Gate installed with `manage.sh` into a scratch project and exercised in live `claude -p` sessions: findings reached Claude and were fixed, `✓`/`✗` messages reached the user, the Stop gate confirmed, and a file written through Bash was formatted from `bashEditDiff`. Suites pass on bash 3.2.57 and 5.3.20 with Ruff 0.16.8. Not yet installed from the remote marketplace |
| Claude Code on Linux / WSL | 🧪 Not tested | — | Same Bash handler; CI runs both suites on Linux |
| Claude Code on Windows with Git Bash | 🧪 Not tested | — | Designed for Git Bash; not yet run on Windows |
| Claude Code on Windows without Git Bash | ❌ Not supported | — | Hooks run in PowerShell; `preflight` refuses |
| Claude Code cloud sessions | ⚠️ Partial | — | Only project scope applies: cloud sessions don't read `~/.claude/settings.json`, and Ruff must be available there |
| Claude Cowork | 🧪 Not tested | — | The `ruff` skill should work; Cowork does not run settings hooks ([anthropics/claude-code#40495](https://github.com/anthropics/claude-code/issues/40495)), so `ruff-hooks` refuses to install |
| Claude Chat (web, desktop) | ❌ Not supported | — | Plugins aren't used in Chat. |

## 💡 Examples

**Install the gate with the recommended profile**

```text
Set up Ruff so every Python file you touch is linted and formatted, and you can't stop with errors.
```

→ Claude assesses the project, shows the recommended `ruff.toml`, your current
configuration, and Ruff's defaults with today's finding counts, and waits. After
you answer "recommended, project", it installs, shows `99 passed, 0 failed`,
and asks you to check `/hooks`.

**What Claude sees after an edit**

```text
ruff-quality: STOP and fix this before any other change.

calc.py:2:5: F841 Local variable `tmp` is assigned to but never used

Change the code so each rule passes. Suppression comments (noqa, ruff: noqa/ignore/disable/file-ignore, fmt: off/skip, isort: skip/off) and Ruff configuration changes are never accepted by this gate. …
```

**What you see**

```text
PostToolUse:Write says: ruff-quality ✗ 1 Ruff finding(s); Claude has been told to fix them now.
PostToolUse:Write says: ruff-quality ✓ calc.py: lint-clean and formatted
Stop says: ruff-quality ✓ Stop gate: 1 edited Python file(s) are lint-clean, formatted, and unsuppressed.
```

## 🔐 Security

| Access | What it may do |
| --- | --- |
| Read | Python files Claude edits; Ruff configuration files in the repository and `~/.config/ruff/`; the three Claude Code settings files; managed settings (assessment only) |
| Write | Only after your choice: one settings file, the `hooks/` folder and one handler copy, a `ruff.toml` (recommended mode, only where none exists), backups under `<git common dir>/ruff-quality-backups/` (project and local scope) or `~/.claude/backups/ruff-quality/` (user scope, under `$CLAUDE_CONFIG_DIR` when set), `.git/info/exclude` (local scope), and per-session state in `$TMPDIR`. The installed hooks rewrite the Python files Claude edits (safe fixes and formatting). `uninstall` removes the gate's hook groups, the handler, its `hooks/` folder when empty, a project or local settings file left empty, and the local-scope exclude lines; it keeps the backups and any `ruff.toml` |
| Process | `bash`, `jq`, `git`, `ruff`, and the bundled scripts |
| Network | Not used |
| Credentials | None |

- **Human approval:** every write happens only after you choose a scope and a mode; while the gate is installed, only you can change or remove it (it denies Claude running the installer).
- **Fail closed:** a missing tool, broken configuration, or unreadable payload exits 2 with the reason.
- **Trust:** review [`ruff-quality-gate.sh`](skills/ruff-hooks/assets/ruff-quality-gate.sh) and [`manage.sh`](skills/ruff-hooks/scripts/manage.sh) before installing in a critical repository.
- **Report a vulnerability** privately via the [security policy](../../SECURITY.md). Never post secrets in issues.

## 🚧 Limitations

| Limitation | What you'll see | Safe recovery |
| --- | --- | --- |
| Bash writes are seen only when Claude Code records `bashEditDiff` (auto and bypass modes, or `bashEditDiffEnabled: true`), only inside a Git repository and never for Git-ignored files | A file written by `sed` or a heredoc in default mode, or a Git-ignored file, is not fixed after the command | The guard's Bash heuristics and the Stop gate's suppression and configuration checks still apply; set `bashEditDiffEnabled` in user settings |
| The Bash guard is textual | A suppression hidden in a script Claude wrote and then ran is not denied up front | Post and Stop catch suppression growth and configuration drift in files the gate knows |
| The gate cannot tell who changed configuration during a turn | If you edit `ruff.toml` while Claude is working, the Stop gate flags it | Let the turn end (it releases after the block limit with a warning); your next prompt accepts the change |
| Unused imports are not reported mid-change | `F401` appears only at Stop | Intended: an import added one edit before its use would otherwise be deleted |
| Hook timeout (30 s guard and baseline, 60 s post, 120 s Stop) | The call proceeds without a decision; a timed-out guard does not deny | Measured runs take well under a second per file; report very slow projects |
| A committed project gate without the tools on a teammate's machine | Every Python edit fails closed with `ruff not found` | Install Ruff or set `RUFF_BIN`, or uninstall the gate |
| `jq` removed after the gate is installed | Every `Write`, `Edit`, and `Bash` call is denied (fail-closed) with the reason | Install `jq` again with the `!` prefix, or uninstall the gate the same way |
| Cowork | No gate | Use Claude Code |
| Ruff passing is not proof of correctness | — | Tests and review still apply |

## ❓ FAQ

<details>
<summary>Why a skill that installs hooks, instead of plugin hooks?</summary>

Plugin hooks would be active in every project the moment you install the
plugin, with no choice of scope or configuration. Here you decide whether,
where, and with which configuration; the gate keeps working if the plugin is
updated or removed; and a team can commit it.

</details>

<details>
<summary>Can Claude add a <code># noqa</code> if I ask for it?</summary>

With the gate installed, no: it denies every new suppression, whoever asked.
Add it yourself in your editor, between turns; the gate accepts changes you
make between turns.

</details>

<details>
<summary>How is this different from Astral's official Ruff skill?</summary>

As of 2026-09-19, the official skill (in `astral-sh/claude-code-plugins`)
predates Ruff 0.16 and installs no hooks. This plugin covers the current
defaults (413 rules, `ruff: ignore`, Markdown formatting), migration and pipelines,
and adds an optional, tested gate that also forbids silencing rules. It is not
affiliated with Astral.

</details>

## 📝 Changelog

Every published version is in [CHANGELOG.md](CHANGELOG.md), and each version is tagged
`ruff-quality--v<version>`. Current version: see the badge above.

## 📄 License

[Apache-2.0](LICENSE) © Nery Samuel Murillo Tejada.

---

<sub>Part of [claude-essentials](../../README.md) · [Report an issue](https://github.com/nerymurillohnd/claude-essentials/issues/new/choose) · [Security](../../SECURITY.md) · Not an official Anthropic product.</sub>
