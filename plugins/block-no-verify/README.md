# 🛡️ Block No Verify

[![Version](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2Fnerymurillohnd%2Fclaude-essentials%2Fmain%2Fplugins%2Fblock-no-verify%2F.claude-plugin%2Fplugin.json&query=%24.version&label=version&color=blue)](CHANGELOG.md)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Kind](https://img.shields.io/badge/kind-skill--only-8A2BE2)](../../docs/decisions/adr-0001-marketplace-distribution-model.md)
[![Claude Code](https://img.shields.io/badge/Claude_Code-partial-D97757?logo=claude&logoColor=white)](#-compatibility)
[![Claude Cowork](https://img.shields.io/badge/Claude_Cowork-not_supported-D97757?logo=claude&logoColor=white)](#-compatibility)
![Bash](https://img.shields.io/badge/Bash-%E2%89%A53.2-4EAA25?logo=gnubash&logoColor=white)
![jq](https://img.shields.io/badge/jq-%E2%89%A51.6-555555)
![Git](https://img.shields.io/badge/Git-%E2%89%A52.18-F05032?logo=git&logoColor=white)
![Hooks](https://img.shields.io/badge/hooks-PreToolUse_(on_request)-orange)
![Network](https://img.shields.io/badge/network-none-lightgrey)

[← claude-essentials](../../README.md) · [Install](#-installation) · [Skill](#-skills) ·
[Security](#-security) · [Limitations](#-limitations) · [Changelog](CHANGELOG.md)

> **Stop Claude from skipping your Git hooks or commit signing, in the scope you choose, only when you ask for it.**

**Kind:** `skill-only` — exactly one skill, nothing else.

Block No Verify helps developers who rely on pre-commit, husky, lefthook, or
signed commits keep Claude from bypassing them with `--no-verify`, `-n`,
`--no-gpg-sign`, `-c core.hooksPath=…`, `HUSKY=0`, and similar tricks. Its
skill assesses the repository, recommends a scope, and, after your explicit
approval, installs a Claude Code `PreToolUse` hook that denies those commands.
Installing the plugin does **not** wire anything.

> [!CAUTION]
> After you approve, the skill writes to a Claude Code settings file
> (`.claude/settings.json`, `.claude/settings.local.json`, or
> `~/.claude/settings.json`, or `$CLAUDE_CONFIG_DIR/settings.json` when set) and
> copies one handler script next to it. It backs
> up the settings file first and prints the exact rollback.

## 🎯 What it does

| Scenario | How this plugin helps | Expected result |
| --- | --- | --- |
| A hook fails and Claude reaches for `git commit --no-verify` | The installed policy denies the command and tells Claude to fix the cause | The hook's failure gets fixed instead of skipped |
| Your team requires signed commits | Denies `--no-gpg-sign`, `-c commit.gpgsign=false`, `git config commit.gpgsign false`, fake `gpg.program` | Unsigned commits never come from Claude's shell |
| Husky, pre-commit, or lefthook guard the repository | Denies `HUSKY=0`, `SKIP=…`, `LEFTHOOK=0`, `core.hooksPath` overrides, even via `export`, `env`, `sudo`, `bash -c`, `eval` | Local verification runs on every Claude commit |
| You want to know whether you're protected | `status` and `assess` report where the policy is installed and what it would protect | A clear answer, with no changes |

## 🚫 What it does not do

- **Does not** install anything when you install the plugin. No hook, no settings, no `.claude/` directory.
- **Does not** write any file until you approve a scope in the conversation.
- **Does not** control what you type in your own terminal, IDE Git integrations, or CI.
- **Not a fit when** you need enforcement: branch protection, required status checks, and required signatures on the server are the real controls. This policy stops Claude's shortcuts; it is not a security boundary against a determined user.

## ⚡ Installation

**Claude Code** — add the marketplace once, then install:

```text
/plugin marketplace add nerymurillohnd/claude-essentials
/plugin install block-no-verify@claude-essentials
```

Then ask for it, for example: `Protect this repo so you can't skip my pre-commit hooks.`

**Claude Cowork** — **Customize → Plugins → Add marketplace**, enter
`nerymurillohnd/claude-essentials`, then install **Block No Verify** from the list.
The skill loads there, but Cowork does not run settings-based hooks, so it only
reports and never installs the policy. See [Compatibility](#-compatibility).

> [!TIP]
> Installation is complete when `/plugin list` shows `block-no-verify` as enabled
> and `/block-no-verify:block-no-verify` appears in the `/` menu.

### What installing changes

| | Effect |
| --- | --- |
| **Does** | Registers one skill (`block-no-verify`) in Claude Code's plugin state. |
| **Does not** | Create or modify settings, hooks, `.claude/`, `~/.claude/`, or your repository. |

### Update, disable, or remove

```text
/plugin marketplace update claude-essentials
/plugin disable block-no-verify@claude-essentials
/plugin uninstall block-no-verify@claude-essentials
```

In Cowork, use **Update** on the marketplace, and **Uninstall** on the plugin
under **Customize → Plugins**.

Uninstalling the plugin does **not** remove a policy the skill installed: the
installed handler is a standalone copy. Ask the skill to uninstall it first
(`Uninstall the block-no-verify policy from project scope`), or follow
[rollback](skills/block-no-verify/references/rollback.md).

## 🧠 Skills

| Skill | Invoke | Claude uses it when | Invocation |
| --- | --- | --- | --- |
| [`block-no-verify`](skills/block-no-verify/SKILL.md) | `/block-no-verify:block-no-verify` | You ask to block `--no-verify`, protect hooks, enforce signing, or check/remove the policy; or you're committing/rebasing, when it runs the read-only `status` check once per session (reads the three settings files and the version line of any installed handler) and offers the protection in one line if it's absent | Claude + user |

The skill's workflow, with a stop at each gate:

1. **Assess**: repository, hook tooling, signing, existing hooks in every scope, and a verdict (including "nothing to protect here").
2. **Recommend a scope** (project, local, or user) and wait for your explicit choice.
3. **Preflight**: bash, jq, valid settings JSON, no `disableAllHooks`/managed restriction, and the handler runs on this machine. Any failure stops.
4. **Install**: backup, byte-identical handler copy, one idempotent settings merge.
5. **Verify**: 331-case suite against the installed copy, plus live payloads (a bypass is denied, a clean commit allowed). Failure restores the backup.
6. **Hand off**: you confirm in `/hooks`; you get the exact rollback.

## 🤖 Agents

None — this plugin ships exactly one skill and no agents.

## 🪝 Hooks and side effects

The plugin registers **no** hooks. On your approval, the skill installs one
hook group in the scope you chose:

| Event | Matcher | What the handler does | Blocks? |
| --- | --- | --- | --- |
| `PreToolUse` | `Bash\|PowerShell` | Parses the command Claude is about to run and denies Git verification or signing bypasses; reads Git aliases (read-only) to resolve `git <alias> -n`; writes nothing; timeout 10 s | Yes: the tool call |

| Scope | Settings file | Handler | Shared |
| --- | --- | --- | --- |
| project | `.claude/settings.json` | `.claude/hooks/block-no-verify.sh` | Yes — commit both files together |
| local | `.claude/settings.local.json` | `.claude/hooks/block-no-verify.sh` | No — kept out of git via `.git/info/exclude` |
| user | `~/.claude/settings.json` (or `$CLAUDE_CONFIG_DIR/settings.json`) | `~/.claude/hooks/block-no-verify.sh` (or under `$CLAUDE_CONFIG_DIR`) | No — applies to every repository on this machine |

The hook denies with a JSON `permissionDecision: "deny"` plus exit code 2, so
it blocks even in `bypassPermissions` mode and even if a shell profile prints
noise. Everything else exits 0 silently. See the
[bypass catalogue](skills/block-no-verify/references/bypass-catalogue.md).

## 🔌 MCP, permissions, and network

None — no MCP servers, no network access, no credentials.

## 📋 Requirements

| Requirement | Minimum | Check | Why |
| --- | --- | --- | --- |
| Claude Code | 2.1.222 | `claude --version` | Loads the skill and runs the hook; `plugin.json` carries `metadata`, a recognized manifest field from 2.1.222 — earlier versions treat it as unrecognized, which `claude plugin validate --strict` turns into an error; `${CLAUDE_SKILL_DIR}` needs 2.1.69 |
| Bash | 3.2 | `bash --version` | Runs the handler and the installer (macOS's stock `/bin/bash` 3.2 works) |
| jq | 1.6 | `jq --version` | Parses hook payloads and merges settings |
| Git | 2.18 | `git --version` | Assessment (`config --type=bool`, `rev-parse --git-common-dir`); the handler also reads Git aliases (read-only) to resolve `git <alias> -n` |
| Windows only | Git for Windows (Git Bash) | `bash --version` in Git Bash | Without Git Bash, Claude Code runs hooks in PowerShell and a Bash handler cannot run |

With **project scope**, everyone who runs Claude Code in the repository needs
Bash and jq too, because the committed hook runs on their machine.

Verification:

```bash
bash --version
jq --version
git --version
```

The skill's `preflight` step runs the same checks and stops on any failure. It
only checks; it never installs anything or asks for credentials. macOS 15+
ships `jq` at `/usr/bin/jq`; otherwise install it with your package manager
(`brew install jq`, `apt install jq`, `winget install jqlang.jq`).

## ✅ Verification

**Consumer smoke test** — after installing from the remote marketplace, in a
Git repository with a pre-commit hook:

```text
Assess whether this repository should install the block-no-verify policy.
```

Expected result: a report of hook tooling, signing, existing hooks, and a
scope recommendation, with no file changed. After you approve a scope, the
install output reports `0 failed` for the test suite and `DENY  git commit --no-verify -m wip`.

**Behavioral evals** — [`evals/`](evals/) run per the maintainer's eval protocol; results are
reported in the pull request or a dated file under `docs/audits/`, never here.

<details>
<summary>Maintainer checks</summary>

From the marketplace root:

```bash
make check
claude plugin validate plugins/block-no-verify --strict
bash plugins/block-no-verify/skills/block-no-verify/scripts/test-handler.sh
BNV_TEST_BASH=/bin/bash bash plugins/block-no-verify/skills/block-no-verify/scripts/test-handler.sh
claude plugin eval plugins/block-no-verify --ablation with-without --allow-tools Bash Write Edit --model claude-sonnet-5 --judge-model claude-opus-5 --no-publish --max-cost-usd 12
```

`make check` runs the handler suite under `bash` and `/bin/bash`, so CI covers it. The suite
ships inside the plugin, the one exception to suites living in the repository, because
`manage.sh install` and `verify` run it against the installed copy.

</details>

## 🧭 Compatibility

| Surface | Status | Last verified | Notes |
| --- | --- | --- | --- |
| Claude Code (CLI, Desktop, IDE) on macOS | ✅ Supported | 2026-09-19 | Installed from the remote marketplace with Claude Code 2.1.278 into a clean config: assess, preflight, install (project), verify, status, and uninstall all pass, and live decisions deny `--no-verify`, `core.hooksPath`, and `HUSKY=0` while allowing plain commits. Handler suite (331 cases) passes on bash 3.2.57 and 5.3.20; about 30 ms per typical command, about 200 ms worst case on 50 KB inputs |
| Claude Code (CLI, Desktop, IDE) on Linux / WSL | 🧪 Not tested | — | Same Bash handler and tests; not yet installed on a Linux or WSL machine |
| Claude Code on Windows with Git Bash | 🧪 Not tested | — | Designed for Git Bash; not yet run on Windows |
| Claude Code on Windows without Git Bash | ❌ Not supported | — | Hooks run in PowerShell; `preflight` refuses |
| Claude Code cloud sessions | ⚠️ Partial | — | Only project scope applies: cloud sessions don't read `~/.claude/settings.json` |
| Claude Cowork | ❌ Not supported | 2026-09-18 (GitHub issue, not docs) | Cowork's sandbox does not run settings hooks ([anthropics/claude-code#40495](https://github.com/anthropics/claude-code/issues/40495)); the skill reports and refuses to install. It detects Cowork through `CLAUDE_CODE_IS_COWORK`, which only that issue documents |
| Claude Chat (web, desktop) | ❌ Not supported | — | Plugins aren't used in Chat. |

## 💡 Examples

**Protect a repository**

```text
Protect this repo so you can never skip my husky hooks.
```

→ Claude assesses the repository, recommends `project` scope because `.husky/`
is present, and waits. After you answer "project", it installs, shows the test
summary and live decisions, and asks you to check `/hooks`.

**Check or remove**

```text
Is the no-verify protection installed? Then remove it from my user settings.
```

→ Claude runs `status`, confirms the scope with you, uninstalls only this
policy with a backup, and prints the backup path.

**What Claude sees when it tries a bypass**

```text
block-no-verify: git commit --no-verify skips hooks (--no-verify). Do not retry with another bypass. Run the command without it and fix the underlying hook or signing failure; if the hook itself is wrong, ask the user to fix or skip it themselves.
```

## 🔐 Security

| Access | What it may do |
| --- | --- |
| Read | Git config and hook files of the current repository; the three Claude Code settings files; managed settings; installed plugins' `hooks/hooks.json` (assessment only) |
| Write | Only after approval: one settings file (created if absent), the `hooks/` folder and one handler copy, backups under `<git common dir>/block-no-verify-backups/` (project and local scope) or `~/.claude/backups/block-no-verify/` (user scope, under `$CLAUDE_CONFIG_DIR` when set), and (local scope) `.git/info/exclude`. Uninstall deletes the handler, an emptied `hooks/` folder, and a project or local settings file left as `{}` |
| Process | `bash`, `jq`, `git`, and the bundled scripts, only when the skill runs; the auto-invoked skill runs the read-only `status` once per session while you commit (it reads the three settings files and installed handler copies). The installed hook runs `bash` + `jq` on each Bash/PowerShell tool call, and `git config --get alias.<name>` (read-only) when a command uses a Git alias |
| Network | Not used |
| Credentials | None |

- **Human approval:** every write happens only after you choose a scope in the conversation; uninstall asks you to confirm the scope.
- **Fail closed:** malformed payloads, unterminated quotes, and handler errors deny; if `jq` disappears, only commands that mention `git` are denied (the working directory and transcript path are ignored).
- **Trust:** review [`block-no-verify.sh`](skills/block-no-verify/assets/block-no-verify.sh) and [`manage.sh`](skills/block-no-verify/scripts/manage.sh) before installing in a critical repository.
- **Report a vulnerability** privately via the [security policy](../../SECURITY.md). Never post secrets in issues.

## 🚧 Limitations

| Limitation | What you'll see | Safe recovery |
| --- | --- | --- |
| Values hidden in variables, aliases, functions, or scripts run from files | A bypass inside `./release.sh` is not seen | Keep server-side controls; review scripts Claude writes |
| Constructs the parser can't resolve (`$GIT commit`, deep nesting, `xargs git` from a pipe) | A deny naming the construct, if the text mentions a bypass | Run the `git` command directly with literal arguments |
| Pathological command size (tens of KB of tokens) | Text-only check: denied if it mentions `git` and a bypass marker | Split the command |
| A committed project group whose handler wasn't committed | Hook errors on every shell call; nothing is blocked | Commit `.claude/hooks/block-no-verify.sh` with the settings; `status` warns |
| Hook timeout or a deleted handler | The call proceeds (Claude Code treats it as a non-blocking error) | `status` detects a missing handler; reinstall |
| `jq` is absent | The handler fails closed for Git: every shell call that mentions `git` is denied with that reason, and other calls pass | Install `jq` 1.6 or later, or remove the hook group by hand per [rollback](skills/block-no-verify/references/rollback.md); `manage.sh` itself refuses to run without `jq` |
| Cowork | No protection | Use Claude Code |
| Cowork detection relies on `CLAUDE_CODE_IS_COWORK`, an undocumented variable | If Cowork stops setting it, `preflight` may not refuse there; the policy still would not run | Check `/hooks` availability; report an issue |
| Commands outside Claude's shell tools | Not inspected | Branch protection and CI |

## ❓ FAQ

<details>
<summary>Does installing this plugin modify my project?</summary>

No. It only registers the skill. Files change only after you ask for the
protection and approve a scope.

</details>

<details>
<summary>Why a skill that installs a hook, instead of a plugin hook?</summary>

A plugin hook would be active in every project the moment you install the
plugin, with no choice of scope. Here you decide whether and where, the policy
keeps working if the plugin is updated or removed, and a team can commit it.

</details>

<details>
<summary>Why Bash instead of Python or Node?</summary>

Claude Code runs shell-form hooks through `sh`/Git Bash, so Bash is always
there. A hook whose interpreter is missing exits with a non-blocking error and
lets the command through; a Bash handler cannot silently lose its runtime.

</details>

## 📝 Changelog

Every published version is in [CHANGELOG.md](CHANGELOG.md), and each version is tagged
`block-no-verify--v<version>`. Current version: see the badge above.

## 📄 License

[Apache-2.0](LICENSE) © Nery Samuel Murillo.

---

<sub>Part of [claude-essentials](../../README.md) · [Report an issue](https://github.com/nerymurillohnd/claude-essentials/issues/new/choose) · [Security](../../SECURITY.md) · Not an official Anthropic product.</sub>
