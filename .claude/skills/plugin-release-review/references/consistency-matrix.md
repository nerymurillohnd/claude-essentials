# Consistency matrix

Check each row by opening the sources, not from memory. Rows marked *(CI)* are
also enforced by `npm run validate`; still confirm them, because the validator
only runs when someone runs it.

## Identity

| Fact | Must agree across | Notes |
| --- | --- | --- |
| Plugin id | directory name, `plugin.json` `name`, `marketplace.json` entry `name`, badge URLs, `/plugin install <id>@claude-essentials` lines, `plugin: <id>` label, tag prefix `<id>--v` | *(CI: name = directory, catalog drift)* |
| Display name | `plugin.json` `displayName`, README `# <emoji> <Display Name>`, root catalog link text, Cowork install line ("install **<Display Name>**") | *(CI: README title = displayName; catalog link text)* |
| One-line purpose | README blockquote outcome, root catalog "Description" cell | Same meaning; the catalog cell may be shorter, never different |
| Long description | `plugin.json` `description`, `marketplace.json` entry `description` (generated), README intro paragraph | Same claims and the same most important non-goal; no feature in one that the others contradict |
| Keywords | `plugin.json` `keywords` | Describe the problem space a user would search for; no brand names |

## Version and history

| Fact | Must agree across | Notes |
| --- | --- | --- |
| Version | `plugin.json` `version`, top CHANGELOG `## [X.Y.Z] - YYYY-MM-DD`, tag `<id>--vX.Y.Z` after merge | *(CI: version-check)*; version is never duplicated in `marketplace.json` |
| CHANGELOG content | the actual diff of this version | Each entry describes a user-visible change truthfully; numbers in it (test counts, timings) match the README |
| Dates | CHANGELOG date, "Last verified" dates in Compatibility and eval tables | Real dates of the verification, not the writing date |

## Legal

| Fact | Must agree across | Notes |
| --- | --- | --- |
| License | `plugin.json` `license` = `Apache-2.0`, `LICENSE` verbatim from `templates/LICENSE-Apache-2.0-reusable-template.md`, README license badge and License section | Compare the LICENSE text byte for byte (`diff`); never reformat it |
| Third-party material | README License section | Declared with its license, or the sentence removed |

## Behavior and requirements

| Fact | Must agree across | Notes |
| --- | --- | --- |
| Kind | files on disk, README `**Kind:**` line, kind badge, root catalog kind cell | *(CI)* |
| Components | files on disk, README Skills/Agents/Hooks/MCP/Other sections, "What installing changes" | Every shipped component listed; "None" sections really have none |
| Requirements | scripts' actual checks (e.g. version gates in a preflight), README Requirements table and badges, root catalog "Additional requirements" | Same tools, same minimum versions *(CI: badge ↔ table ↔ catalog)*; every stated minimum is enforced by a check, or the README names the one step that needs it; requirements also apply to teammates who inherit a committed config |
| What installing activates | plugin files (hooks/hooks.json, .mcp.json, monitors), `plugin.json`/`marketplace.json` descriptions, root catalog cell, README "What installing changes" | Nothing may claim protection or behavior "on install" that the files don't register; watch for "as soon as", "automatically", "every" |
| Implementation claims | shebangs and interpreters, CHANGELOG, FAQ, `SKILL.md`, README | "Bash handler" vs "Python handler" and similar statements match the files |
| Hook command form | `hooks/hooks.json` (or skill/agent frontmatter hooks), README Requirements minimum Claude Code version | Exec form (`args`) exists only since Claude Code 2.1.139: an older version ignores `args` and runs the bare `command`, which for `bash` means reading the hook payload from stdin as a script. Use shell form with quoted placeholders, or state a minimum at or above the feature's version; check every hook field against the changelog |
| Embedded version strings | `plugin.json` `version`, version headers inside shipped scripts, status/version output | Bumped together, or the difference is documented |
| Reads/writes/network | fact sheet, README Security table, Hooks and side effects, MCP/permissions/network, CAUTION alert | The single most important consistency check *(CI: network-none vs network tools in scripts)*; the Write row includes created folders and anything uninstall deletes |
| Auto-invoked behavior | skill `description` triggers, SKILL.md incidental path, README Skills and Security | A skill that fires on its own discloses any script it then runs and what that script reads |
| Surfaces | README Compatibility table, surface badges, root catalog status cells | *(CI: badge ↔ catalog)*; ✅ only with a dated remote-marketplace install; "Last verified" names its source honestly (official docs vs a GitHub issue vs an undocumented variable) |
| Numbers | test counts, timings, eval scores in README and CHANGELOG | Re-measure or remove when the code changes; eval claims must be testable with the tools the case grants |
| License text | `LICENSE` bytes | *(CI: SHA-256 of the verbatim Apache-2.0 text)* |
| CHANGELOG links | every `## [X]` heading | *(CI: a link definition per heading)*; released entries are never rewritten, only new ones added |

## Repository surfaces

| Surface | Check |
| --- | --- |
| Root README catalog | Row present, sorted, wording current *(CI: structure)* |
| `marketplace.json` | Regenerated (`npm run generate` leaves no diff) *(CI)* |
| Issue forms | "Affected plugin" dropdown lists the plugin *(CI)* |
| Labels | `plugin: <id>` exists on GitHub after the Labels workflow runs (`gh label list`) |
| Tags | After merge: `git ls-remote --tags origin '<id>--v*'` shows the new version |
| Links | Every relative link in the README resolves; external links point at the right pages |
