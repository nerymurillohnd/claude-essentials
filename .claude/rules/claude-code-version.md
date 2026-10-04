# Claude Code version and currency

- Every fact I give you was verified on Claude Code 2.1.289 on 2026-10-03.
- The minimum version for the tooling and for new plugins is pinned at 2.1.289, in `repo.MIN_CLAUDE_CODE` and in `CLAUDE_CODE_VERSION` in release.yml.
- New plugins declare it in `metadata.minClaudeCodeVersion`, and an author may lower it only after testing on that version.
- A plugin with mods must declare at least 2.1.287.
- Before touching schema, components or releases, read `llms.txt` and every changelog entry newer than 2.1.289.
- Raising the pin is deliberate: both pins change together, and you record the changelog window you reviewed.
- The pin exists because of validator fixes in 2.1.280–2.1.289: names Claude Code cannot install fail (2.1.283), and a plugin was skipped when its folder also held a marketplace manifest (fixed in 2.1.289).
- CI always runs 2.1.289 or newer.
