# 📚 Agent Self-Knowledge

[![Version](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2Fnerymurillohnd%2Fclaude-essentials%2Fmain%2Fplugins%2Fagent-self-knowledge%2F.claude-plugin%2Fplugin.json&query=%24.version&label=version&color=blue)](CHANGELOG.md)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Kind](https://img.shields.io/badge/kind-skill--only-8A2BE2)](../../docs/decisions/adr-0001-marketplace-distribution-model.md)
[![Claude Code](https://img.shields.io/badge/Claude_Code-partial-D97757?logo=claude&logoColor=white)](#-compatibility)
[![Claude Cowork](https://img.shields.io/badge/Claude_Cowork-not_tested-D97757?logo=claude&logoColor=white)](#-compatibility)
![Python](https://img.shields.io/badge/Python-%E2%89%A53.14-3776AB?logo=python&logoColor=white)
![Network](https://img.shields.io/badge/network-required-lightgrey)

[← claude-essentials](../../README.md) · [Install](#-installation) · [Skill](#-skills) ·
[Security](#-security) · [Limitations](#-limitations) · [Changelog](CHANGELOG.md)

> **Claude stops answering questions about Claude Code from memory, and starts quoting the live documentation with the URL and the version it checked.**

**Kind:** `skill-only` — exactly one skill, nothing else.

Agent Self-Knowledge helps anyone configuring Claude Code get answers that are
true today rather than true at training time. It queries the official
documentation, the upstream changelog and the npm registry on demand, quotes
the sentence that decides the question verbatim, and reports what it could not
find — and it does **not** cover any product other than Claude Code.

> [!CAUTION]
> This plugin reaches the network. Its skill grants its own bundled Python
> script through `allowed-tools`, so the script runs without a per-command
> approval prompt, and the script's `raw` command accepts any URL with no
> scheme or host validation — including `file://`. Review
> `skills/claude-code-docs/scripts/ccdocs.py` before enabling this in a
> sensitive environment.

> [!IMPORTANT]
> **Requires Python 3.14 or later as `python3` on your `PATH`.** The skill runs
> `python3 …/ccdocs.py`, and the script stops with a message naming the version it
> found when `python3` is older. The Python that ships with the Xcode Command Line
> Tools on macOS (3.9) and the default `python3` of Ubuntu 24.04 (3.12) or Debian 13
> (3.13) are too old: install 3.14 from python.org, with `brew install python@3.14`,
> or with `uv python install 3.14 --default`.

## 🎯 What it does

| Scenario | How this plugin helps | Expected result |
| --- | --- | --- |
| You ask whether a settings key exists and what it accepts. | Locates the key across every documentation page, then reads only the section that defines it. | The exact sentence quoted, its URL, and the version it was verified against. |
| Claude is about to tell you a feature doesn't exist. | Requires three misses — headings, full corpus, changelog — before any negative claim. | "Not found as of `<date>`, latest v`<version>`", with where it looked, instead of a wrong denial. |
| A configuration looks correct but doesn't work. | Reads your actual files and compares them against the current schema, then points at the built-in inspectors. | The mismatch named, or the key identified as unrecognized. |
| The documentation and the changelog disagree. | Quotes both and applies a stated authority order. | Both sources shown, with which one governs and why. |

## 🚫 What it does not do

- **Does not** cover anything but Claude Code — not the Agent SDK's host
  language, not other AI tools, not your project's own stack.
- **Does not** guarantee it loads on its own. Claude decides; you can always
  invoke it by name.
- **Does not** write to your repository, install anything, or use credentials.
- **Not a fit when** the question is about your own code rather than about how
  Claude Code behaves.

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
under **Customize → Plugins**. Uninstalling does not delete the documentation
cache under `${XDG_CACHE_HOME:-~/.cache}/ccdocs`; remove that directory by hand
if you want the disk space back.

## 🧠 Skills

| Skill | Invoke | Claude uses it when | Invocation |
| --- | --- | --- | --- |
| [`claude-code-docs`](skills/claude-code-docs/SKILL.md) | `/agent-self-knowledge:claude-code-docs` | A question, plan, config file or code change depends on how Claude Code works right now. | Claude + user |

## 🤖 Agents

None — this plugin ships exactly one skill and no agents.

## 🪝 Hooks and side effects

None — this plugin registers no hooks. Its only side effect is the documentation
cache described under [Security](#-security).

## 🔌 MCP, permissions, and network

The plugin registers no MCP server and sends no credentials. Its skill's
`allowed-tools` grants five rules — its own bundled script, read-only `curl`
against `code.claude.com` and `raw.githubusercontent.com/anthropics/*`,
`claude --version`, and `WebFetch` limited to `code.claude.com` — so retrieval
runs without a prompt for each command. Network destinations are listed under
[Security](#-security).

One disclosure: when the bundled script is unavailable, the skill lists
Anthropic's own documentation MCP server as a fallback and may propose
`claude mcp add --transport http --scope user claude-code-docs
https://code.claude.com/docs/mcp`. Installing this plugin never runs that
command. It is a suggestion you approve and own, and it registers a server in
your **user** scope, outside this plugin.

## 📋 Requirements

| Requirement | Minimum | Check | Why |
| --- | --- | --- | --- |
| Claude Code | 2.1.222 | `claude --version` | `plugin.json` carries `metadata`, a recognized manifest field only from that version; earlier builds treat it as unrecognized, which `claude plugin validate --strict` turns into an error. |
| Python | 3.14 | `python3 -V` | `ccdocs.py` is stdlib-only and needs no packages and no virtualenv; it checks the version at start and stops with a message on anything older. |
| `python3` on `PATH` | — | `command -v python3` | The `allowed-tools` grant invokes it by name. |
| `curl` | 7.64 | `curl --version` | The `allowed-tools` grant fetches the documentation hosts with `curl -sS`. |
| Network access | — | — | Retrieval reads `code.claude.com`, `raw.githubusercontent.com` and `registry.npmjs.org`. |
| Writable cache directory | — | — | `${XDG_CACHE_HOME:-~/.cache}/ccdocs`. If it cannot be written, retrieval still works and only caching is lost. |

The script enforces the Python minimum itself; the others are not checked up front,
and a missing `python3` or an unreachable network fails visibly.

Two environment variables change how the script runs, both optional:

| Variable | Default | Effect |
| --- | --- | --- |
| `CCDOCS_CACHE_TTL` | `900` | Seconds a fetched page stays cached. `0` disables caching, so every answer refetches. |
| `CCDOCS_CORPUS_TTL` | `3600` | Seconds the 9 MB full corpus that `grep` searches stays cached. |
| `CCDOCS_LANG` | `en` | Documentation language segment used when building documentation URLs. |

## ✅ Verification

**Consumer smoke test** — after installing from the remote marketplace, in any directory:

```text
Which key in .claude/settings.json controls where new worktrees branch from, and what values does it accept?
```

Expected result: the answer quotes the sentence defining `worktree.baseRef`
verbatim, links the settings reference, and states the date and version it
verified against.

**Behavioural evals** — Behavioural evals live in [`evals/`](evals/) and run per the
maintainer's eval protocol; results are reported in the pull request, never here.

<details>
<summary>Maintainer checks</summary>

From the marketplace root:

```bash
npm run check
claude plugin validate plugins/agent-self-knowledge --strict
claude plugin eval plugins/agent-self-knowledge --trust-plugin \
  --allow-tools "Bash(python3 *)" "Bash(curl -sS https://*)" "Bash(claude --version)" WebFetch \
  --model claude-sonnet-5 --judge-model claude-sonnet-5 --no-publish --max-cost-usd 8
```

The skill also validates its own citations:

```bash
python3 plugins/agent-self-knowledge/skills/claude-code-docs/scripts/ccdocs.py selfcheck
```

</details>

## 🧭 Compatibility

| Surface | Status | Last verified | Notes |
| --- | --- | --- | --- |
| Claude Code | ⚠️ Partial | 2026-09-20, Claude Code 2.1.278 | Retrieval exercised in a real session on macOS; Linux and WSL follow from stdlib Python but are unverified. Windows without Git Bash is unsupported: the grant is a `Bash` rule. The evals in this branch ran against the shipped frontmatter; the consumer smoke test from a remote-marketplace install has not been run. |
| Claude Cowork | 🧪 Not tested | — | Retrieval needs `python3` and outbound network; neither is verified there. |
| Claude Chat (web, desktop) | ❌ Not supported | — | Plugins aren't used in Chat. |

## 💡 Examples

**A key you're about to write into a config file**

```text
Does plugin.json's "skills" field replace the default skills/ scan, or add to it?
```

→ Claude reads the manifest reference and answers with the sentence that settles
it — *"Adds to the default `skills/` scan"* — plus the documented
marketplace-root exception, rather than guessing from the field's name.

**A feature you suspect doesn't exist**

```text
Is there a settings key to move where Claude Code creates worktrees?
```

→ Claude searches headings, the full corpus and the changelog, reports that no
such key is documented as of the date it checked, and points at the
`WorktreeCreate` hook, which is the documented way to do it.

## 🔐 Security

| Access | What it may do |
| --- | --- |
| Read | Public documentation pages on `code.claude.com`, the upstream `CHANGELOG.md`, and npm registry metadata. When you ask why a configuration isn't working, also your own `.claude/settings.json`, `.mcp.json`, hooks, `CLAUDE.md`, `.claude/rules/`, agents and plugin manifests. |
| Write | Only the response cache under `${XDG_CACHE_HOME:-~/.cache}/ccdocs`. Nothing in your repository. |
| Process | `python3` running the plugin's own bundled script, `curl` against the two granted hosts, and `claude --version` to read your installed build. |
| Network | `code.claude.com`, `raw.githubusercontent.com`, `registry.npmjs.org` — and, through the script's `raw` command, any URL it is given, including `file://`. |
| Credentials | None. The plugin has no `userConfig` and sends no authentication. |

- **Human approval:** the `allowed-tools` grant means retrieval commands run
  without a per-command prompt. That is the point of the grant and the main
  reason to read the script before enabling it.
- **Trust:** review the current script source before enabling this in a critical
  repository. The `raw` command performs no URL validation; this is a known,
  accepted limitation recorded in the repository's debt ledger.
- **Report a vulnerability** privately via the [security policy](../../SECURITY.md). Never post secrets in issues.

## 🚧 Limitations

| Limitation | What you'll see | Safe recovery |
| --- | --- | --- |
| The skill may not load on its own. | An answer about Claude Code with no quote and no source line. | Invoke it directly with `/agent-self-knowledge:claude-code-docs`. |
| **Claude Code ships settings keys that the published documentation does not carry, and the skill reads only what is published.** Verified 2026-09-20: `worktree.location` is defined in the settings schema inside Claude Code 2.1.278 and returns 0 hits across the 99,415 lines of `llms-full.txt`. | A bounded report that a settings key was not found, when the key exists but is undocumented. | Treat a not-found result for a settings key as *not documented*, not as *does not exist*. DEBT-0023. |
| No network, or a proxy blocks the docs host. | The script exits with the URL and the underlying error; it never returns a partial corpus. | Retry with access, or ask Claude to quote the page you paste in. |
| `python3` is absent or older than 3.14. | The Bash call fails, or `ccdocs.py` stops with `ccdocs.py needs Python 3.14 or later`; retrieval can't run. | Install Python 3.14 (python.org, `brew install python@3.14`, or `uv python install 3.14 --default`) so `python3` is 3.14. The Xcode Command Line Tools' Python (3.9) is not enough. |
| `curl` is absent. | The granted `curl -sS https://…` calls fail and only the bundled references answer. | Install `curl` (it ships with macOS, Linux and Windows 10 or later). |
| A documentation page is renamed upstream. | An error naming the URL that moved. | Re-run with `find <topic>` to relocate the page. |
| `raw` accepts any URL. | Nothing visible; it is a capability, not an error. | Read the script; the closing condition is a host allowlist. |

## ❓ FAQ

<details>
<summary>Does installing this plugin modify my project?</summary>

No. It registers one skill in Claude Code's plugin cache. Nothing runs until the
skill is used, and when it runs it writes only to its own cache directory
outside your repository.

</details>

<details>
<summary>Why quote verbatim instead of summarizing?</summary>

A paraphrase hides the gap between what the documentation says and what the
model concluded, and that gap is where wrong answers come from. Quoting makes
the difference visible to you in the answer itself.

</details>

## 📝 Changelog

Every published version is in [CHANGELOG.md](CHANGELOG.md), and each version is tagged
`agent-self-knowledge--v<version>`. Current version: see the badge above.

## 📄 License

[Apache-2.0](LICENSE) © Nery Samuel Murillo Tejada.

---

<sub>Part of [claude-essentials](../../README.md) · [Report an issue](https://github.com/nerymurillohnd/claude-essentials/issues/new/choose) · [Security](../../SECURITY.md) · Not an official Anthropic product.</sub>
