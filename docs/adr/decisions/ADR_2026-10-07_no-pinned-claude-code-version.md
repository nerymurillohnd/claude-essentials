---
status: accepted
date: 2026-10-07
decision-makers:
  - "Nery Samuel Murillo (maintainer)"
supersedes: ADR_2026-10-03_minimum-claude-code-version.md
superseded-by: none
---

# No pinned Claude Code version

## Purpose

Remove the repository-wide Claude Code version pin (`repo.MIN_CLAUDE_CODE`, 2.1.289) and say what replaces it.

## Scope

`scripts/repo.py`, `scripts/check_docs.py` (`PIN_SITES`), `scripts/claude_hooks.py` (session-start notice), `scripts/new_plugin.py`, `scripts/sync_readmes.py`, the README templates, the rules and skills that mention the pin, and `/cc-currency`. A plugin's own `metadata.minClaudeCodeVersion` stays, as an optional declaration.

## Context and problem statement

The pin was meant as an honest minimum for users and a reproducible CI. Neither held:

- CI stopped installing the pinned version on 2026-10-05 (ADR unpinned-tooling-and-shebang-interpreters).
- Claude Code does not read `metadata`: the official plugin reference calls it a "free-form object for your own data. Claude Code doesn't read it" (checked 2026-10-06), so the minimum never blocked an older install.
- The session-start notice compared the installed version with the pin, so it fired for every release already reviewed (DEBT-003).
- Raising the pin touched five documents, a gate and a test, for a value that gated nothing (DEBT-002).

## Decision drivers

- State only facts that something enforces or that a reader can verify.
- Keep the currency routine that finds stale rules.
- Keep plugin changes out of a tooling decision, so no plugin needs a release.

## Considered options

- Remove the pin and keep a last reviewed release in the version rule
- Relabel the pin as a tested version
- Keep the pin and add a plugin-side check

## Decision outcome

Chosen option: **remove the pin**, because nothing enforces it and the information it carried is better kept as dated facts in the rules.

- `repo.MIN_CLAUDE_CODE`, `PIN_SITES`, the session-start notice and the default `minClaudeCodeVersion` of new plugins are removed.
- `.claude/rules/claude-code-version.md` holds the last reviewed release; `/cc-currency` reads every changelog entry newer than it and replaces it after a review.
- A plugin declares `metadata.minClaudeCodeVersion` only when it relies on a feature of a specific version (mods need 2.1.287, `MOD_MIN_CLAUDE_CODE`). Its README then shows the badge and the version; without it, the README asks for a current release.
- The root README asks for a current Claude Code and sends readers to each plugin's README for specific versions.

### Consequences

- Good, because no document claims a minimum that nothing enforces.
- Good, because a Claude Code review no longer needs the maintainer to raise a constant in several files.
- Bad, because the session no longer warns when Claude Code is newer than the last review; the maintainer runs `/cc-currency` before schema, component, release or distribution work (CLAUDE.md).
- Bad, because a user on an old Claude Code gets no stated minimum for plugins without a declared one.

### Confirmation

| Criterion or claim                                          | Verification method                        | Evidence or result                              | Responsible party                          | Review condition                         |
| ----------------------------------------------------------- | ------------------------------------------ | ----------------------------------------------- | ------------------------------------------ | ---------------------------------------- |
| No script, test or document names a pinned version constant | `grep -rnE "MIN_CLAUDE_CODE\b              | PIN_SITES"`outside`docs/adr/decisions/`         | only `MOD_MIN_CLAUDE_CODE`, the mods floor | Claude                                   | When a rule or script mentions a version |
| A plugin without a declared minimum renders a valid README  | `tests/test_gates.py` `MinimumVersionTest` | passes with `scripts/check.py`                  | Claude                                     | When the README generator changes        |
| Existing plugin READMEs are unchanged                       | `git diff --stat -- plugins`               | no plugin file changed, so no release is needed | Claude                                     | When a plugin drops its declared minimum |

## Pros and cons of the options

### Remove the pin

- Good, because it deletes a value that gated nothing.
- Bad, because users lose a stated minimum for plugins that declare none.

### Relabel as a tested version

- Good, because it keeps an informative number.
- Bad, because it still needs a constant, five copies and a gate for information that already lives in the dated rules.

### Keep the pin and add a plugin-side check

- Good, because it would enforce the minimum for mods.
- Bad, because every plugin would ship a startup hook for a floor Claude Code does not offer to enforce.

## More information

Replaces [ADR minimum-claude-code-version](ADR_2026-10-03_minimum-claude-code-version.md). Closes DEBT-002 and DEBT-003. Approved by the maintainer in the Claude Code session of 2026-10-07.
