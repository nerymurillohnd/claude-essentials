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
