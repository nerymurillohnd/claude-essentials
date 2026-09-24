# 📚 Agent Self-Knowledge

[![Version](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2Fnerymurillohnd%2Fclaude-essentials%2Fmain%2Fplugins%2Fagent-self-knowledge%2F.claude-plugin%2Fplugin.json&query=%24.version&label=version&color=blue)](CHANGELOG.md)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Kind](https://img.shields.io/badge/kind-skill--only-8A2BE2)](../../docs/decisions/adr-0001-marketplace-distribution-model.md)
[![Claude Code](https://img.shields.io/badge/Claude_Code-partial-D97757?logo=claude&logoColor=white)](#-compatibility)
[![Claude Cowork](https://img.shields.io/badge/Claude_Cowork-not_tested-D97757?logo=claude&logoColor=white)](#-compatibility)
![Python](https://img.shields.io/badge/Python-%E2%89%A53.12-3776AB?logo=python&logoColor=white)
![Network](https://img.shields.io/badge/network-required-lightgrey)

[← claude-essentials](../../README.md) · [Install](#-installation) · [Skill](#-skills) ·
[Security](#-security) · [Limitations](#-limitations) · [Changelog](CHANGELOG.md)

> **Claude stops answering from memory about Claude Code, Cowork and the Claude API, researches every page the topic lives on, and cites the exact sentence and URL for each claim.**

**Kind:** `skill-only` — exactly one skill, nothing else.

Agent Self-Knowledge helps anyone building with Claude Code, Cowork, the Claude apps, the Agent
SDK or the Claude API get answers that are true today rather than true at training time. Before
Claude answers, plans or writes a configuration, its skill runs one research command that reads
every live documentation page related to the task, follows the links between them and checks
six months of release notes; the answer quotes the sentences that settle it and lists what could
not be verified. It does **not** answer questions about your own code or other products.

> [!CAUTION]
> This plugin reaches the network and writes to your disk. Its skill grants its own bundled
> Python script through `allowed-tools`, so research runs without a per-command approval
> prompt; the script's `raw` command fetches any `https://` URL it is given; and each research
> run writes a folder of a few megabytes, keeping the last 10. Review
> `skills/claude-code-docs/scripts/ccdocs.py` before enabling this in a sensitive environment.

## 🎯 What it does

| Scenario | How this plugin helps | Expected result |
| --- | --- | --- |
| You're writing a plugin, hook, skill, subagent, MCP or settings file. | Reads every page of the areas the task touches — for a plugin's subagent: subagents, skills, plugins, marketplaces, hooks, MCP — and the sections those pages link to. | The constraint that only another page states (for example, fields a plugin's subagent ignores) is found and quoted before the file is written. |
| You ask how a feature works or which option to pick. | Keeps only the sections about the topic from each live page, across Claude Code, the Help Center and the Platform docs. | An answer with one verbatim sentence and its section URL per claim. |
| Claude is about to say a feature doesn't exist. | Requires three misses — research, a full-text search, the changelog — before any negative claim. | "Not found as of `<date>`, v`<version>`", with where it looked, instead of a wrong denial. |
| The docs changed recently. | Checks the Claude Code changelog, the Claude apps release notes and the Platform release notes for the last six months. | What changed, in which version or on which date. |

## 🚫 What it does not do

- **Does not** answer questions about your own code, your project's stack or other AI tools.
- **Does not** guarantee it loads on its own. Claude decides; you can always invoke it by name.
- **Does not** write to your repository, install anything, or use credentials.
- **Does not** read documentation through WebFetch: pages are downloaded whole, never summarized.
- **Not a fit when** the question is about how your code behaves rather than how these products behave.

## ⚡ Installation

**Claude Code** — add the marketplace once, then install:

```text
/plugin marketplace add nerymurillohnd/claude-essentials
/plugin install agent-self-knowledge@claude-essentials
```

**Claude Cowork** — **Customize → Plugins → Add marketplace**, enter
`nerymurillohnd/claude-essentials`, then install **Agent Self-Knowledge** from the list.

> [!TIP]
> Installation is complete when `/plugin list` shows `agent-self-knowledge` as enabled
> and `/agent-self-knowledge:claude-code-docs` appears in the slash-command menu.

### What installing changes

| | Effect |
| --- | --- |
| **Does** | Registers one skill and its bundled script in Claude Code's plugin cache. |
| **Does not** | Touch your project, your settings, or the network — nothing runs until the skill is used. |

### Update, disable, or remove

```text
/plugin marketplace update claude-essentials
/plugin disable agent-self-knowledge@claude-essentials
/plugin uninstall agent-self-knowledge@claude-essentials
```

In Cowork, use **Update** on the marketplace, and **Uninstall** on the plugin
under **Customize → Plugins**. Uninstalling does not delete the documentation cache under
`${XDG_CACHE_HOME:-~/.cache}/ccdocs` or the research folders under
`~/.claude/plugins/data/`; remove them by hand if you want the disk space back.

## 🧠 Skills

| Skill | Invoke | Claude uses it when | Invocation |
| --- | --- | --- | --- |
| [`claude-code-docs`](skills/claude-code-docs/SKILL.md) | `/agent-self-knowledge:claude-code-docs` | A question, plan, integration or configuration file depends on how Claude Code, Cowork, the Claude apps, the Agent SDK or the Claude API work today, or Claude is about to say a feature doesn't exist. | Claude + user |

## 🤖 Agents

None — this plugin ships exactly one skill and no agents.

## 🪝 Hooks and side effects

None — this plugin registers no hooks. Its side effects are the documentation cache and the
research folders described under [Security](#-security).

## 🔌 MCP, permissions, and network

The plugin registers no MCP server and sends no credentials. Its skill's `allowed-tools` grants
its own bundled script and `claude --version`, so research runs without a prompt for each
command. It also names two tools of Anthropic's docs MCP server (`claude-code-docs`) as an
optional fallback; since this plugin does not bundle that server, those two grants have no
effect unless the server is added. Any URL taken from that server goes through
`ccdocs.py url` before it is cited, because its paths omit `/docs` and
`https://code.claude.com/en/<page>` redirects to a marketing page.

- **Least privilege:** read-only access to public documentation; the only writes are the cache
  and the research folders.
- **Cowork:** not tested; see [Compatibility](#-compatibility).

## 📋 Requirements

> [!IMPORTANT]
> **Requires Python 3.12 or later as `python3` on your `PATH`.** The skill runs
> `python3 …/ccdocs.py`, and the script stops with one line naming the version it found when
> `python3` is older. The Python that ships with the Xcode Command Line Tools on macOS (3.9) is
> too old: install 3.12 or later from python.org, with Homebrew, or with `uv python install`.

| Requirement | Minimum | Check | Why |
| --- | --- | --- | --- |
| Claude Code | 2.1.222 | `claude --version` | `plugin.json` carries `metadata`, a recognized manifest field only from that version. |
| Python | 3.12 | `python3 -V` | `ccdocs.py` is standard-library only: no packages, no virtual environment. |
| `python3` on `PATH` | — | `command -v python3` | The `allowed-tools` grant invokes it by name. |
| Network access | — | — | Research reads `code.claude.com`, `support.claude.com`, `platform.claude.com`, `raw.githubusercontent.com` and `registry.npmjs.org`. |
| Writable cache and data directories | — | — | `${XDG_CACHE_HOME:-~/.cache}/ccdocs` for the cache; `${CLAUDE_PLUGIN_DATA}/research` for research folders. |

`claude` on `PATH` is optional: with it, research compares your build with the npm latest; without
it, the skill asks you for `claude --version`.

Five environment variables change how the script runs, all optional:

| Variable | Default | Effect |
| --- | --- | --- |
| `CCDOCS_CACHE_TTL` | `900` | Seconds a fetched page stays cached. `0` disables caching. |
| `CCDOCS_CORPUS_TTL` | `3600` | Seconds the full Claude Code corpus stays cached. |
| `CCDOCS_ANCHOR_TTL` | `3600` | Seconds the anchors read from rendered pages stay cached. |
| `CCDOCS_LANG` | `en` | Documentation language segment of Claude Code URLs. |
| `XDG_CACHE_HOME` | `~/.cache` | Cache root. An empty or relative value is ignored. |

An invalid value for any of the three TTLs stops the command with a one-line error.

## ✅ Verification

**Consumer smoke test** — after installing from the remote marketplace, in an empty directory:

```text
I'm building a Claude Code plugin for a public GitHub marketplace. Its subagent must always use a skill from the same plugin and have its own hook and MCP server. How do I set it up so it works when someone installs it from the marketplace?
```

Expected result: Claude runs the skill's research command, then answers that a plugin's subagent
ignores the `hooks` and `mcpServers` frontmatter fields, quoting that sentence with its URL, and
declares the hook and the MCP server at plugin level instead.

**Behavioral evals** — [`evals/`](evals/) run per the maintainer's eval protocol; results are
reported in the pull request or a dated file under `docs/audits/`, never here.

<details>
<summary>Maintainer checks</summary>

From the marketplace root:

```bash
make check
claude plugin validate plugins/agent-self-knowledge --strict
claude plugin eval plugins/agent-self-knowledge --no-publish --max-cost-usd 12
```

The skill also validates its own routing tables against the live pages:

```bash
python3 plugins/agent-self-knowledge/skills/claude-code-docs/scripts/ccdocs.py selfcheck --live
```

</details>

## 🧭 Compatibility

| Surface | Status | Last verified | Notes |
| --- | --- | --- | --- |
| Claude Code | ⚠️ Partial | 2026-09-24, Claude Code 2.1.281 | Research exercised in a headless session on macOS with the plugin loaded through `--plugin-dir`; the consumer smoke test from a remote-marketplace install has not been run. Linux follows from standard-library Python but is unverified. Windows without Git Bash is unsupported: the grant is a `Bash` rule. |
| Claude Cowork | 🧪 Not tested | — | Commands run in Anthropic's sandbox or a Linux VM, never on your machine. A Cowork sandbox observed on 2026-09-24 had Python 3.10, where the script stops with its version message. |
| Claude Chat (web, desktop) | ❌ Not supported | — | Plugins aren't used in Chat. |

## 💡 Examples

**A configuration you're about to write**

```text
Can a plugin's subagent preload a skill from the same plugin, and what name goes in its skills field?
```

→ Claude researches subagents, skills and plugins, quotes the `skills` preload rule and the
plugin-scoped naming of agents, and says which part it confirmed only by testing.

**A feature you suspect doesn't exist**

```text
Is there a settings key to move where Claude Code creates worktrees?
```

→ Claude researches, searches the full text and the changelog, and reports that no such key is
documented as of the date it checked, with where it looked, instead of a flat "no".

## 🔐 Security

| Access | What it may do |
| --- | --- |
| Read | Public pages on `code.claude.com`, `support.claude.com` and `platform.claude.com`, the Claude Code `CHANGELOG.md` on `raw.githubusercontent.com`, and npm registry metadata. When you ask why a configuration isn't working, also your own Claude Code configuration files. |
| Write | The cache under `${XDG_CACHE_HOME:-~/.cache}/ccdocs`, created with your system's default permissions, and research folders under `${CLAUDE_PLUGIN_DATA}/research` (or the cache when that directory isn't writable). Research keeps the last 10 folders and deletes older ones. Nothing in your repository. |
| Process | `python3` running the plugin's own bundled script, and `claude --version` to read your installed build. |
| Network | The five hosts above — and, through the script's `raw` command, any `https://` URL it is given. Non-`https` URLs, including `file://`, are refused. |
| Credentials | None. The plugin has no `userConfig` and sends no authentication. |

- **Human approval:** the `allowed-tools` grant means the script runs without a per-command
  prompt. That is the point of the grant and the main reason to read the script first.
- **Trust:** review the current script source before enabling this in a critical repository.
- **Report a vulnerability** privately via the [security policy](../../SECURITY.md). Never post secrets in issues.

## 🚧 Limitations

| Limitation | What you'll see | Safe recovery |
| --- | --- | --- |
| The skill may not load on its own. | An answer about these products with no quotes and no `Verified` line. | Invoke it with `/agent-self-knowledge:claude-code-docs`. |
| `python3` is absent or older than 3.12. | `ccdocs.py needs Python 3.12 or later; this python3 is …`, and research can't run. | Install Python 3.12 or later and put it first on `PATH`. |
| **Claude Code ships settings keys the published documentation does not carry**, and the skill reads only what is published. | A not-found report for a key that exists but is undocumented. | Treat a not-found settings key as *not documented*, not as *does not exist*. DEBT-0023. |
| No network, or a proxy blocks a docs host. | The failing URL and error in the research map's `FAILURES` list. | Retry with access; the answer lists what that left unverified. |
| Broken anchors or retired articles on the docs sites themselves. | Entries in `FAILURES` such as `anchor #h_… not found`. | None needed: the page URL is cited without the anchor. |
| A research run reads many pages. | A few megabytes per folder and a map too large to print whole. | The map is saved and its path printed; Claude opens only the pages and sections the task needs. |
| `raw` accepts any `https://` URL. | Nothing visible; it is a capability, not an error. | Read the script; the closing condition is a host allowlist. |

## ❓ FAQ

<details>
<summary>Does installing this plugin modify my project?</summary>

No. It registers one skill in Claude Code's plugin cache. Nothing runs until the skill is used,
and when it runs it writes only to its own cache and data directories outside your repository.

</details>

<details>
<summary>Does it read the whole page, or a summary?</summary>

The whole page. `ccdocs.py` downloads the raw markdown the same way `curl` does; on 2026-09-24
the `hooks`, `settings-reference` and `sub-agents` pages it fetched were byte-identical to
`curl`'s. Research then writes the sections about the topic to separate files, and every page
file lists all its headings, so any other section can be read whole with `page`.

</details>

<details>
<summary>Why quote verbatim instead of summarizing?</summary>

A paraphrase hides the gap between what the documentation says and what the model concluded,
and that gap is where wrong answers come from. Quoting makes the difference visible to you in
the answer itself.

</details>

## 📝 Changelog

Every published version is in [CHANGELOG.md](CHANGELOG.md), and each version is tagged
`agent-self-knowledge--v<version>`. Current version: see the badge above.

## 📄 License

[Apache-2.0](LICENSE) © Nery Samuel Murillo.

---

<sub>Part of [claude-essentials](../../README.md) · [Report an issue](https://github.com/nerymurillohnd/claude-essentials/issues/new/choose) · [Security](../../SECURITY.md) · Not an official Anthropic product.</sub>
