# 🐚 Shell Quality

[![Version](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2Fnerymurillohnd%2Fclaude-essentials%2Fmain%2Fplugins%2Fshell-quality%2F.claude-plugin%2Fplugin.json&query=%24.version&label=version&color=blue)](CHANGELOG.md)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Kind](https://img.shields.io/badge/kind-bundle-8A2BE2)](../../docs/decisions/adr-0001-marketplace-distribution-model.md)
[![Claude Code](https://img.shields.io/badge/Claude_Code-not_tested-D97757?logo=claude&logoColor=white)](#-compatibility)
[![Claude Cowork](https://img.shields.io/badge/Claude_Cowork-not_tested-D97757?logo=claude&logoColor=white)](#-compatibility)
![ShellCheck](https://img.shields.io/badge/ShellCheck-%E2%89%A50.10-4EAA25)
![shfmt](https://img.shields.io/badge/shfmt-%E2%89%A53.12-00ADD8)
![Bash](https://img.shields.io/badge/Bash-%E2%89%A53.2-4EAA25?logo=gnubash&logoColor=white)
![jq](https://img.shields.io/badge/jq-%E2%89%A51.6-555555)
![Git](https://img.shields.io/badge/Git-%E2%89%A52.18-F05032?logo=git&logoColor=white)
![Hooks](https://img.shields.io/badge/hooks-4_events_(on_request)-orange)
![Network](https://img.shields.io/badge/network-none-lightgrey)

[← claude-essentials](../../README.md) · [Install](#-installation) · [Skills](#-skills) ·
[Security](#-security) · [Limitations](#-limitations) · [Changelog](CHANGELOG.md)

> **Claude writes shell scripts that pass ShellCheck and shfmt, and, when you ask for it, cannot finish until every script it touched is formatted and clean, without silencing a single check.**

**Kind:** `bundle` — a full workflow: multiple components working together.

Shell Quality helps anyone who lets Claude write Bash or POSIX shell keep it
correct and consistent. Its `shell-lint` skill teaches Claude the current
ShellCheck and shfmt workflow, correct fixes for common SC codes,
macOS Bash 3.2 pitfalls, configuration, migration, and pipelines whenever it
works on a shell script. Its `shell-hooks` skill installs, only after you
choose a scope and a configuration, a gate that formats and checks every script
Claude edits, denies `# shellcheck disable` directives and configuration
changes, and blocks the end of the turn until everything passes. Installing
the plugin does **not** wire any hook.

> [!CAUTION]
> After you choose a scope and a mode, `shell-hooks` writes five hook groups (four
> events) to a Claude Code settings file (`.claude/settings.json`,
> `.claude/settings.local.json`, or `~/.claude/settings.json`), copies one
> handler script next to it, and, for the recommended mode, writes a
> `.shellcheckrc` where none exists and appends a marked `[[shell]]` block to
> `.editorconfig`. From then on the hooks reformat the scripts Claude edits. It
> backs up the files it changes and prints the exact rollback.

## 🎯 What it does

| Scenario | How this plugin helps | Expected result |
| --- | --- | --- |
| Claude writes or edits a shell script | The `shell-lint` skill loads: shfmt, then ShellCheck; correct fixes for SC2086, SC2155, SC2164, SC2181, SC1091…; no directives to silence | Scripts that pass the project's ShellCheck and EditorConfig |
| A script must run on a stock Mac | The skill lists what `/bin/bash` 3.2 lacks, which ShellCheck never flags | No `declare -A`, `mapfile`, or `${x,,}` surprises at run time |
| Your CI runs `shfmt -i 2 -s` next to an `.editorconfig` | The skill explains that any style flag disables EditorConfig, and gives the flag-free CI and pre-commit setup | One source of formatting truth |
| You want ShellCheck enforced on every edit | `shell-hooks` shows the exact configuration of each mode with today's counts, then installs the gate in the scope you pick | Every edited script is formatted and checked; findings go straight back to Claude |
| Claude tries `# shellcheck disable=…`, `source=/dev/null`, or relaxing `.shellcheckrc` | The gate denies the edit before it happens, and re-checks directive counts and configuration after edits and at Stop | The script gets fixed; configuration stays your decision |
| Claude tries to finish with findings left | The Stop gate re-checks every script edited this session and blocks, up to a limit you choose | The turn ends clean, or with a visible list of what is unresolved |

## 🚫 What it does not do

- **Does not** install any hook when you install the plugin, or write any file until you choose a scope and a mode.
- **Does not** lint or format the whole repository: the gate only touches scripts Claude edits in the session.
- **Does not** install ShellCheck or shfmt, use the network, or check zsh scripts (ShellCheck does not support zsh).
- **Does not** overwrite an existing rc file or EditorConfig shell style: the recommended profile is added only where none exists.
- **Does not** check Bash version compatibility: ShellCheck cannot; the skill teaches the pitfalls instead.
- **Not a fit when** you need enforcement for everyone, including humans and other tools: use pre-commit and CI for that (the `shell-lint` skill shows how). The gate is a guardrail for Claude, not a security boundary.

## ⚡ Installation

**Claude Code** — add the marketplace once, then install:

```text
/plugin marketplace add nerymurillohnd/claude-essentials
/plugin install shell-quality@claude-essentials
```

Then work on shell scripts as usual, or ask for the gate, for example: `Run shfmt and ShellCheck on every script you edit, and don't finish with findings left.`

**Claude Cowork** — **Customize → Plugins → Add marketplace**, enter
`nerymurillohnd/claude-essentials`, then install **Shell Quality** from the list.
The `shell-lint` skill works there; Cowork does not run settings-based hooks, so
`shell-hooks` only reports and never installs the gate. See [Compatibility](#-compatibility).

> [!TIP]
> Installation is complete when `/plugin list` shows `shell-quality` as enabled
> and `/shell-quality:shell-lint` and `/shell-quality:shell-hooks` appear in the `/` menu.

### What installing changes

| | Effect |
| --- | --- |
| **Does** | Registers two skills (`shell-lint`, `shell-hooks`) in Claude Code's plugin state. |
| **Does not** | Create or modify settings, hooks, `.claude/`, `~/.claude/`, `.shellcheckrc`, `.editorconfig`, or your repository. |

### Update, disable, or remove

```text
/plugin marketplace update claude-essentials
/plugin disable shell-quality@claude-essentials
/plugin uninstall shell-quality@claude-essentials
```

In Cowork, use **Update** on the marketplace, and **Uninstall** on the plugin
under **Customize → Plugins**.

Uninstalling the plugin does **not** remove a gate the skill installed: the
installed handler is a standalone copy. Remove the gate first with
`! bash "<plugin dir>/skills/shell-hooks/scripts/manage.sh" uninstall --scope <scope>`
(ask Claude for the exact command), or follow
[rollback](skills/shell-hooks/references/rollback.md).

## 🧠 Skills

| Skill | Invoke | Claude uses it when | Invocation |
| --- | --- | --- | --- |
| [`shell-lint`](skills/shell-lint/SKILL.md) | `/shell-quality:shell-lint` | It writes, edits, reviews, or fixes a shell script; or you ask about SC codes, `.shellcheckrc`, shfmt and EditorConfig, portability, migration, pre-commit, or CI | Claude + user |
| [`shell-hooks`](skills/shell-hooks/SKILL.md) | `/shell-quality:shell-hooks` | You ask for a ShellCheck/shfmt after-edit hook or gate, or to check, update, or remove it | Claude + user |

The `shell-hooks` workflow, with a stop at each gate:

1. **Assess**: ShellCheck and shfmt versions, the scripts found (by extension and shebang), the rc file and EditorConfig that apply today, findings and unformatted scripts under each mode, existing hooks.
2. **Show the configuration**: the exact recommended `.shellcheckrc` and `[[shell]]` block, your own configuration, or the tools' defaults, explained with those counts; you choose the mode.
3. **Choose a scope**: project, local, or user.
4. **Preflight**: bash, jq, git, ShellCheck, and shfmt versions, valid settings, no second scope, no `disableAllHooks`.
5. **Install**: backups, profile (recommended mode, only where none exists), handler copy, five hook groups, then the test suite against the installed copy; failure restores everything.
6. **Hand off**: you confirm in `/hooks`; you get the exact rollback.

## 🤖 Agents

None — this plugin ships two skills and no agents.

## 🪝 Hooks and side effects

The plugin registers **no** hooks. On your approval, `shell-hooks` installs these
in the scope you chose:

| Event | Matcher | What the handler does | Blocks? |
| --- | --- | --- | --- |
| `UserPromptSubmit` | — | Records the ShellCheck/EditorConfig configuration and directive counts as accepted | No |
| `PreToolUse` | `Write\|Edit\|Bash` | Denies adding `# shellcheck disable=…`/`source=/dev/null` and changing `.shellcheckrc`/`shellcheckrc`, the user-level rc, the shfmt keys of `.editorconfig`, the handler, or its settings | Yes: the edit |
| `PostToolUse` | `Write\|Edit`, `Bash` | `shfmt -w`, then `shellcheck -f gcc` on each edited `.sh`/`.bash`/`.bats` or sh/bash/dash/ksh shebang script; reformats those files | No (the tool already ran); findings go to Claude with exit 2 |
| `Stop` | — | Re-checks every script edited this session (`shellcheck`, `shfmt -d`), directives, and configuration | Yes: the end of the turn, up to `--max-blocks` (1–7, default 5) |

| Scope | Settings file | Handler | Shared |
| --- | --- | --- | --- |
| project | `.claude/settings.json` | `.claude/hooks/shell-quality-gate.sh` | Yes — commit both (and new `.shellcheckrc`/`.editorconfig` changes) |
| local | `.claude/settings.local.json` | `.claude/hooks/shell-quality-gate.sh` | No — kept out of git via `.git/info/exclude` |
| user | `~/.claude/settings.json` | `~/.claude/hooks/shell-quality-gate.sh` | No — applies to every project on this machine |

Every result tells you in one line (`shell-quality ✓ …` or `✗ …`). Failures exit 2,
never 1, so Claude always sees them; missing tools and broken configuration fail
closed. Per-session state lives in `$TMPDIR/shell-quality-gate-<uid>/`. Details:
[hook contract](skills/shell-hooks/references/hook-contract.md).

## 🔌 MCP, permissions, and network

None — no MCP servers, no network access, no credentials.

## 📋 Requirements

| Requirement | Minimum | Check | Why |
| --- | --- | --- | --- |
| Claude Code | 2.1.222; 2.1.269 for Bash-edit coverage | `claude --version` | Loads the skills and runs the hooks; `plugin.json` carries `metadata`, a recognized manifest field from 2.1.222 — earlier versions treat it as unrecognized, which `claude plugin validate --strict` turns into an error; `${CLAUDE_SKILL_DIR}` needs 2.1.69; `bashEditDiff` needs 2.1.269 |
| ShellCheck | 0.10 (0.11 for the recommended profile) | `shellcheck --version` | Checks every edited script; the profile uses 0.11 optional checks |
| shfmt | 3.12 | `shfmt --version` | Formats every edited script; `simplify` in EditorConfig needs 3.12 |
| Bash | 3.2 | `bash --version` | Runs the handler and installer (macOS's stock `/bin/bash` 3.2 works) |
| jq | 1.6 | `jq --version` | Parses hook payloads and merges settings |
| Git | 2.18 | `git --version` | Project and local scope, backups, and suppression baselines |
| Windows only | Git for Windows (Git Bash) | `bash --version` in Git Bash | Without Git Bash, hooks run in PowerShell and a Bash handler cannot run |

Only the gate needs these; the `shell-lint` skill works without them. With project
scope, everyone who runs Claude Code in the repository needs them too.

```bash
shellcheck --version
shfmt --version
bash --version
jq --version
```

Install them with your package manager (`brew install shellcheck shfmt`) or
pinned release binaries; Ubuntu's apt ships ShellCheck 0.9, too old for the
recommended profile. The skill's
`preflight` step checks everything and never installs anything.

## ✅ Verification

**Consumer smoke test** — after installing from the remote marketplace, in a
Git repository with shell scripts:

```text
Assess whether this project should use the shell-quality gate, and show me each configuration option.
```

Expected result: a report of the ShellCheck and shfmt versions, the configuration
that applies, counts per mode, and the three configurations, with no file
changed. After you choose a scope and a mode, the install output shows
`test suite: 82 passed, 0 failed`.

**Behavioral evals** — [`evals/`](evals/) runs with `claude plugin eval`, which compares a
run with the plugin against a baseline without it:

| Case | Checks | With | Without | Δ | Last run |
| --- | --- | ---: | ---: | ---: | --- |
| `fix-shell-snippet` | `shell-lint` fires when cleaning up a script and fixes findings instead of silencing them | — | — | — | Pending re-measurement — the skill descriptions changed in this version |
| `editorconfig-question` | `shell-lint` fires and explains that style flags disable EditorConfig | — | — | — | Pending re-measurement — the skill descriptions changed in this version |
| `hook-request-gated` | `shell-hooks` fires, asks for scope and mode, writes no settings (the case grants no shell, so it tests the gate's wording, not an install) | — | — | — | Pending re-measurement — the skill descriptions changed in this version |
| `ignores-concept-question` | Neither skill fires on a conceptual shell question | — | — | — | Pending re-measurement — the skill descriptions changed in this version |

<details>
<summary>Maintainer checks</summary>

From the marketplace root:

```bash
npm run check
claude plugin validate plugins/shell-quality --strict
plugins/shell-quality/skills/shell-hooks/scripts/test-gate.sh
plugins/shell-quality/skills/shell-hooks/scripts/test-manage.sh
SQ_TEST_BASH=/bin/bash plugins/shell-quality/skills/shell-hooks/scripts/test-gate.sh
SQ_TEST_BASH=/bin/bash plugins/shell-quality/skills/shell-hooks/scripts/test-manage.sh
claude plugin eval plugins/shell-quality --no-publish --max-cost-usd 6
```

`npm test` runs both suites on every bash it finds, so CI covers them.

</details>

## 🧭 Compatibility

| Surface | Status | Last verified | Notes |
| --- | --- | --- | --- |
| Claude Code (CLI, Desktop, IDE) on macOS | 🧪 Not tested | 2026-09-19, Claude Code 2.1.278, local checkout only | Gate installed with `manage.sh` (project scope, recommended mode) into a scratch project and exercised in live `claude -p` sessions: an SC2086 finding reached Claude and was fixed, `✓`/`✗` messages reached the user, and the Stop gate confirmed; asked to add `# shellcheck disable`, Claude declined, so the deny path is covered by the suite only. Suites pass on bash 3.2.57 and 5.3.20 with ShellCheck 0.11.0 and shfmt 3.14.1. Not yet installed from the remote marketplace |
| Claude Code on Linux / WSL | 🧪 Not tested | — | Same Bash handler; CI runs both suites on Linux |
| Claude Code on Windows with Git Bash | 🧪 Not tested | — | Designed for Git Bash; not yet run on Windows |
| Claude Code on Windows without Git Bash | ❌ Not supported | — | Hooks run in PowerShell; `preflight` refuses |
| Claude Code cloud sessions | ⚠️ Partial | — | Only project scope applies: cloud sessions don't read `~/.claude/settings.json`, and ShellCheck and shfmt must be available there |
| Claude Cowork | 🧪 Not tested | — | The `shell-lint` skill should work; Cowork does not run settings hooks ([anthropics/claude-code#40495](https://github.com/anthropics/claude-code/issues/40495)), so `shell-hooks` refuses to install |
| Claude Chat (web, desktop) | ❌ Not supported | — | Plugins aren't used in Chat. |

## 💡 Examples

**Install the gate with your own configuration**

```text
Whenever you edit a shell script here, run shfmt and ShellCheck, and don't finish while ShellCheck complains.
```

→ Claude assesses the repository, shows your `.shellcheckrc` and EditorConfig,
the recommended profile, and the defaults with today's counts, and waits. After
you answer "own, project", it installs, shows `82 passed, 0 failed`, and asks
you to check `/hooks`.

**What Claude sees after an edit**

```text
shell-quality: STOP and fix this before any other change.

deploy.sh:4:6: note: Double quote to prevent globbing and word splitting. [SC2086]

Change the script so each check passes; read a code's explanation at https://www.shellcheck.net/wiki/SC<code>. ShellCheck suppressions (# shellcheck disable=..., source=/dev/null) and configuration changes are never accepted by this gate. …
```

**What Claude gets when it tries to silence a check**

```text
shell-quality: this edit to deploy.sh adds a ShellCheck suppression (# shellcheck disable=... or source=/dev/null). Silencing a finding is never allowed through this gate; change the script so the check passes. …
```

## 🔐 Security

| Access | What it may do |
| --- | --- |
| Read | Shell scripts Claude edits; `.shellcheckrc`/`shellcheckrc` and `.editorconfig` in the repository, `~/.shellcheckrc`, `${XDG_CONFIG_HOME:-~/.config}/shellcheckrc`; the three Claude Code settings files; managed settings (assessment only) |
| Write | Only after your choice: one settings file, the `hooks/` folder and one handler copy, a `.shellcheckrc` and a marked `.editorconfig` block (recommended mode, only where none exists), backups under `<git common dir>/shell-quality-backups/` (project and local scope) or `~/.claude/backups/shell-quality/` (user scope, under `$CLAUDE_CONFIG_DIR` when set), `.git/info/exclude` (local scope), and per-session state in `$TMPDIR`. The installed hooks reformat the scripts Claude edits |
| Process | `bash`, `jq`, `git`, `shellcheck`, `shfmt`, and the bundled scripts |
| Network | Not used |
| Credentials | None |

- **Human approval:** every write happens only after you choose a scope and a mode; while the gate is installed, only you can change or remove it (it denies Claude running the installer).
- **Fail closed:** a missing tool, broken configuration, or unreadable payload exits 2 with the reason.
- **Trust:** review [`shell-quality-gate.sh`](skills/shell-hooks/assets/shell-quality-gate.sh) and [`manage.sh`](skills/shell-hooks/scripts/manage.sh) before installing in a critical repository.
- **Report a vulnerability** privately via the [security policy](../../SECURITY.md). Never post secrets in issues.

## 🚧 Limitations

| Limitation | What you'll see | Safe recovery |
| --- | --- | --- |
| Bash writes are seen only when Claude Code records `bashEditDiff` (auto and bypass modes, or `bashEditDiffEnabled: true`) | A script written by a heredoc in default mode is not formatted after the command | The guard's Bash heuristics and the Stop gate's directive and configuration checks still apply; set `bashEditDiffEnabled` in user settings |
| The Bash guard is textual | A directive hidden in a script Claude wrote and then ran is not denied up front | Post and Stop catch directive growth and configuration drift in scripts the gate knows |
| The gate cannot tell who changed configuration during a turn | If you edit `.shellcheckrc` while Claude is working, the Stop gate flags it | Let the turn end (it releases after the block limit with a warning); your next prompt accepts the change |
| zsh and fish scripts | Not checked | ShellCheck does not support them |
| Bash version compatibility | A script that passes can fail on macOS `/bin/bash` 3.2 | Follow the `shell-lint` portability section; test with `/bin/bash` |
| Hook timeout (30 s baseline and guard, 60 s post, 120 s Stop) | The call proceeds without a decision | Measured runs take well under a second per script |
| A committed project gate without the tools on a teammate's machine | Every script edit fails closed with `shellcheck not found` | Install the tools, or uninstall the gate |
| `jq` removed after the gate is installed | Every `Write`, `Edit`, and `Bash` call is denied (fail-closed) with the reason | Install `jq` again with the `!` prefix, or uninstall the gate the same way |
| Cowork | No gate | Use Claude Code |

## ❓ FAQ

<details>
<summary>Why a skill that installs hooks, instead of plugin hooks?</summary>

Plugin hooks would be active in every project the moment you install the
plugin, with no choice of scope or configuration. Here you decide whether,
where, and with which configuration; the gate keeps working if the plugin is
updated or removed; and a team can commit it.

</details>

<details>
<summary>Why not a one-line <code>shfmt -w -i 2 &amp;&amp; shellcheck</code> hook?</summary>

Three reasons it does nothing useful: hooks get the file path as JSON on stdin
(there is no file-path environment variable), `shellcheck` exits 1 on findings
and exit 1 never reaches Claude (only exit 2 does), and `-i 2` disables your
EditorConfig. This gate parses the payload, exits 2 with the findings,
respects EditorConfig, and adds the guard and the Stop gate.

</details>

<details>
<summary>Can Claude add a <code># shellcheck disable</code> if I ask for it?</summary>

With the gate installed, no: it denies every new directive, whoever asked. Add
it yourself in your editor, between turns; the gate accepts changes you make
between turns.

</details>

## 📝 Changelog

Every published version is in [CHANGELOG.md](CHANGELOG.md), and each version is tagged
`shell-quality--v<version>`. Current version: see the badge above.

## 📄 License

[Apache-2.0](LICENSE) © Nery Samuel Murillo Tejada.

---

<sub>Part of [claude-essentials](../../README.md) · [Report an issue](https://github.com/nerymurillohnd/claude-essentials/issues/new/choose) · [Security](../../SECURITY.md) · Not an official Anthropic product.</sub>
