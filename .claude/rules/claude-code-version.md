# Claude Code version and currency

- Every fact I give you was verified on Claude Code 2.1.289 on 2026-10-03.
- The minimum version new plugins declare is pinned at 2.1.289, in `repo.MIN_CLAUDE_CODE`; it is also the minimum shown in the README badges. CI installs the latest Claude Code (ADR unpinned-tooling-and-shebang-interpreters).
- New plugins declare it in `metadata.minClaudeCodeVersion`, and an author may lower it only after testing on that version.
- Claude Code does not read `metadata` (checked 2026-10-04): the value informs users and never blocks older versions.
- A plugin with mods must declare at least 2.1.287.
- Before touching schema, components or releases, read `llms.txt` and every changelog entry newer than 2.1.289.
- Raising the pin is deliberate: change `repo.MIN_CLAUDE_CODE` and its copies (`PIN_SITES` in `scripts/check_docs.py`), and record the changelog window you reviewed.
- The pin exists because of validator fixes in 2.1.280–2.1.289: names Claude Code cannot install fail (2.1.283), and a plugin was skipped when its folder also held a marketplace manifest (fixed in 2.1.289).
- CI always runs 2.1.289 or newer.
- Reviewed window 2.1.291 on 2026-10-06 with `/cc-currency`: installed and latest 2.1.291, stable 2.1.285. The entry holds two regression fixes only (cloud sessions dropping permission answers, the last messages of a session lost on quit) and changes no rule. Re-read of 2.1.290 for this release: a plugin's **async** `Stop` hook with an unquoted script path under a folder with a space made Claude reply in an endless loop; `svelte-development` runs its `Stop` hook synchronously and quotes `"${CLAUDE_PLUGIN_ROOT}"`, so the fix confirms the shape already shipped. The pin stays at 2.1.289.
- Reviewed window 2.1.290 on 2026-10-05 with `/cc-currency`: installed and latest 2.1.290, stable 2.1.285. The entries that touch skills (multi-line `!` blocks with CRLF fixed on Windows, `!` commands with raw control characters refused, skills found by their `SKILL.md` name) change no rule, and plugin skills here use no `!` injection. The pin stays at 2.1.289; the session-start notice keeps flagging 2.1.290 until the maintainer raises it, because it compares only the installed version with the pin.
