# 🧹 Repo Hygiene

[![Version](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2Fnerymurillohnd%2Fclaude-essentials%2Fmain%2Fplugins%2Frepo-hygiene%2F.claude-plugin%2Fplugin.json&query=%24.version&label=version&color=blue)](CHANGELOG.md)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Kind](https://img.shields.io/badge/kind-bundle-8A2BE2)](../../docs/decisions/adr-0001-marketplace-distribution-model.md)
[![Claude Code](https://img.shields.io/badge/Claude_Code-not_tested-D97757?logo=claude&logoColor=white)](#-compatibility)
[![Claude Cowork](https://img.shields.io/badge/Claude_Cowork-not_supported-D97757?logo=claude&logoColor=white)](#-compatibility)
![Git](https://img.shields.io/badge/Git-%E2%89%A52.38-F05032?logo=git&logoColor=white)
![GitHub CLI](https://img.shields.io/badge/gh-optional-181717?logo=github&logoColor=white)
![Network](https://img.shields.io/badge/network-optional-lightgrey)

[← claude-essentials](../../README.md) · [Install](#-installation) · [Skills](#-skills) ·
[Security](#-security) · [Limitations](#-limitations) · [Changelog](CHANGELOG.md)

> **Ask Claude to audit and clean a repository, and it inspects everything a senior Git expert
> would — then changes only what you approve.**

**Kind:** `bundle` — a full workflow: multiple components working together.

Repo Hygiene helps anyone who wants a clean repository but does not know every Git command. It
finds garbage, noise, drift and hidden state: merged and squash-merged branches, lost commits,
forgotten stashes, hidden local edits, secrets in history, leftover operation files, stale pull
requests and unresolved reviews. It reports everything with a detailed recommendation for each
item, and changes nothing until you approve specific items by ID.

> [!CAUTION]
> Approved items change your repository and, when you approve them, your hosting provider:
> deleted branches and tags, dropped stashes, removed files, closed pull requests, resolved
> review threads, and in `deep` programs expired reflogs and reclaimed objects. Each
> recommendation states its undo command or says **irreversible**. Destructive `deep`
> operations require a backup that has passed a restore test first.

## 🎯 What it does

| Scenario | How this plugin helps | Expected result |
| --- | --- | --- |
| "Clean up this repo" with old branches and stashes | Classifies every branch: merged, squash-merged, gone, or unique work. Inventories stashes, worktrees, leftover files, ignored caches and hidden refs | One report and a numbered plan; nothing deleted until you approve IDs |
| A branch was squash-merged, so Git says "not merged" | Proves integration by content, not by ancestry, and states the evidence | The branch is safe to delete with a recovery command, or flagged for review |
| A commit was lost with `reset --hard`, or a stash was dropped | Finds it in the reflog or among unreachable objects | A recovery command awaiting approval |
| Years of pull requests with unresolved review threads (`/repo-hygiene:deep`) | Reads every PR and thread, and decides each thread against today's code | Per-thread verdicts, replies drafted, closure with a receipt after approval |
| "Leave only `main`" (`/repo-hygiene:deep plan`) | Writes a multi-session program: acceptance contract, operation IDs, backup with restore test, runbook | A plan you approve by operation, executed and certified |

## 🚫 What it does not do

- **Does not** change anything without your approval of specific item IDs. "Clean it up" is
  not an approval.
- **Does not** print secrets. It inventories secret-shaped files and history secrets by path
  and commit only, and redacts credentials in URLs as it reads them.
- **Does not** enforce anything: there are no hooks. If you run Claude in `auto` or
  `bypassPermissions` mode, your permission settings are what stand between a command and
  your repository.
- **Does not** install tools, change authentication or request tokens.
- **Not a fit when** you want server-side enforcement: use branch protection, rulesets and
  required checks on your provider.

## ⚡ Installation

**Claude Code** — add the marketplace once, then install:

```text
/plugin marketplace add nerymurillohnd/claude-essentials
/plugin install repo-hygiene@claude-essentials
```

**Claude Cowork** — not supported: the plugin needs a local repository and a shell.

> [!TIP]
> Installation is complete when `/plugin` lists `repo-hygiene` as enabled and
> `/repo-hygiene:deep` appears in the `/` menu.

### What installing changes

| | Effect |
| --- | --- |
| **Does** | Registers two skills and three agents in Claude Code |
| **Does not** | Touch any repository, settings file or provider until a skill runs and you approve items |

### Update, disable, or remove

```text
/plugin marketplace update claude-essentials
/plugin disable repo-hygiene@claude-essentials
/plugin uninstall repo-hygiene@claude-essentials
```

Uninstalling does not revert approved changes. Evidence packages it created under
`${TMPDIR:-/tmp}/repo-hygiene/` stay until you delete them.

## 🧠 Skills

| Skill | Invoke | Claude uses it when | Invocation |
| --- | --- | --- | --- |
| [`routine`](skills/routine/SKILL.md) | `/repo-hygiene:routine` | You ask to audit, review, clean or prune a repository, its branches, stashes, worktrees, leftovers or old PRs, or which commit introduced something | Claude + user |
| [`deep`](skills/deep/SKILL.md) | `/repo-hygiene:deep [audit \| plan \| execute S01,S02 \| resume \| certify] [focus]` | Only when you invoke it: full forensics and multi-session cleanup programs | User only |

`routine` covers every area at everyday depth. `deep` runs the same areas at full depth: every
reflog, the unreachable census with and without reflog roots, integrity, every ref namespace,
full history, and every PR and review thread. It also adjudicates what it finds instead of only
counting it. When `routine` finds something only `deep` can resolve, it tells you to run it.

## 🤖 Agents

| Agent | Role | Tools | Model |
| --- | --- | --- | --- |
| [`thread-adjudicator`](agents/thread-adjudicator.md) | Decides a batch of review threads against the current code; drafts replies | `Read, Grep, Glob, Bash` (no Write/Edit) | `inherit` |
| [`candidate-classifier`](agents/candidate-classifier.md) | Classifies unreachable commits, stash paths, branches and lost-found entries | `Read, Grep, Glob, Bash` (no Write/Edit) | `inherit` |
| [`certificate-verifier`](agents/certificate-verifier.md) | Re-checks a program's acceptance contract independently | `Read, Grep, Glob, Bash` (no Write/Edit) | `inherit` |

`deep` delegates to them when a volume exceeds one context, such as hundreds of review threads
or unreachable commits. They only read. Every change is made by the main conversation, one at a
time, after your approval.

## 🪝 Hooks and side effects

None — this plugin registers no hooks. The only file it writes without an item approval is
its evidence package: a directory created with mode 700 under `${TMPDIR:-/tmp}/repo-hygiene/`,
or a location you name. It holds command outputs and enumerations, never secret values.

## 🔌 MCP, permissions, and network

None — the plugin ships no MCP server and asks for no credentials.

- **Provider reads** use what you already have: a connected provider MCP server first, then
  `gh` or `glab` if installed and authenticated. Without either, provider areas are reported
  as `blocked`, with the reason.
- **Network:** `git ls-remote` and provider API reads when a remote or provider exists. `git
  fetch` only as an approved item.
- **Permissions:** read-only Git commands already run without prompts in Claude Code. Every
  change goes through your normal permission prompt.

## 📋 Requirements

| Requirement | Minimum | Check | Why |
| --- | --- | --- | --- |
| Claude Code | 2.1.222 | `claude --version` | A model attempt to run `deep` is refused and turned into a suggestion that you run it |
| Git | 2.38 | `git --version` | `git merge-tree --write-tree` proves squash-merged branches; newer features (`%(ahead-behind)` 2.41, `ls-remote --branches` 2.46) have documented fallbacks |
| POSIX shell tools | `sed -E`, `awk`, `sort`, `head`, `find` | shipped with macOS, Linux, Git for Windows | Redaction and bounded listings |
| `gh` or `glab` | any current | `gh auth status` | Optional: provider areas (PRs, review threads, settings, CI, alerts) |
| `git-filter-repo`, `git-lfs`, `gitleaks`, `trufflehog`, `git-secrets`, `git-sizer` | — | `command -v <tool>` | Optional: used when present, never installed |

## ✅ Verification

**Consumer smoke test** — after installing from the remote marketplace, in any Git repository:

```text
Audita este repositorio y dime qué sobra, sin cambiar nada.
```

Expected result: one report that opens with a coverage table (every area inspected, not
applicable or blocked), findings with evidence, recommendations with undo commands, and a
request to approve IDs. `git status` and `git for-each-ref` are unchanged afterwards.

**Behavioral evals** — [`evals/`](evals/) run per the maintainer's eval protocol; results are
reported in the pull request or a dated file under `docs/audits/`, never here.

<details>
<summary>Maintainer checks</summary>

From the marketplace root:

```bash
make check
claude plugin validate plugins/repo-hygiene --strict
claude plugin eval plugins/repo-hygiene --ablation with-without --scaffold --allow-tools Bash \
  --model claude-sonnet-5 --judge-model claude-opus-5 --no-publish --max-cost-usd 25
```

</details>

## 🧭 Compatibility

| Surface | Status | Last verified | Notes |
| --- | --- | --- | --- |
| Claude Code | 🧪 Not tested | — | Built and checked locally with Claude Code 2.1.280 on 2026-09-22, not yet from the remote marketplace. macOS, Linux, WSL, Windows with Git Bash. In `-p` and SDK runs it reports and recommends only, because approval needs a reply |
| Claude Cowork | ❌ Not supported | — | Needs a local repository and shell |
| Claude Chat (web, desktop) | ❌ Not supported | — | Plugins aren't used in Chat. |

## 💡 Examples

**Everyday cleanup**

```text
Limpia este repo: tengo ramas viejas, stashes y cosas que sobran.
```

→ Claude inspects every area and reports, for example:

- which branches are merged, squash-merged, gone or hold unique work;
- the stashes and what each one contains;
- a hidden `assume-unchanged` edit;
- a token committed and later removed from history;
- leftover `.orig`/`.rej` files.

Each finding comes with a recommendation (command, undo and consequence). You answer, for
example, "Approve R1, R3 and R4".

**Forensics and a cleanup program**

```text
/repo-hygiene:deep
/repo-hygiene:deep plan
/repo-hygiene:deep execute S01,S02,S03
```

→ The first command runs a full audit: every reflog, the unreachable objects, integrity, and
every PR and review thread, with verdicts. `plan` writes a plan package with an acceptance
contract. `execute` runs only the named operations, starting with a backup that is
restore-tested.

## 🔐 Security

| Access | What it may do |
| --- | --- |
| Read | The repository's files by name and metadata, its Git objects and config (redacted), and provider data through your MCP server or CLI. Never the contents of secret-shaped files (`.env*`, keys, credentials) or unknown payloads |
| Write | The evidence package (mode 700). Repository, provider and file changes only for approved item IDs |
| Process | `git`, POSIX tools, and `gh`/`glab`/scanners when present; never hooks, aliases or configured diff/filter drivers during an audit |
| Network | `git ls-remote` and provider API reads; `git fetch` and provider writes only when approved |
| Credentials | None requested or stored; it uses your existing `gh`/`glab`/MCP authentication and reports scopes by name only |

- **Human approval:** every mutation — branch, tag, stash, worktree, file, config, remote,
  provider, reflog and object store — runs only after you approve its ID. In `deep` programs,
  destructive operations also require a backup that has passed a restore test.
- **Untrusted repositories:** `deep` stops before running Git in a repository you do not own
  and recommends cloning it with `--no-local` first. Git's config and hooks can execute
  commands.
- **Trust:** review the skill and reference sources before enabling this on a critical
  repository.
- **Report a vulnerability** privately via the [security policy](../../SECURITY.md). Never post
  secrets in issues.

## 🚧 Limitations

| Limitation | What you'll see | Safe recovery |
| --- | --- | --- |
| No hooks: guidance, not enforcement | In `auto` or `bypassPermissions` mode a destructive command could run if the skill did not load | Keep the default permission mode for repository cleanup, or add deny rules for destructive Git commands |
| Squash detection is a heuristic | Some branches come back as `NEEDS REVIEW` | Confirm with the provider's merged PR, or review the listed diff |
| Provider access depends on your tools | Provider areas reported as `blocked` with a reason (no `gh`, missing scope, plan limit) | Authenticate `gh`/`glab` or connect a provider MCP server, then re-run |
| GitLab covers settings, branches, merge requests and discussions only; other providers none | Those areas marked `blocked (not covered…)` | Audit them in the provider's UI |
| Shallow clones hide ancestry | Integration verdicts marked `unknown (shallow)` | Approve the proposed `git fetch --unshallow` |
| A `deep` run on a large repository with a long PR history is long | Progress per area; large lists in the evidence package | Focus it, e.g. `/repo-hygiene:deep audit P3` |
| The bundled Git reference can drift from git-scm | A behavior that differs from the reference | The official URL is on every entry; live docs win |
| Native PowerShell | Recipes use POSIX tools | Use Git Bash on Windows |

## ❓ FAQ

<details>
<summary>Why does Claude not ask before running so many Git commands?</summary>

Because they only read. Claude Code already runs read-only Git commands without prompting, and
the skill treats asking before a read as a defect: stopping early is how serious problems go
unfound. Anything that changes state waits for your approval.

</details>

<details>
<summary>Why can't Claude run <code>deep</code> on its own?</summary>

`deep` carries the most destructive procedures in Git: history rewrite, reflog expiry and
object pruning. It runs only when you invoke it. If Claude needs it, it tells you to run
`/repo-hygiene:deep`.

</details>

## 📝 Changelog

Every published version is in [CHANGELOG.md](CHANGELOG.md), and each version is tagged
`repo-hygiene--v<version>`. Current version: see the badge above.

## 📄 License

[Apache-2.0](LICENSE) © Nery Samuel Murillo. The command reference summarizes and links the Git
documentation (https://git-scm.com/docs, GPL-2.0) and Pro Git (https://git-scm.com/book,
CC BY-NC-SA 3.0); it quotes short passages with attribution and ships no copy of either.

---

<sub>Part of [claude-essentials](../../README.md) · [Report an issue](https://github.com/nerymurillohnd/claude-essentials/issues/new/choose) · [Security](../../SECURITY.md) · Not an official Anthropic product.</sub>
