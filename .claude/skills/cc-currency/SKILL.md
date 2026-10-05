---
name: cc-currency
description: Checks the claude-essentials repository against the current Claude Code release - installed and latest versions against the pin, every changelog entry newer than the pin, and the rules those entries affect - and raises the pin when the maintainer approves. Use before schema, component, release or distribution work, when the session start reports a newer Claude Code, or when asked whether the repo is current with Claude Code.
---

# Keep the repository current with Claude Code

The pin is `MIN_CLAUDE_CODE` in `scripts/repo.py`; the `docs` gate lists every copy of it (`PIN_SITES` in `scripts/check_docs.py`). Facts come only from official sources: the docs index `https://code.claude.com/docs/llms.txt`, the pages it lists (append `.md` for raw Markdown) and the changelog `https://code.claude.com/docs/en/changelog.md`.

```
- [ ] 1 Versions    installed, latest and stable against the pin
- [ ] 2 Changelog   every entry newer than the pin, read in full
- [ ] 3 Impact      rules, docs, scripts and plugins each entry touches
- [ ] 4 Update      rules with date and version; flag conflicts
- [ ] 5 Raise pin   only with the maintainer's approval
- [ ] 6 Verify      check.py and test-install
```

1. **Versions.** `claude --version`, `npm view @anthropic-ai/claude-code dist-tags --json` and `python3 -c "import sys; sys.path.insert(0, 'scripts'); import repo; print(repo.MIN_CLAUDE_CODE)"`. Report all four numbers: installed, latest, stable and the pin.
2. **Changelog.** Download the raw changelog with `curl -sL https://code.claude.com/docs/en/changelog.md -o <scratch>/changelog.md` and read every `<Update label="…">` block newer than the pin, whole. When none is newer, read the latest five blocks to confirm that nothing in them contradicts a rule, and report "current". Use the `live-docs-research` skill when it is available.
3. **Impact.** For each entry, decide whether it changes a fact in `.claude/rules/`, a guide in `docs/`, a script's assumption (validator output, `claude plugin` flags, install behaviour), or what plugins may rely on. Open the current reference page for every affected feature; a changelog line alone is not enough, and an entry that removes something often does not name it.
4. **Update.** Edit the affected rule with the fact, the version and the date. When the live docs contradict a rule or a doc, the live docs win: say so explicitly, with the quote. For many rules at once, ask the maintainer to start the `/rules-currency` workflow: workflows run many agents and start only on request.
5. **Raise the pin**, only after the maintainer approves: change `MIN_CLAUDE_CODE`, then run `scripts/check_docs.py` and update every site it names (`release.yml`, the version rule, CLAUDE.md, `docs/releasing.md`, the bug report form). Record the reviewed window in `.claude/rules/claude-code-version.md`, and write a new dated ADR that supersedes the minimum-version ADR.
6. **Verify.** `scripts/check.py` and `scripts/check.py test-install`, with raw output.

## Report

Lead with: installed, latest, stable, pin, and "current" or "N releases behind". Then a table of relevant entries: version, entry, affected file, action taken or proposed. End with gaps (pages not reachable, entries not verified at runtime).

## Gotchas

- `--help` and `--version` describe this machine, never what changed upstream.
- `metadata.minClaudeCodeVersion` in a plugin is informational: Claude Code does not read it, so a pin bump never blocks users on older versions.
- A raised pin changes new plugins' default minimum and the README badges; CI always installs the latest Claude Code. It is a reviewed change, not a routine edit.
