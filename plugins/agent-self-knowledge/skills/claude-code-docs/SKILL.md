---
name: claude-code-docs
description: Retrieve current, cited Claude Code facts from the live official documentation, the upstream changelog and the npm registry instead of answering from memory, and quote the sentence that settles it verbatim with its URL and the version checked. Route model, pricing and API questions to the platform docs, plans and billing to support, and the MCP protocol itself to its own spec. Close every answer with the commands used, whether the skill loaded on its own, and what could not be verified.
when_to_use: Whenever an answer, a plan, a config file or a code change depends on how Claude Code works right now (hooks, MCP, LSP, subagents, agent teams, workflows, skills, plugins, marketplaces, CI, models and effort, memory, rules, settings, permissions, commands, flags, env vars, error messages, versions), even when the answer feels certain; before saying a feature does not exist, which takes three separate misses and is then reported as not found on a date, never as a denial; before writing any key into a settings file or a manifest; and when a configuration looks correct but does not work.
allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/ccdocs.py *) Bash(curl -sS https://code.claude.com/*) Bash(curl -sS https://raw.githubusercontent.com/anthropics/*) Bash(claude --version) WebFetch(domain:code.claude.com)
---

# Claude Code Official Docs

Claude Code ships releases almost daily (2.1.x patch releases, often several per week). Hook events,
frontmatter keys, settings, CLI flags, model aliases and whole features appear, change or get renamed
between one week and the next. Your training memory is a snapshot of an older product — treat it as a
hint about *where to look*, never as the answer. The docs are machine-readable and fast to query, so
verifying costs seconds; a wrong hook schema or stale model alias costs the user a broken setup.

This skill tells you **where** each topic lives, **how** to pull just the part you need, and **how to
reconcile** docs, changelog and the user's installed version before answering.

## Scope routing — pick the right corpus first

| Question is about… | Go to |
|---|---|
| Claude Code CLI / Desktop / IDE / web, its config, extensions, CI integrations, Agent SDK | `code.claude.com/docs` (this skill) |
| Model IDs, context windows, pricing, deprecations, Messages API, API-side Agent Skills | `platform.claude.com/llms.txt` → `platform.claude.com/docs/en/models/overview.md` |
| claude.ai plans, billing, usage limits, account features | `support.claude.com` |
| MCP protocol itself (not Claude Code's client) | `modelcontextprotocol.io` |

Many questions straddle two (e.g. "which model does `opus` map to and how big is its context" = Claude
Code `model-config` + platform models page). Fetch both.

## The retrieval loop

**1. Locate.** Use the topic map below for the usual pages. When the topic isn't there, or you need a
specific sub-feature, search the live docs map — it contains every page's full heading tree:

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/ccdocs.py find <keyword> [keyword2]   # headings + owning page
python3 ${CLAUDE_SKILL_DIR}/scripts/ccdocs.py index --grep <regex>        # page titles/summaries
python3 ${CLAUDE_SKILL_DIR}/scripts/ccdocs.py grep <regex> [--pages]      # full text of every page
```

`find` matches heading text only. Settings keys and hook events usually *are* headings, so `find` finds
them — but env var names, error strings, CLI flags, table cells and anything explained only in prose are
invisible to it, and so is any term whose heading uses different words than the user did (`find effort cap`
returns nothing; the cap lives under "Organization effort limits"). `grep` searches every word of every
page and reports each hit with its page and nearest heading, ranked by hit count, so you land on the
owning section instead of guessing. Reach for it whenever `find` comes back empty or you know the concept
but not the vocabulary. `--pages` prints just the page list with hit counts — the cheapest way to see which
page owns a concept before reading any of it.

**2. Read narrowly.** Pages are big (settings-reference ≈ 430 KB, hooks ≈ 320 KB, plugins-reference ≈
140 KB, mcp and sub-agents ≈ 110 KB each) and they grow every week. Pulling a whole page burns tens of
thousands of tokens and buries the answer. Outline first, then fetch the section:

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/ccdocs.py outline hooks
python3 ${CLAUDE_SKILL_DIR}/scripts/ccdocs.py page hooks --section "PreToolUse decision control"
```

`--section` matches a heading substring (case-insensitive) and returns it with its subsections. Several
headings often match a short string — `"decision control"` currently matches 19 of them on the hooks
page — so the command prints a `NOTE:` listing the matches and shows the first. Read that note: if the
heading it showed isn't the one you meant, re-run with a longer `--section` string or `--nth N`.
Citing the generic section when the user asked about a specific event is a silent wrong answer.

Every command ends with a `SOURCE:` line — that is your citation.

**3. Check the version dimension.** Docs describe the latest release. The changelog tells you *when*
something changed, which matters when the user is on an older build or a feature is brand-new:

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/ccdocs.py version                         # npm latest/stable/next + local build + release gap
python3 ${CLAUDE_SKILL_DIR}/scripts/ccdocs.py changelog --grep "<feature>" --last 15
python3 ${CLAUDE_SKILL_DIR}/scripts/ccdocs.py changelog --since <user's version>   # everything they're missing
```

`version` reports how many releases the local build is behind `latest` (or flags it as a `next`/nightly
build that's ahead of the docs). If `claude` isn't on PATH — you're not in their shell, or it's installed
elsewhere — ask for their `claude --version` rather than assuming they run the newest release.

If the docs page and changelog disagree, the changelog is usually newer — say so and cite both.
`stable` on npm can trail `latest` by a week or more; a user on the stable channel may not have a feature
the docs already describe.

**4. Check local reality when you're inside a project.** The docs say what should happen; the user's
machine says what does. When the question is "why isn't my X working", read their actual files
(`.claude/settings.json`, `.mcp.json`, `.claude/hooks/…`, `CLAUDE.md`, `.claude/rules/`, `.claude/agents/`,
plugin manifests) and point them at the built-in inspectors: `/status`, `/doctor`, `/context`, `/hooks`,
`/mcp`, `/memory`, `/agents`, `/skills`, `/plugin`, `/permissions`, `claude plugin validate`. The
`debug-your-config` page is the official checklist.

**5. Answer with provenance, and quote verbatim.** Lead with the answer, then the exact words,
then the citation.

Quote the source rather than paraphrasing it: reproduce the sentence carrying the fact inside
quotation marks, exactly as the page writes it. A paraphrase hides the gap between what the docs
say and what you concluded, and that gap is where wrong answers live. Quote the clause that
decides the question, not a whole section, and never present reconstructed wording as a
quotation — if you can't quote it, you haven't read it yet.

> `skills` — "Custom skill directories containing `<name>/SKILL.md`. **Adds to the default `skills/` scan**."
>
> Sources: [Plugins reference › Component path fields](https://code.claude.com/docs/en/plugins-reference#component-path-fields) · changelog 2.1.275 · verified 2026-09-20 against v2.1.278

Include the date and the version you verified against, so a reader later can tell how fresh the
claim is. When two sources disagree, quote both and say which one governs and why.

**6. Close with the report block.** End every answer that used this skill with these three lines,
named exactly like this, so the reader can audit the retrieval instead of trusting it:

```
TOOLS USED: every command run, plus any WebFetch, WebSearch or MCP server
ACTIVATION: whether this skill loaded on its own, or was invoked by name
NOT FOUND: what could not be verified, and what was therefore left unstated
```

`NOT FOUND` is not a formality: an answer with nothing left unverified is rare enough to be worth
saying so explicitly. Naming a gap costs one line; letting the reader assume it was checked costs
the answer its credibility.

## Topic map (the user's high-value areas)

Slugs are relative to `https://code.claude.com/docs/en/`. For key sections, related pages, adjacent
sources and what's volatile in each area, read `references/topic-routing.md` — it's organized by these
same topics, so read only the section you need.

| Topic | Guide / how-to | Reference / schema | Also check |
|---|---|---|---|
| Hooks | `hooks-guide` | `hooks` (events, input/output, exit codes, decision control) | `agent-sdk/hooks` for SDK |
| MCP | `mcp-quickstart`, `mcp` | `mcp` (scopes, auth, limits, tool search) | `managed-mcp`, `channels` |
| LSP / code intelligence | `plugins` › "Add LSP servers" | `plugins-reference` › "LSP servers", `tools-reference` › "LSP tool behavior" | `discover-plugins` › "Code intelligence" |
| Agents (chooser) | `agents` | — | `features-overview` |
| Subagents & forks | `sub-agents` | `sub-agents` › "Supported frontmatter fields" | `tools-reference` › "Agent tool behavior" |
| Agent teams | `agent-teams` | — | `agent-view`, `cross-session-messaging`, `worktrees` |
| Dynamic workflows | `workflows` | `workflows` › "Behavior and limits" | `claude-directory` |
| Skills | `skills` | `skills` › "Frontmatter reference", "Available string substitutions" | `commands` |
| Plugins | `plugins` | `plugins-reference` | `plugin-evals`, `plugin-dependencies` |
| Marketplaces | `discover-plugins` | `plugin-marketplaces` | official marketplace JSON (see sources) |
| GitHub Actions / CI | `github-actions`, `gitlab-ci-cd`, `headless` | `claude-code-action/action.yml` (GitHub raw) | `github-actions-cloud-providers`, `code-review`, `cli-reference` |
| Models & effort | `model-config` | `model-config`, `settings-reference` | `fast-mode`, `advisor`, platform models page |
| Memory | `memory` | `memory` | `best-practices`, `large-codebases`, `prompt-caching` |
| Rules files | `memory` › "Organize rules with `.claude/rules/`" | same | `claude-directory`, `large-codebases` |
| Settings / permissions (cross-cutting) | `settings`, `permissions` | `settings-reference`, `env-vars`, `cli-reference`, `commands` | `managed-settings`, `permission-modes` |

What's-new digests (`ccdocs.py whatsnew`) are the fastest way to answer "what changed recently in X".

## Claims that need extra care

**Negative claims ("Claude Code can't…", "there's no setting for…").** These are the claims most likely
to be wrong, because features land weekly and absence in memory proves nothing. A negative claim needs
three misses, not one: `find <term>` (headings), `grep <term>` (every word of every page), and
`changelog --grep <term> --last 40` (the changelog often lands a release before the docs page). Search
the concept under two or three names — the docs may call it something you don't. If all three come back
empty, report the bounded fact — "I couldn't find this in the docs or changelog as of <date>, latest
v<version>" — not "it doesn't exist", and say where you looked so the user can judge.

**Anything you're about to write into a config file.** Fetch the exact schema section right before
writing (hook event input/decision JSON, subagent/skill frontmatter keys, `plugin.json`/`marketplace.json`
fields, `.mcp.json` shape, settings keys, action inputs). Afterwards validate: JSON parses,
`claude plugin validate`, `/hooks` or `/mcp` shows it, `/doctor` is clean.

**Model names and aliases.** Alias targets (`opus`, `sonnet`, `best`, …), available models, context sizes
and defaults change with every model launch and differ by provider (Anthropic API vs Bedrock/Vertex/Foundry)
and by plan. Never state them from memory.

**Experimental or gated features.** Some features sit behind env flags, plans, providers or early access
(e.g. agent teams require an experimental env var at time of writing). Check the page's "Enable…",
"Availability", "Limitations" sections and `feature-availability` before promising something works for the user.

**CLI vs Agent SDK.** Hooks, MCP, subagents, skills and plugins exist in both with different APIs. Confirm
which one the user means; cite `agent-sdk/*` pages for SDK answers.

## Fallbacks when the script can't run

The script is a convenience; everything it does is plain HTTP. Equivalents:

- Index: `curl -sS https://code.claude.com/docs/llms.txt`
- Map (heading tree): `curl -sS https://code.claude.com/docs/en/claude_code_docs_map.md | grep -n -i <term>`
- Full text (9 MB — pipe it, never read it into context):
  `curl -sS https://code.claude.com/docs/llms-full.txt | grep -n -i -m 20 <term>` — then find the
  nearest preceding `Source:` line for the owning page URL
- Page: `curl -sS https://code.claude.com/docs/en/<slug>.md` then slice with `awk`/`sed` around the heading
- Changelog: `curl -sS https://raw.githubusercontent.com/anthropics/claude-code/main/CHANGELOG.md | head -200`
- Versions: `npm view @anthropic-ai/claude-code dist-tags` or `curl -sS https://registry.npmjs.org/@anthropic-ai/claude-code`
- Docs MCP server (semantic + regex search over the whole corpus, no auth):
  `claude mcp add --transport http --scope user claude-code-docs https://code.claude.com/docs/mcp`
- WebFetch works on these URLs too, but it summarizes through a small model — fine for concepts, lossy for
  exact keys, enums and JSON. Use raw fetches for anything you'll paste into config.

The built-in `claude-code-guide` subagent also reads these docs, but it runs on a small model; use it for
orientation and verify exact details yourself.

`references/sources.md` has the full endpoint catalog, the authority order for resolving conflicts,
anchor rules for citation links, localized docs, legacy-URL redirects, and proxy/TLS notes.

## Self-maintenance

Page slugs are stable for months; section headings shift more often. A routing table that silently rots
is worse than no routing table, because it sends you to a 404 with full confidence.

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/ccdocs.py selfcheck
```

This validates every page slug and every quoted section name in `SKILL.md` and `references/topic-routing.md`
against the live index and heading map, and prints exactly what moved. Run it when a lookup 404s, when a
`--section` string stops matching, or when the user asks whether this skill is still current — it costs two
HTTP requests. If it reports issues, fix the lines yourself when you can edit the skill, and otherwise tell
the user which file and which entry to correct. `find` or `grep` will locate the new home of anything that
moved.
