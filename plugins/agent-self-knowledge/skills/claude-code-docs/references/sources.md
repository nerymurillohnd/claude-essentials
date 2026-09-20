# Source catalog — Claude Code live knowledge

All endpoints below were confirmed reachable (HTTP 200) on 2026-09-20. If one fails, fall back to the
next source in the same tier and tell the user which source was unavailable.

## Authority order (resolve conflicts top-down)

| Tier | Source | Answers | Why this rank |
|---|---|---|---|
| 1 | The user's installed Claude Code (`claude --version`, `/status`, `/doctor`, `/context`, `/hooks`, `/mcp`, `/memory`, `/agents`, `/skills`, `/plugin`, `/permissions`, `claude --help`, `claude mcp list`, `claude plugin validate`) | What *this* machine actually does | Docs describe latest; the user may be behind or ahead (`next`) |
| 2 | Docs pages `https://code.claude.com/docs/en/<slug>.md` | Intended behavior, schemas, config | Official, regenerated continuously |
| 3 | Changelog (GitHub raw CHANGELOG.md) | When a behavior was added/changed/fixed; version gating | Ships with each release; sometimes ahead of the docs page |
| 4 | What's new digest `whats-new/index.md`, weekly `whats-new/2026-wNN.md` | Headline features + version ranges per week | Curated context, not exhaustive |
| 5 | Official repos (claude-code-action, claude-plugins-official, claude-code issues) | Exact action inputs, marketplace contents, known bugs | Source of truth for artifacts outside the CLI |
| 6 | Platform docs (`platform.claude.com`) | Model IDs, context sizes, pricing, API features | Owner of model/API facts |
| — | Training memory, blogs, third-party tutorials, Stack Overflow | Orientation only | Stale or unofficial; never cite as fact |

When tier 2 and tier 3 disagree, report both: "Docs say X; changelog vX.Y.Z says Y" — the docs page may lag.

## Endpoints

