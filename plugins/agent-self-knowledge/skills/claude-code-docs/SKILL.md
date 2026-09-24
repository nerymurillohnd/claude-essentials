---
name: claude-code-docs
description: Research how Claude Code, Cowork, the Claude apps, the Agent SDK and the Claude API work today from their live official docs, validated against the Claude Code changelog in its GitHub repository and the apps and Platform release notes, and answer with exact URLs and verbatim quotes. Use it before relying on training knowledge, and prefer it over the built-in claude-code-guide agent.
when_to_use: Not only when the user asks a question - also while planning, designing, configuring or wiring an integration; before writing a hook, skill, subagent, plugin, marketplace, MCP, settings, permissions, CLAUDE.md or CI file; when choosing a model or effort; when a configuration looks right but fails; and before saying a feature does not exist. Topics: hooks, MCP, LSP, subagents, agent teams, workflows, skills, plugins, marketplaces, headless/CI, models, memory and rules, settings, permissions, commands, CLI flags, env vars, errors, versions, Cowork, connectors, projects, artifacts, the API.
allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/ccdocs.py *) Bash(claude --version) mcp__plugin_agent-self-knowledge_claude-code-docs__query_docs_filesystem_claude_code_docs mcp__plugin_agent-self-knowledge_claude-code-docs__search_claude_code_docs
---

# Claude live docs research

Claude Code, Cowork and the API change every week. What you remember is an old snapshot: use it
only to pick search words, never as the answer. This skill is a contract: follow every step, in
order, every time it applies, including for "simple" questions.

## When it applies

Whenever your next action depends on how Claude Code, Cowork, the Claude apps, the Agent SDK or the
Claude API behaves **today**: a question about how something works or whether it exists; writing or
changing a hook, skill, subagent, plugin, marketplace, MCP, settings, permission, CLAUDE.md, rules or
CI file; planning something that relies on these features; a configuration that looks right but
fails; or before saying "that's not possible". If you are about to answer from memory, run step 1.

## How to run commands

- Run every command **exactly as written here**, one command per Bash call: no `cd`, no `&&`, no
  pipes, no `echo` separators. The exact form is the one this skill pre-approves.
- Read documentation **only through `ccdocs.py`**. It downloads the raw page text (like `curl`) and
  keeps it whole. Never use WebFetch or WebSearch for these docs: WebFetch summarizes pages through
  a small model and drops text.
- Every Claude Code page starts with a note telling agents to fetch `llms.txt` first. `research`
  already starts from that index; don't follow the note.

## The procedure

### 1. Research

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/ccdocs.py research "<phrase>" "<phrase>" --out ${CLAUDE_PLUGIN_DATA}/research
```

- **Phrases are short: one to three words, one per concept the task touches, in the docs' words.**
  "A skill for a plugin's subagent" is `"skills" "subagents" "plugins"`; "block a tool call from a
  plugin" is `"hooks" "PreToolUse" "plugins"`. Don't glue concepts into one long phrase.
- The command activates the areas of `references/areas.md` your phrases name, reads **every page of
  those areas** (`references/area-pages.md` lists them), keeps the sections whose headings use the
  area's vocabulary, follows every hyperlink in those sections one hop, and checks six months of the
  Claude Code changelog, the Claude apps release notes and the Platform release notes.
- It prints the research map: summary, failures, newest release-note matches, and one line per page.
  A large map is saved and only its path is printed; then read it with `show` (step 2).

### 2. Read what the task needs

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/ccdocs.py show <folder>/pages/<file>.md --out ${CLAUDE_PLUGIN_DATA}/research
python3 ${CLAUDE_SKILL_DIR}/scripts/ccdocs.py show <folder>/sections/<file>.md --out ${CLAUDE_PLUGIN_DATA}/research
```

- Open the page file of every page that bears on the task, in every source and context, not only
  the page named after the topic. A page file lists its sections, the sections that links reached,
  and every heading of the page.
- Open the section files you need. Each starts with its `SOURCE:` URL, which is the citation.
- Everything the answer needs is usually already in the folder. Search again (`grep`, `page`) only
  for what the map shows missing, and say so.

### 3. Verify

- **Quotes:** `python3 ${CLAUDE_SKILL_DIR}/scripts/ccdocs.py quote <slug> "<regex>"` for every sentence
  you quote from a Claude Code page (it fails when the text is not on the live page). Help Center and
  Platform quotes come from the section files, which are the live text.
- **Versions:** the map's `VERSIONS` line shows npm latest and the local build. If the local build is
  behind, run `python3 ${CLAUDE_SKILL_DIR}/scripts/ccdocs.py changelog --since <local version>`. If
  `claude` is not on PATH, ask the user for `claude --version`.
