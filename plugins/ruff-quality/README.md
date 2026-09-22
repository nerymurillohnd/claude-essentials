# 🐍 Ruff Quality

[![Version](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2Fnerymurillohnd%2Fclaude-essentials%2Fmain%2Fplugins%2Fruff-quality%2F.claude-plugin%2Fplugin.json&query=%24.version&label=version&color=blue)](CHANGELOG.md)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Kind](https://img.shields.io/badge/kind-bundle-8A2BE2)](../../docs/decisions/adr-0001-marketplace-distribution-model.md)
[![Claude Code](https://img.shields.io/badge/Claude_Code-not_tested-D97757?logo=claude&logoColor=white)](#-compatibility)
[![Claude Cowork](https://img.shields.io/badge/Claude_Cowork-not_tested-D97757?logo=claude&logoColor=white)](#-compatibility)
![Ruff](https://img.shields.io/badge/Ruff-%E2%89%A50.16-D7FF64?logo=ruff&logoColor=black)
![Bash](https://img.shields.io/badge/Bash-%E2%89%A53.2-4EAA25?logo=gnubash&logoColor=white)
![jq](https://img.shields.io/badge/jq-%E2%89%A51.6-555555)
![Hooks](https://img.shields.io/badge/hooks-3_events-orange)
![Network](https://img.shields.io/badge/network-none-lightgrey)

[← claude-essentials](../../README.md) · [Install](#-installation) · [Skills](#-skills) ·
[Security](#-security) · [Limitations](#-limitations) · [Changelog](CHANGELOG.md)

> **Every Python file Claude edits is fixed, formatted, and checked with your own Ruff, and Claude keeps working until what is left is fixed in the code, never silenced.**

**Kind:** `bundle` — a full workflow: multiple components working together.

Ruff Quality helps Python developers who use Claude Code keep Ruff green without
babysitting it. Its hook runs the Ruff you already have, in your project or
globally, with your own Ruff configuration, after every edit Claude makes to a
`.py`, `.pyw` or `.pyi` file. Its `ruff` skill teaches Claude to install,
configure, run, integrate, and diagnose Ruff from the official documentation. It does
**not** change your configuration or silence a finding on its own: a suppression or a
configuration edit waits for your answer.

> [!CAUTION]
> Installing the plugin turns its hooks on in the scope you install it in. From
> then on, every Python file Claude writes or edits there is rewritten by Ruff's
> safe fixes and formatter. A file that was never formatted is reformatted whole
> the first time Claude edits it.

## 🎯 What it does

| Scenario | How this plugin helps | Expected result |
| --- | --- | --- |
| Claude writes or edits a Python file | The hook applies Ruff's safe fixes, formats the file, and re-checks it with your configuration | The file passes Ruff, or Claude gets the exact findings left |
| Findings remain that Ruff cannot fix | Claude receives each finding with its rule code and fixes it in the code | Clean code, not suppressed code |
| Claude is about to add or widen `# noqa`, `flake8: noqa`, `ruff: noqa`/`ignore`/`disable`/`file-ignore`, `fmt: off`/`skip`, `yapf: disable` or `isort: skip` (or run `ruff check --add-noqa`/`--add-ignore`), or change `ruff.toml`, `.ruff.toml` or the Ruff settings of `pyproject.toml` | The hook asks you before the edit happens, naming the exact marker | You decide; an edit through Claude's file tools is never silenced behind your back |
| Claude tries to finish with findings left | At the end of the turn the hook re-checks every Python file it touched and keeps Claude working while the findings change, up to 7 attempts | The turn ends clean, or you get the list of what still fails |
| You ask Claude about Ruff | The `ruff` skill: install routes, configuration discovery, rule selection, migration from Black/isort/Flake8, editors, pre-commit and CI | Answers grounded in the official documentation |

## 🚫 What it does not do

- **Does not** install Ruff, run `uv`/`uvx`, download anything, or use the network.
- **Does not** write or change any Ruff configuration: Ruff finds your own, or uses its defaults.
- **Does not** apply unsafe fixes, or remove an import Claude just added (`F401` is reported, not auto-fixed).
- **Does not** check files Claude did not touch, files your Ruff configuration excludes, or `.ipynb` notebooks.
- **Not a fit when** you need enforcement for everyone, including humans and other tools: use pre-commit and CI for that (the `ruff` skill shows how). The hook is a guardrail for Claude, not a security boundary.

## ⚡ Installation

**Claude Code** — add the marketplace once, then install in the scope you want the hook in:

```text
/plugin marketplace add nerymurillohnd/claude-essentials
/plugin install ruff-quality@claude-essentials
```

From a terminal, `claude plugin install ruff-quality@claude-essentials -s user`
(every project), `-s project` (this repository, shared through
`.claude/settings.json`) or `-s local` (this repository, only you).

**Claude Cowork** — **Customize → Plugins → Add marketplace**, enter
`nerymurillohnd/claude-essentials`, then install **Ruff Quality** from the list.
See [Compatibility](#-compatibility) for what runs there.

> [!TIP]
> Installation is complete when `/plugin list` shows `ruff-quality` as enabled,
> `/hooks` lists its `PreToolUse`, `PostToolUse` and `Stop` hooks, and
> `/ruff-quality:ruff` appears in the `/` menu.

### What installing changes

| | Effect |
| --- | --- |
| **Does** | Registers the `ruff` skill and three hook events in Claude Code's plugin state, in the scope you chose; `-s project` also records the plugin in `.claude/settings.json`. |
| **Does not** | Write a Ruff configuration, copy scripts into your repository, or touch `~/.claude/hooks/`. |

### Update, disable, or remove

```text
/plugin marketplace update claude-essentials
/plugin disable ruff-quality@claude-essentials
/plugin uninstall ruff-quality@claude-essentials
```

Updating the plugin updates the hooks; run `/reload-plugins` to switch a running
session to the new version. To keep the skill but stop the hook, set the plugin's
`enabled` option to off in `/config`. In Cowork, use **Update** on the marketplace,
and **Uninstall** on the plugin under **Customize → Plugins**.

**Upgrading from 0.1.x:** 0.2.0 removes the `ruff-hooks` skill and its `manage.sh`, but not a
gate that 0.1.x installed into your settings: that gate is a standalone copy, and it would run
beside the new hooks. Remove it by hand, since the old gate denies Claude changing it: in the
settings file you installed it to (`.claude/settings.json`, `.claude/settings.local.json` or
`~/.claude/settings.json`), delete every hook group whose command contains
`ruff-quality-gate.sh`, then delete that handler from `.claude/hooks/` or `~/.claude/hooks/`.
Or restore the backup the installer printed (`<git dir>/ruff-quality-backups/` or
`~/.claude/backups/ruff-quality/`). Open `/hooks` to confirm only the plugin's hooks remain.

## 🧠 Skills

| Skill | Invoke | Claude uses it when | Invocation |
| --- | --- | --- | --- |
| [`ruff`](skills/ruff/SKILL.md) | `/ruff-quality:ruff` | It writes, edits, reviews, or fixes Python; or you ask about installing Ruff, its rules, configuration, migration from Black/isort/Flake8, pre-commit, CI, or the language server | Claude + user |

## 🤖 Agents

None — this plugin ships one skill and no agents.

## 🪝 Hooks and side effects

| Event | Matcher | What the handler does | Blocks? |
| --- | --- | --- | --- |
| `PreToolUse` | `Write\|Edit` on `.py`, `.pyw`, `.pyi`, `ruff.toml`, `.ruff.toml`, `pyproject.toml`; `Bash` | Asks you before an edit adds a suppression comment or changes Ruff configuration, and before a command writes one | No — it asks, never denies |
| `PostToolUse` | `Write\|Edit` on `.py`, `.pyw`, `.pyi` | `ruff check --fix --no-unsafe-fixes --unfixable F401`, `ruff format`, `ruff check` on the edited file; rewrites it | No (the edit already happened); findings left go to Claude |
| `Stop` | — | Re-fixes, re-formats and re-checks every Python file this session touched | Yes: keeps Claude working while the findings change, at most 7 times; then a message lists what still fails and those files are left alone until edited again |

The handler is [`scripts/ruff-gate.sh`](scripts/ruff-gate.sh). It runs the first Ruff
it finds: the project's own (`.venv/bin/ruff` or `venv/bin/ruff` between the edited
file and the project root, owned by you), then `ruff` on `PATH`, then `~/.local/bin`, `/opt/homebrew/bin` and
`/usr/local/bin`. Ruff then finds your configuration as it always does: the nearest
`ruff.toml`, `.ruff.toml` or `pyproject.toml` with `[tool.ruff]`, else your
user-level file, else its defaults; a file it excludes is reported as not checked.
Every result reaches you as one `ruff-quality` line (see [Examples](#-examples)), and
Claude is told when the hook rewrote a file so it re-reads it. Per-session state (the files touched and the Stop
count) lives in `${CLAUDE_PLUGIN_DATA}` (or, when Claude Code does not set it, a private
`$TMPDIR/ruff-quality-<uid>`) and is pruned after 7 days.

## 🔌 MCP, permissions, and network

None — no MCP servers, no network access, no credentials.

## 📋 Requirements

| Requirement | Minimum | Check | Why |
| --- | --- | --- | --- |
| Claude Code | 2.1.222 | `claude --version` | Loads the skill and the hooks; `plugin.json` carries `metadata`, a recognized manifest field from 2.1.222. |
| Ruff | 0.16 | `ruff --version` | Every hook step; install it in the project or globally. Without a Ruff configuration the hook applies Ruff's default rules, and the skill describes the 0.16 defaults |
| Bash | 3.2 | `bash --version` | Runs the handler (macOS's stock `/bin/bash` 3.2 works) |
| jq | 1.6 | `jq --version` | Reads hook payloads and writes hook answers |
| Windows only | Git for Windows (Git Bash) | `bash --version` in Git Bash | Without Git Bash, hooks run in PowerShell and a Bash handler cannot run |

The skill works without any of them. With project scope, everyone who runs Claude
Code in the repository needs them too.

```bash
ruff --version
bash --version
jq --version
```

Install Ruff as a project dev dependency (`uv add --dev ruff`) or globally
(`uv tool install ruff`, `pipx install ruff`, `brew install ruff`). Without Ruff or
`jq`, the hook tells you once per session and blocks nothing.

## ✅ Verification

**Consumer smoke test** — after installing from the remote marketplace, in a
project with Ruff installed:

```text
Create demo.py with a function that returns f"hello" and an unused variable, then tell me what the hook said.
```

Expected result: a `ruff-quality` line after the write, `demo.py` rewritten by the
safe fixes and the formatter, and Claude fixing the finding Ruff could not fix
(`F841`) before it finishes.

**Behavioral evals** — [`evals/`](evals/) run per the maintainer's eval protocol; results are
reported in the pull request or a dated file under `docs/audits/`, never here.

<details>
<summary>Maintainer checks</summary>

From the marketplace root:

```bash
make check
claude plugin validate plugins/ruff-quality --strict
scripts/plugin_validation/suites/ruff-quality/test-gate.sh
claude plugin eval plugins/ruff-quality --scaffold --allow-tools Bash Write Edit --no-publish --max-cost-usd 15
```

`make check` runs the suite under `bash` and under `/bin/bash`. The suite lives in
the repository, not in the plugin, so it is never installed.

</details>

## 🧭 Compatibility

| Surface | Status | Last verified | Notes |
| --- | --- | --- | --- |
| Claude Code (CLI, Desktop, IDE) on macOS | 🧪 Not tested | 2026-09-22, local checkout only | The hook suite passes on bash 3.2.57 and 5.3.20 with Ruff 0.16.8, and a live `--plugin-dir` session on Claude Code 2.1.278 fired every hook (fix, block, clean, Stop, ask); not yet installed from the remote marketplace |
| Claude Code on Linux / WSL | 🧪 Not tested | — | Same Bash handler; CI runs the suite on Linux |
| Claude Code on Windows with Git Bash | 🧪 Not tested | — | Designed for Git Bash; not yet run on Windows |
| Claude Code on Windows without Git Bash | ❌ Not supported | — | Hooks run in PowerShell and the Bash handler cannot run |
| Claude Code cloud sessions | 🧪 Not tested | — | The hook runs only when Ruff and `jq` are installed in the cloud environment |
| Claude Cowork | 🧪 Not tested | — | The `ruff` skill should work; whether Cowork runs plugin hooks is unverified |
| Claude Chat (web, desktop) | ❌ Not supported | — | Plugins aren't used in Chat. |

## 💡 Examples

**What Claude sees after an edit**

```text
ruff-quality: calc.py still fails Ruff after the safe fixes and formatting (the hook may have rewritten it; re-read it first). Fix each finding in the code; a suppression comment or a configuration change is not a fix and needs the user's confirmation. Findings:
calc.py:2:21: F821 Undefined name `totl`
```

**What you see**

```text
ruff-quality: calc.py has Ruff findings left; Claude is fixing them
ruff-quality: 1 Python file(s) still fail Ruff; Claude keeps working (1/7)
ruff-quality ✓ 1 Python file(s) touched this session pass Ruff
```

**When Claude reaches for a suppression**

```text
ruff-quality: Claude wants to add or widen a suppression in calc.py: # noqa: f821. Allow it only if you want that finding silenced instead of fixed.
```

## 🔐 Security

| Access | What it may do |
| --- | --- |
| Read | The Python files Claude edits; the file an edit targets, to compare suppressions and `[tool.ruff]` tables before and after |
| Write | The Python files Claude edits (Ruff's safe fixes and formatting) and per-session state in `${CLAUDE_PLUGIN_DATA}`, else `$TMPDIR/ruff-quality-<uid>` |
| Process | `bash`, `jq`, the bundled handler, and a `ruff` executable: one you own in a `.venv/` or `venv/` inside the project (a repository can commit one, so it runs on Claude's first edit there, as an editor would), else the one on `PATH` or in `~/.local/bin`, `/opt/homebrew/bin`, `/usr/local/bin`. Never one above the project root |
| Network | Not used |
| Credentials | None |

- **Human approval:** a suppression or a Ruff configuration change reaches your permission prompt before it happens; the hook never denies and never edits configuration.
- **Never blocks on its own failure:** a missing tool, a malformed payload, an unwritable state directory, or a Ruff tool or configuration error (such as a `required-version` mismatch) ends in a message to you, never in Claude being kept working.
- **Trust:** review [`scripts/ruff-gate.sh`](scripts/ruff-gate.sh) and [`hooks/hooks.json`](hooks/hooks.json) before installing in a critical repository.
- **Report a vulnerability** privately via the [security policy](../../SECURITY.md). Never post secrets in issues.

## 🚧 Limitations

| Limitation | What you'll see | Safe recovery |
| --- | --- | --- |
| A file that was never formatted is reformatted whole on its first edit | A diff larger than the change Claude made | Accepted by design; format the project once on purpose, or leave the plugin off where you don't want Ruff's style |
| Files written through `Bash` (`sed`, heredocs) are not fixed after the command | No `ruff-quality` line for that file | The guard still asks before a Bash command writes a suppression; ask Claude to edit with its file tools |
| `.ipynb` notebooks are not checked | No `ruff-quality` line for a notebook | Run `ruff check` on notebooks yourself |
| The Bash guard is textual | It asks only for commands with a visible write (`>`, `tee`, `sed -i`, heredocs); `cp`, `mv` or a script Claude writes and runs are not caught | Review what Claude runs; the Python file's own edits through Write and Edit are still checked |
| Ruff not installed | `ruff-quality: Ruff is not installed …`, once per session (on every edit when no state directory can be written); nothing is checked | Install Ruff in the project or globally |
| `jq` not installed | `ruff-quality: jq is not installed …`, once per session (on every edit when no state directory can be written); nothing is checked | Install `jq` |
| Stop limit reached, or no change between two attempts | `ruff-quality ✗ gave up after 7 attempts …` or `… with no change since the last attempt …`, with the findings | Fix what is listed or ask Claude to; the hook leaves those files alone until they are edited again |
| A file your Ruff configuration excludes | `ruff-quality: … is excluded by the project's Ruff configuration, so it was not checked` | Intended; change `exclude` if you want it checked |
| Hook timeout (10 s guard, 60 s post, 120 s Stop) | The call proceeds without the hook's answer | Measured runs take well under a second per file; report very slow projects |
| Cowork | Hooks may not run | Use Claude Code |
| Ruff passing is not proof of correctness | — | Tests and review still apply |

## ❓ FAQ

<details>
<summary>Can Claude add a <code># noqa</code> if I ask for it?</summary>

Yes, if you confirm it: the hook asks you in the permission prompt before the edit,
and your answer decides. It never adds one on its own and never denies one you want.

</details>

<details>
<summary>How is this different from Astral's official Ruff skill?</summary>

Astral's `astral:ruff` skill (in `astral-sh/claude-code-plugins`) teaches Ruff and
installs no hooks. This plugin adds a hook that fixes, formats, and checks every
Python file Claude edits with your own Ruff and configuration, asks you before any
suppression, and never runs `uvx` in a hook. It is not affiliated with Astral.

</details>

## 📝 Changelog

Every published version is in [CHANGELOG.md](CHANGELOG.md), and each version is tagged
`ruff-quality--v<version>`. Current version: see the badge above.

## 📄 License

[Apache-2.0](LICENSE) © Nery Samuel Murillo.

---

<sub>Part of [claude-essentials](../../README.md) · [Report an issue](https://github.com/nerymurillohnd/claude-essentials/issues/new/choose) · [Security](../../SECURITY.md) · Not an official Anthropic product.</sub>
