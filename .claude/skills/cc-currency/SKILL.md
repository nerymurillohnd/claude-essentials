---
name: cc-currency
description: Checks the claude-essentials repository against the current Claude Code release - installed and latest versions against the last reviewed release, every changelog entry newer than it, and the rules those entries affect - and records the new review. Use before schema, component, release or distribution work, when a new Claude Code release is out, or when asked whether the repo is current with Claude Code.
---

# Keep the repository current with Claude Code

The repository pins no Claude Code version. The baseline is the **last reviewed release**, the first bullet of `.claude/rules/claude-code-version.md`. Facts come only from official sources: the docs index `https://code.claude.com/docs/llms.txt`, the pages it lists (append `.md` for raw Markdown) and the changelog `https://code.claude.com/docs/en/changelog.md`.

```
- [ ] 1 Versions    installed, latest and stable against the last reviewed release
- [ ] 2 Changelog   every entry newer than the last reviewed release, read in full
- [ ] 3 Impact      rules, docs, scripts and plugins each entry touches
- [ ] 4 Update      rules with date and version; flag conflicts
- [ ] 5 Record      the new last reviewed release and its window
- [ ] 6 Verify      check.py and test-install
```

1. **Versions.** `claude --version`, `npm view @anthropic-ai/claude-code dist-tags --json` and the last reviewed release from the rule file. Report all four numbers: installed, latest, stable and last reviewed.
2. **Changelog.** Download the raw changelog with `curl -sL https://code.claude.com/docs/en/changelog.md -o <scratch>/changelog.md` and read every `<Update label="…">` block newer than the last reviewed release, whole. When none is newer, read the latest five blocks to confirm that nothing in them contradicts a rule, and report "current". Use the `live-docs-research` skill when it is available.
3. **Impact.** For each entry, decide whether it changes a fact in `.claude/rules/`, a guide in `docs/`, a script's assumption (validator output, `claude plugin` flags, install behaviour), or what plugins may rely on. Open the current reference page for every affected feature; a changelog line alone is not enough, and an entry that removes something often does not name it.
4. **Update.** Edit the affected rule with the fact, the version and the date. When the live docs contradict a rule or a doc, the live docs win: say so explicitly, with the quote. For many rules at once, ask the maintainer to start the `/rules-currency` workflow: workflows run many agents and start only on request.
5. **Record.** Replace the last reviewed release in `.claude/rules/claude-code-version.md` and add one line for the window you read: versions, date and what changed. No script, test or gate reads this value, so no other file changes.
6. **Verify.** `scripts/check.py` and `scripts/check.py test-install`, with raw output.

## Report

Lead with: installed, latest, stable, last reviewed, and "current" or "N releases behind". Then a table of relevant entries: version, entry, affected file, action taken or proposed. End with gaps (pages not reachable, entries not verified at runtime).

## Gotchas

- `--help` and `--version` describe this machine, never what changed upstream.
- `metadata.minClaudeCodeVersion` in a plugin is informational: Claude Code does not read it. A plugin declares one only when it relies on a feature of a specific version (mods need 2.1.287), never as a repository default.
- CI always installs the latest Claude Code, so a review is about rules and docs, not about which version CI runs.