### Discovery
- Page index (title + slug + one-line summary for every page): https://code.claude.com/docs/llms.txt
- Docs map (every page's full heading tree; auto-regenerated, carries a "Last updated" stamp):
  https://code.claude.com/docs/en/claude_code_docs_map.md
- Full corpus in one file (≈ 9.2 MB — only grep it, never read it into context):
  https://code.claude.com/docs/llms-full.txt — `ccdocs.py grep <regex>` searches it and attributes every hit
  to its page and nearest heading (pages are delimited by a `# Title` line followed by `Source: <url>`).
  This is the local equivalent of the docs MCP full-text search, and the evidence base for negative claims.
- Localized indexes: `https://code.claude.com/docs/_llms/<code>.md` (codes listed under "Indexes" at the end of
  llms.txt, e.g. `es`, `fr`, `de`, `jp`, `ko`, `cn`, `pt-br`); localized pages live at `/docs/<lang>/<slug>.md`
  (e.g. `/docs/es/hooks.md`). English is canonical and translations can lag — cite `/en/` for technical claims,
  even when answering in Spanish.

### Pages
- Raw markdown: `https://code.claude.com/docs/en/<slug>.md` (e.g. `hooks.md`, `agent-sdk/hooks.md`).
  The HTML URL also returns markdown when requested with `Accept: text/markdown`.
- Human-facing citation URL: drop `.md` → `https://code.claude.com/docs/en/<slug>`; section anchors follow the
  rendered heading id (lowercase, spaces→`-`, punctuation dropped, `/` kept), e.g.
  `memory#organize-rules-with-claude/rules/`, `hooks#exit-code-2-behavior-per-event`. Treat anchors as
  best-effort; the page URL is always valid.
- Pages are large and still growing (measured 2026-09-20: settings-reference ≈ 433 KB, hooks ≈ 321 KB,
  plugins-reference ≈ 138 KB, mcp ≈ 114 KB, sub-agents ≈ 112 KB, skills ≈ 112 KB, model-config ≈ 108 KB).
  Fetch a section, not the whole page.

### Changelog & versions
- Raw changelog (plain `## <version>` blocks, newest first): https://raw.githubusercontent.com/anthropics/claude-code/main/CHANGELOG.md
- Rendered changelog (≈ 780 KB, dated `<Update>` blocks): https://code.claude.com/docs/en/changelog.md — use it when you need the release *date*.
- npm registry (dist-tags `latest`, `stable`, `next` + publish times): https://registry.npmjs.org/@anthropic-ai/claude-code
- In-app: `/release-notes`.

### Docs MCP server (official, no auth)
- URL: `https://code.claude.com/docs/mcp` (HTTP transport). Documented in `mcp-quickstart`.
- Tools: `search_claude_code_docs` (semantic search → titles + links), `query_docs_filesystem_claude_code_docs`
  (read-only virtual FS: `rg`, `grep`, `tree`, `ls`, `cat`, `head` over `/<path>.mdx`), and `submit_feedback`
  (reports a doc problem — only use if the user asks you to).
- Install: `claude mcp add --transport http claude-code-docs https://code.claude.com/docs/mcp`
  (add `--scope user` for all projects). Once connected the tools appear as
  `mcp__claude-code-docs__search_claude_code_docs` etc.
- Best for: fuzzy/conceptual questions and exact regex across the whole corpus without downloading 9.5 MB.

### Built-in helper
- The `claude-code-guide` built-in subagent answers Claude Code questions by fetching these docs. It runs on
  Haiku (per `sub-agents` → "Built-in subagents"), so it is fine for orientation but verify exact field names,
  flags and schemas yourself before writing config.
- Admin note: blocking `code.claude.com` on the network breaks this agent and docs lookups (`network-config`).

### Adjacent official sources
- GitHub Action: https://github.com/anthropics/claude-code-action
  - Inputs/outputs: https://raw.githubusercontent.com/anthropics/claude-code-action/main/action.yml
  - Docs: https://raw.githubusercontent.com/anthropics/claude-code-action/main/docs/usage.md (also configuration, setup, security, solutions, faq, custom-automations, migration-guide)
  - Releases: `gh release list -R anthropics/claude-code-action`; API-free fallback: `git ls-remote --tags https://github.com/anthropics/claude-code-action`
- Official plugin marketplace: https://github.com/anthropics/claude-plugins-official
  - Catalog JSON: https://raw.githubusercontent.com/anthropics/claude-plugins-official/main/.claude-plugin/marketplace.json
- Bug reports / known issues: https://github.com/anthropics/claude-code/issues (`gh issue list -R anthropics/claude-code --search "<term>"`)
- Settings JSON Schema (SchemaStore, community-maintained): https://json.schemastore.org/claude-code-settings.json
- Platform/API docs index: https://platform.claude.com/llms.txt — models: https://platform.claude.com/docs/en/models/overview.md
- Support center (plans, billing, claude.ai features): https://support.claude.com
- MCP protocol spec: https://modelcontextprotocol.io

### Legacy URLs (still seen in old skills, prompts and blog posts)
- `docs.anthropic.com/en/docs/claude-code/*` → 301 to `code.claude.com/docs/en/*`
- `docs.claude.com/*` → 301 to `platform.claude.com/*`
Cite the final `code.claude.com` / `platform.claude.com` URL, not the redirecting one.

## Fetching mechanics
- Prefer `scripts/ccdocs.py` or `curl -sS <url>.md` through Bash: you get the exact text. `code.claude.com`
  returns 403 to a request with no `User-Agent`, so a bare urllib/requests call fails where curl and
  `ccdocs.py` (which sets one) succeed — don't read that 403 as the page being gone. WebFetch passes the
  page through a small summarizing model — acceptable for "what is X", lossy for exact keys, flags, enums and
  JSON shapes. (WebFetch to code.claude.com is pre-approved, so it is the fallback when Bash network is blocked.)
- Behind a corporate proxy: urllib/curl honor `HTTPS_PROXY`; set `SSL_CERT_FILE` / `CURL_CA_BUNDLE` to the proxy CA if TLS fails.
- GitHub API (`api.github.com`) may be rate-limited unauthenticated; prefer `gh` (authenticated) or `raw.githubusercontent.com`.