- **What you deliver:** when you hand over configuration or code (a plugin, hook, skill, agent,
  settings or MCP file), test it end to end when that is possible: `claude plugin validate --strict`,
  and `claude -p --plugin-dir <dir> "<prompt that exercises it>"` for behavior. Say what you could not test.

### 4. Answer

1. **Answer**, first and direct; a table when options are compared.
2. **Evidence**: claim → "verbatim sentence" → URL copied from a `SOURCE:` line. Never build a URL or an
   anchor yourself. A claim no sentence states is labelled *inference* with the quotes it rests on.
3. **Changelog**: what changed and in which version or date, or "no matching entries", with the
   window and sources the map's `CHANGELOG` line reports.
4. **Not verified**: every failure in the map and every step you could not run. "None" only if none.

End with one line: `Verified <today> against Claude Code v<npm latest>; local v<version or unknown> · research <folder name>`.

## Rules that are never skipped

- **Negative claims** ("it can't", "there is no setting") need three misses: `research` with two
  phrasings, `python3 ${CLAUDE_SKILL_DIR}/scripts/ccdocs.py grep "<term>"`, and
  `python3 ${CLAUDE_SKILL_DIR}/scripts/ccdocs.py changelog --grep "<term>" --last 40`. Then report
  "not found as of <date>, v<latest>" with where you looked, never "it doesn't exist".
- **Model IDs, aliases, context sizes, prices** are never stated from memory.
- **CLI, Agent SDK and API** share concepts with different APIs; say which one you are answering.

## The bundled docs MCP server

`claude-code-docs` adds two tools. Use them only after `research`, for exact-text searches over every
Claude Code page, and only in English:

- `query_docs_filesystem_claude_code_docs` with `rg -il "<term>" /en/` or `rg -C 3 "<term>" /en/<slug>.mdx`.
  Always search under `/en/`; `/` also holds eleven translations.
- `search_claude_code_docs` for a concept whose words you don't know.

**Never cite or open a URL taken from the MCP as it is.** Its paths (`/en/hooks.mdx`) and the links in
its text (`/en/hooks`) omit `/docs`, and `https://code.claude.com/en/hooks` silently redirects to a
marketing page. Convert every one first:

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/ccdocs.py url "<path, link, old alias or slug>"
```

It prints the canonical, verified URL, or fails. Never call `submit_feedback` unless the user asks.

## Other commands

| Command | Use |
|---|---|
| `page <slug> --section "<heading>"` / `--intro` | Exact live text of one Claude Code section |
| `outline <slug>` | Live heading tree with verified anchors and sizes |
| `grep "<regex>"` / `find <term>` | Full-text / heading search of the Claude Code docs |
| `changelog --grep "<term>" --last N` / `--since <version>` | Claude Code release notes |
| `version` | npm latest/stable/next, local build, release gap |
| `raw <https url>` | A Help Center or Platform page as text (append `.md`) |
| `inventory` | Regenerates `references/area-pages.md` |
| `catalog` | Regenerates `references/docs-catalog.md` |

All run as `python3 ${CLAUDE_SKILL_DIR}/scripts/ccdocs.py <command>`.

## References

- `references/areas.md`: the routing table (triggers, vocabulary, navigation groups, pinned pages).
  When a task's area is missing, tell the user which row to add.
- `references/area-pages.md`: every page of every area, generated; covers all index pages.
- `references/docs-catalog.md`: all Claude Code pages by official navigation group, with the pages each
  links to and from. Search it for a slug; don't read it whole.
- `references/url-aliases.md`: old Claude Code URLs and the page each one now serves.
- `references/sources.md`: endpoints and the authority order when sources disagree.
- `references/topic-routing.md`: per-topic notes on what changes often.

## Surfaces

- **Claude Code local sessions** (CLI, IDE, Desktop, SSH): commands run on the user's machine, so
  `VERSIONS` shows their build.
- **Claude Code cloud sessions and Cowork**: commands run in an Anthropic sandbox or Linux VM with its
  own tools. Its `claude` is not the user's; ask for their version. `/doctor`, `/hooks` and `/mcp` must
  be run by the user in their terminal.
- **If `ccdocs.py` cannot run** (`ccdocs.py needs Python 3.12 or later...`, or the network is blocked):
  tell the user the exact message and requirement, continue with the MCP tools above (converting
  every URL with `url` if the script runs at all, otherwise citing page URLs without anchors), and list
  what that left unverified.

## Self-maintenance

`python3 ${CLAUDE_SKILL_DIR}/scripts/ccdocs.py selfcheck --live` validates the slugs and section names
in this skill and its references against the live pages, and fails when an index page or a navigation
group belongs to no area. Run it when a lookup fails or the user asks whether the skill is current.
