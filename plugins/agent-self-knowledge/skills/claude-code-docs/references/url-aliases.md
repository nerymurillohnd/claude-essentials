# Claude Code docs URLs outside the index

`docs-catalog.md` lists the 197 pages of https://code.claude.com/docs/llms.txt. The site also serves
the URLs below. Found on 2026-09-24 with a Firecrawl map of `https://code.claude.com/docs/en` (218
distinct URLs, every indexed page included). Each one was checked on that date: HTTP status, page
`<title>`, and the indexed page with the same title.

## Rules

1. **Cite the canonical page, never an alias.** An alias serves the canonical page's content under an
   old slug; its anchors and future behavior are not guaranteed.
2. **When a user, a file or an old answer uses an alias, translate it** with the table below, then read
   the canonical page.
3. **An unindexed page is real but not part of the navigation.** Read it only when the question is
   about exactly that page, and say it is not in the index.

## Legacy aliases (serve another page's content)

| Alias URL | Canonical page |
|---|---|
| https://code.claude.com/docs/en/agent-sdk | [`agent-sdk/overview`](https://code.claude.com/docs/en/agent-sdk/overview) |
| https://code.claude.com/docs/en/agent-sdk/slash-commands | [`agent-sdk/skills`](https://code.claude.com/docs/en/agent-sdk/skills) |
| https://code.claude.com/docs/en/bedrock-vertex | [`third-party-integrations`](https://code.claude.com/docs/en/third-party-integrations) |
| https://code.claude.com/docs/en/bedrock-vertex-proxies | [`third-party-integrations`](https://code.claude.com/docs/en/third-party-integrations) |
| https://code.claude.com/docs/en/claude-md | [`memory`](https://code.claude.com/docs/en/memory) |
| https://code.claude.com/docs/en/corporate-proxy | [`network-config`](https://code.claude.com/docs/en/network-config) |
| https://code.claude.com/docs/en/desktop-changelog | [`desktop`](https://code.claude.com/docs/en/desktop) |
| https://code.claude.com/docs/en/iam | [`authentication`](https://code.claude.com/docs/en/authentication) |
| https://code.claude.com/docs/en/team | [`authentication`](https://code.claude.com/docs/en/authentication) |
| https://code.claude.com/docs/en/ide-integrations | [`vs-code`](https://code.claude.com/docs/en/vs-code) |
| https://code.claude.com/docs/en/installation | [`setup`](https://code.claude.com/docs/en/setup) |
| https://code.claude.com/docs/en/mcp-servers | [`mcp`](https://code.claude.com/docs/en/mcp) |
| https://code.claude.com/docs/en/slash-commands | [`skills`](https://code.claude.com/docs/en/skills) |
| https://code.claude.com/docs/en/tools | [`tools-reference`](https://code.claude.com/docs/en/tools-reference) |
| https://code.claude.com/docs/en/web-scheduled-tasks | [`routines`](https://code.claude.com/docs/en/routines) |
| https://code.claude.com/docs/en/whats-new | [`whats-new/index`](https://code.claude.com/docs/en/whats-new/index) |

## Real pages missing from the index

| URL | What it is |
|---|---|
| https://code.claude.com/docs/en/auto-mode-classifier-billing | "Auto mode classifier request charges" |
| https://code.claude.com/docs/en/terminal-guide | "Terminal guide for new users" |
| https://code.claude.com/docs/en/ultraplan | "Ultraplan is no longer available" (a retirement notice, not a feature page) |
| https://code.claude.com/docs/en/claude_code_docs_map | The heading map of every page (`ccdocs.py find` and `outline --map` read it) |
| https://code.claude.com/docs/en/changelog/rss.xml | RSS feed of the changelog page |
