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
![Hooks](https://img.shields.io/badge/hooks-3_events-orange)
![Network](https://img.shields.io/badge/network-none-lightgrey)

[← claude-essentials](../../README.md) · [Install](#-installation) · [Skills](#-skills) ·
[Security](#-security) · [Limitations](#-limitations) · [Changelog](CHANGELOG.md)

> **Every shell script Claude edits is formatted with your shfmt and checked with your ShellCheck, and Claude keeps working until what is left is fixed in the script, never disabled.**

**Kind:** `bundle` — a full workflow: multiple components working together.

Shell Quality helps developers who use Claude Code keep their shell scripts clean
without babysitting them. Its hook runs the shfmt and ShellCheck you already have,
in your project or globally, with your own `.shellcheckrc` and `.editorconfig`,
after every edit Claude makes to a `.sh` or `.bash` file. Its `shell-lint` skill
teaches Claude to install, configure, run, integrate, and fix findings with both
tools from the official documentation. It does **not** change your configuration or
silence a finding on its own: a directive or a configuration edit waits for your answer.

> [!CAUTION]
> Installing the plugin turns its hooks on in the scope you install it in. From
> then on, every `.sh` and `.bash` file Claude writes or edits there is rewritten
> by shfmt. A script that was never formatted is reformatted whole the first time
> Claude edits it.

## 🎯 What it does

| Scenario | How this plugin helps | Expected result |
| --- | --- | --- |
| Claude writes or edits a shell script | The hook formats it with shfmt (your EditorConfig) and checks it with ShellCheck (your rc) | The script passes, or Claude gets the exact findings left |
| ShellCheck reports findings | Claude receives each finding with its `SC` code and fixes it in the script | Clean scripts, not disabled checks |
| Claude is about to add `# shellcheck disable=` or `source=/dev/null`, or change `.shellcheckrc` or the shfmt keys of `.editorconfig` | The hook asks you before the edit happens | You decide; nothing is silenced behind your back |
| Claude tries to finish with findings left | At the end of the turn the hook re-checks every script it touched and keeps Claude working, up to 7 attempts | The turn ends clean, or you get the list of what still fails |
| You ask Claude about ShellCheck or shfmt | The `shell-lint` skill: install routes, rc and EditorConfig discovery, fixes for the common `SC` codes, portability, editors, pre-commit and CI | Answers grounded in the official documentation |

## 🚫 What it does not do

- **Does not** install ShellCheck or shfmt, download anything, or use the network.
- **Does not** write or change `.shellcheckrc`, `.editorconfig` or any other configuration.
- **Does not** apply ShellCheck's suggested fixes: they can change behaviour, so Claude fixes each finding.
- **Does not** check files Claude did not touch, extensionless scripts, or zsh scripts (ShellCheck does not support zsh).
- **Not a fit when** you need enforcement for everyone, including humans and other tools: use pre-commit and CI for that (the `shell-lint` skill shows how). The hook is a guardrail for Claude, not a security boundary.

## ⚡ Installation

**Claude Code** — add the marketplace once, then install in the scope you want the hook in:

```text
/plugin marketplace add nerymurillohnd/claude-essentials
/plugin install shell-quality@claude-essentials
```

From a terminal, `claude plugin install shell-quality@claude-essentials -s user`
(every project), `-s project` (this repository, shared through
`.claude/settings.json`) or `-s local` (this repository, only you).

**Claude Cowork** — **Customize → Plugins → Add marketplace**, enter
`nerymurillohnd/claude-essentials`, then install **Shell Quality** from the list.
See [Compatibility](#-compatibility) for what runs there.

> [!TIP]
> Installation is complete when `/plugin list` shows `shell-quality` as enabled,
> `/hooks` lists its `PreToolUse`, `PostToolUse` and `Stop` hooks, and
> `/shell-quality:shell-lint` appears in the `/` menu.

### What installing changes

| | Effect |
| --- | --- |
| **Does** | Registers the `shell-lint` skill and three hook events in Claude Code's plugin state, in the scope you chose; `-s project` also records the plugin in `.claude/settings.json`. |
| **Does not** | Write a `.shellcheckrc` or `.editorconfig`, copy scripts into your repository, or touch `~/.claude/hooks/`. |

### Update, disable, or remove

```text
/plugin marketplace update claude-essentials
/plugin disable shell-quality@claude-essentials
/plugin uninstall shell-quality@claude-essentials
```

Updating the plugin updates the hooks; run `/reload-plugins` to switch a running
session to the new version. To keep the skill but stop the hook, set the plugin's
`enabled` option to off in `/config`. In Cowork, use **Update** on the marketplace,
and **Uninstall** on the plugin under **Customize → Plugins**.

## 🧠 Skills

| Skill | Invoke | Claude uses it when | Invocation |
| --- | --- | --- | --- |
| [`shell-lint`](skills/shell-lint/SKILL.md) | `/shell-quality:shell-lint` | It writes, edits, reviews, or fixes a shell script; or you ask about an `SC` code, `.shellcheckrc`, the shfmt keys of EditorConfig, portability, pre-commit or CI | Claude + user |

## 🤖 Agents

None — this plugin ships one skill and no agents.

## 🪝 Hooks and side effects

| Event | Matcher | What the handler does | Blocks? |
| --- | --- | --- | --- |
| `PreToolUse` | `Write\|Edit` on `.sh`, `.bash`, `.shellcheckrc`, `shellcheckrc`, `.editorconfig`; `Bash` | Asks you before an edit adds a suppression directive, changes `.shellcheckrc`, or changes the sections or shfmt keys of `.editorconfig`, and before a command writes one | No — it asks, never denies |
| `PostToolUse` | `Write\|Edit` on `.sh`, `.bash` | `shfmt -w` (no style flags, so your EditorConfig decides), then `shellcheck -x` on the edited script; rewrites it | No (the edit already happened); findings left go to Claude |
| `Stop` | — | Re-formats and re-checks every script this session touched | Yes: keeps Claude working while the findings change, at most 7 times; then a message lists what still fails and those scripts are left alone until edited again |

The handler is [`scripts/shell-gate.sh`](scripts/shell-gate.sh). It runs the first
shfmt and ShellCheck it finds: the project's own (`.venv/bin/` or `venv/bin/` between
the edited script and the project root, owned by you, for example from `shellcheck-py` and `shfmt-py`), then `PATH`,
then `~/.local/bin`, `/opt/homebrew/bin` and `/usr/local/bin`. Each tool then finds
your configuration as it always does: ShellCheck the nearest `.shellcheckrc`, then
`~/.shellcheckrc`, then `$XDG_CONFIG_HOME/shellcheckrc`, plus `SHELLCHECK_OPTS`,
which every ShellCheck report names when it is set; shfmt the `.editorconfig` files above the
script. Every result reaches you as one `shell-quality` line (see [Examples](#-examples)), and
Claude is told when shfmt rewrote a script so it re-reads it. Per-session
state (the scripts touched and the Stop count) lives in `${CLAUDE_PLUGIN_DATA}` (or, when
Claude Code does not set it, a private `$TMPDIR/shell-quality-<uid>`) and is pruned after 7 days.

## 🔌 MCP, permissions, and network

None — no MCP servers, no network access, no credentials.

## 📋 Requirements

| Requirement | Minimum | Check | Why |
| --- | --- | --- | --- |
| Claude Code | 2.1.222 | `claude --version` | Loads the skill and the hooks; `plugin.json` carries `metadata`, a recognized manifest field from 2.1.222. The `enabled` row in `/config` needs 2.1.269 |
| ShellCheck | 0.10 | `shellcheck --version` | Checks every edited script. 0.10 is the first release that reads the `extended-analysis` key and `--rcfile` the skill's configuration guidance uses; tested with 0.11.0 |
| shfmt | 3.12 | `shfmt --version` | Formats every edited script. 3.12 is the first release that reads the `simplify` and `minify` EditorConfig keys; the `[[shell]]` sections the skill describes need 3.13; tested with 3.14.1 |
| Bash | 3.2 | `bash --version` | Runs the handler (macOS's stock `/bin/bash` 3.2 works) |
| jq | 1.6 | `jq --version` | Reads hook payloads and writes hook answers |
| Windows only | Git for Windows (Git Bash) | `bash --version` in Git Bash | Without Git Bash, hooks run in PowerShell and a Bash handler cannot run |

The skill works without any of them. With project scope, everyone who runs Claude
Code in the repository needs them too.

```bash
shellcheck --version
shfmt --version
bash --version
jq --version
```

Install them with your package manager (`brew install shellcheck shfmt`), as
project dev dependencies (`shellcheck-py`, `shfmt-py`), or as release binaries;
Ubuntu's apt may ship a ShellCheck older than 0.10. Without them, or without `jq`,
the hook tells you once per session and blocks nothing.

## ✅ Verification

**Consumer smoke test** — after installing from the remote marketplace, in a
project with ShellCheck and shfmt installed:

```text
Create hello.sh that prints its first argument without quoting it, then tell me what the hook said.
```

Expected result: a `shell-quality` line after the write, and Claude quoting the
expansion because ShellCheck reported `SC2086`, before it finishes.

**Behavioral evals** — [`evals/`](evals/) run per the maintainer's eval protocol; results are
reported in the pull request or a dated file under `docs/audits/`, never here.

<details>
<summary>Maintainer checks</summary>

From the marketplace root:

```bash
make check
claude plugin validate plugins/shell-quality --strict
scripts/plugin_validation/suites/shell-quality/test-gate.sh
claude plugin eval plugins/shell-quality --scaffold --allow-tools Bash Write Edit --no-publish --max-cost-usd 15
```

`make check` runs the suite under `bash` and under `/bin/bash`. The suite lives in
the repository, not in the plugin, so it is never installed.

</details>

## 🧭 Compatibility

| Surface | Status | Last verified | Notes |
| --- | --- | --- | --- |
| Claude Code (CLI, Desktop, IDE) on macOS | 🧪 Not tested | 2026-09-22, local checkout only | The hook suite passes on bash 3.2.57 and 5.3.20 with ShellCheck 0.11.0 and shfmt 3.14.1; not yet installed from the remote marketplace |
| Claude Code on Linux / WSL | 🧪 Not tested | — | Same Bash handler; CI runs the suite on Linux |
| Claude Code on Windows with Git Bash | 🧪 Not tested | — | Designed for Git Bash; not yet run on Windows |
| Claude Code on Windows without Git Bash | ❌ Not supported | — | Hooks run in PowerShell and the Bash handler cannot run |
| Claude Code cloud sessions | 🧪 Not tested | — | The hook runs only when ShellCheck, shfmt and `jq` are installed in the cloud environment |
| Claude Cowork | 🧪 Not tested | — | The `shell-lint` skill should work; whether Cowork runs plugin hooks is unverified |
| Claude Chat (web, desktop) | ❌ Not supported | — | Plugins aren't used in Chat. |

## 💡 Examples

**What Claude sees after an edit**

```text
shell-quality: bin/deploy.sh still fails ShellCheck after formatting (the hook may have rewritten it; re-read it first). Fix each finding in the script (read a code's explanation at https://www.shellcheck.net/wiki/SC<code>); a # shellcheck disable= directive or a configuration change is not a fix and needs the user's confirmation. Findings:
bin/deploy.sh:3:6: note: Double quote to prevent globbing and word splitting. [SC2086]
```

**What you see**

```text
shell-quality: bin/deploy.sh has findings left; Claude is fixing them
shell-quality: 1 shell script(s) still fail; Claude keeps working (1/7)
shell-quality ✓ 1 shell script(s) touched this session pass shfmt and ShellCheck
```

**When Claude reaches for a directive**

```text
shell-quality: Claude wants to add or widen a ShellCheck directive in bin/deploy.sh: # shellcheck disable=sc2086. Allow it only if you want that finding silenced instead of fixed.
```

## 🔐 Security

| Access | What it may do |
| --- | --- |
| Read | The shell scripts Claude edits; the file an edit targets, to compare directives and shfmt keys before and after |
| Write | The shell scripts Claude edits (shfmt formatting) and per-session state in `${CLAUDE_PLUGIN_DATA}`, else `$TMPDIR/shell-quality-<uid>` |
| Process | `bash`, `jq`, the bundled handler, and `shfmt` and `shellcheck` executables: ones you own in a `.venv/` or `venv/` inside the project (a repository can commit them, so they run on Claude's first edit there, as an editor would), else the ones on `PATH` or in `~/.local/bin`, `/opt/homebrew/bin`, `/usr/local/bin`. Never ones above the project root |
| Network | Not used |
| Credentials | None |

- **Human approval:** a suppression or a configuration change reaches your permission prompt before it happens; the hook never denies and never edits configuration.
- **Never blocks on its own failure:** a missing tool, a malformed payload, an unwritable state directory, or a ShellCheck tool or configuration error ends in a message to you, never in Claude being kept working.
- **Trust:** review [`scripts/shell-gate.sh`](scripts/shell-gate.sh) and [`hooks/hooks.json`](hooks/hooks.json) before installing in a critical repository.
- **Report a vulnerability** privately via the [security policy](../../SECURITY.md). Never post secrets in issues.

## 🚧 Limitations

| Limitation | What you'll see | Safe recovery |
| --- | --- | --- |
| A script that was never formatted is reformatted whole on its first edit | A diff larger than the change Claude made | Accepted by design; format the project once on purpose, or leave the plugin off where you don't want shfmt's style |
| Only `.sh` and `.bash` files are checked | No `shell-quality` line for an extensionless script or a `.bats` file | Ask Claude to run ShellCheck on it; the `shell-lint` skill covers it |
| zsh scripts are skipped | `shell-quality: … is a zsh script; ShellCheck does not support zsh …` | Review zsh scripts another way |
| Files written through `Bash` (`sed`, heredocs) are not checked after the command | No `shell-quality` line for that file | The guard still asks before a Bash command writes a directive; ask Claude to edit with its file tools |
| `SHELLCHECK_OPTS` in your environment applies, including any `-e` exclusions | Every report says `(SHELLCHECK_OPTS=… applies)` | Unset it, or move what you want into `.shellcheckrc` |
| The Bash guard is textual | It asks only for commands with a visible write (`>`, `tee`, `sed -i`, heredocs); `cp`, `mv`, `rm` or a script Claude writes and runs are not caught | Review what Claude runs; the script's own edits through Write and Edit are still checked |
| ShellCheck or shfmt not installed | `shell-quality: … not installed …`, once per session (on every edit when no state directory can be written); nothing is checked | Install them in the project or globally |
| `jq` not installed | `shell-quality: jq is not installed …`, once per session (on every edit when no state directory can be written); nothing is checked | Install `jq` |
| Stop limit reached, or no change between two attempts | `shell-quality ✗ gave up after 7 attempts …` or `… with no change since the last attempt …`, with the findings | Fix what is listed or ask Claude to; the hook leaves those scripts alone until they are edited again |
| Your `.editorconfig` sets a `shell_variant` the script is not written in | `… could not be checked … a tool or configuration error` | Fix `.editorconfig` (a `[[bash]]` section, or `shell_variant = auto`); Claude does not rewrite a correct script to fit it |
| Hook timeout (10 s guard, 60 s post, 120 s Stop) | The call proceeds without the hook's answer | Measured runs take well under a second per script; report very slow projects |
| Cowork | Hooks may not run | Use Claude Code |
| Passing ShellCheck is not proof of correctness | — | Tests and review still apply |

## ❓ FAQ

<details>
<summary>Can Claude add a <code># shellcheck disable</code> if I ask for it?</summary>

Yes, if you confirm it: the hook asks you in the permission prompt before the edit,
and your answer decides. It never adds one on its own and never denies one you want.

</details>

<details>
<summary>Why not a one-line <code>shfmt -w -i 2 &amp;&amp; shellcheck</code> hook?</summary>

Hooks get the file path as JSON on stdin, not as a variable; a plain `shellcheck`
exit 1 never reaches Claude as feedback; and `-i 2` makes shfmt ignore your
EditorConfig. This hook reads the payload, hands the findings to Claude, keeps your
EditorConfig in charge, and adds the guard and the end-of-turn check.

</details>

## 📝 Changelog

Every published version is in [CHANGELOG.md](CHANGELOG.md), and each version is tagged
`shell-quality--v<version>`. Current version: see the badge above.

## 📄 License

[Apache-2.0](LICENSE) © Nery Samuel Murillo.

---

<sub>Part of [claude-essentials](../../README.md) · [Report an issue](https://github.com/nerymurillohnd/claude-essentials/issues/new/choose) · [Security](../../SECURITY.md) · Not an official Anthropic product.</sub>
