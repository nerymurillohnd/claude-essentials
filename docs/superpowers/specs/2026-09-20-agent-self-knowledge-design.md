# agent-self-knowledge plugin — design

## Goal

Ship the existing `cc-live-docs` skill as a `skill-only` plugin named
`agent-self-knowledge`, whose single skill is `claude-code-docs`, adapting it to
this repository's distribution and documentation contract **without altering how
it retrieves or cites anything**.

The maintainer fixed the scope: adapt to a plugin, adopt the repository's
documentation, improve the `description`, make the skill model-invocable, and
add two behaviours to `SKILL.md` — verbatim quoting and a closing
`HERRAMIENTAS / ACTIVACION / NO ENCONTRADO` report block. Nothing else changes.

## Provenance and authorship

The skill is the maintainer's own work, authored in a claude.ai session to
counter cross-session inconsistency in Claude Code answers. It is not
third-party content, so it ships Apache-2.0 like every other plugin here
([ADR-0005](../../decisions/adr-0005-apache-2-0-license.md)).

## Evidence: the clean-session test (2026-09-20)

The skill was installed unpatched at `.claude/skills/cc-live-docs/`, exercised
from a **separate session with no shared context**, then removed. Four questions
whose ground truth had been established beforehand:

| # | Question | Result |
| --- | --- | --- |
| 1 | Does `plugin.json`'s `skills` replace or add to the default scan? | Correct — adds; not an allowlist |
| 2 | Does the CLI read `worktree.location`? | **Wrong — the key exists, undocumented** |
| 3 | What governs background-session file isolation? | Correct — `worktree.bgIsolation`, default `"worktree"` |
| 4 | What does exit code 2 do in a `PermissionRequest` hook? | Correct — not honored; resolved the docs' internal conflict |

Question 2 matters most, and it is the one the skill got wrong — established on
2026-09-20 while running the eval suite, after this section was first written.
`worktree.location` **exists**. The settings schema shipped inside Claude Code
2.1.278 defines it, with the description *"Directory under which Claude Code
Desktop creates the worktrees of SSH sessions that run on this machine ...
instead of `<project>/.claude/worktrees`. Read by the desktop app from the SSH
host user settings; a location chosen in the desktop app's SSH connection
settings takes precedence. The CLI (--worktree, EnterWorktree, agent isolation)
does not read it yet."* [observed: `strings` over the installed binary].

The published corpus does not carry it: `worktree.location` returns 0 hits
across 99,415 lines of `llms-full.txt`, which documents only `baseRef`,
`bgIsolation`, `sparsePaths` and `symlinkDirectories` [observed, 2026-09-20].
So the skill searched the only corpus it knows, found nothing, and reported the
key as absent — a **false negative**, not a correction. The earlier conclusion
that a verbatim quote had been fabricated was itself wrong: the sentence is
real, it just lives in the binary rather than in the docs.

This is the plugin's material limitation, not a wording defect: the skill's
sources are the published documentation, the changelog and the npm registry,
and Claude Code ships settings keys in none of them. Every bounded negative
claim about a settings key can therefore be a false negative. Recorded as
DEBT-0023.

Two negative findings, both recorded rather than papered over:

- **The skill did not self-invoke.** The test session reported
  `ACTIVACION: manual` despite a prompt that asked for sources four times.
- **Efficiency is unmeasured.** The run cost $1.96 / 3 min wall, but no
  baseline arm ran the same battery without the skill, so no comparative claim
  is made here.

## Verified constraints (live docs + changelog, 2026-09-20, Claude Code 2.1.278)

| Constraint | Source |
| --- | --- |
| `disable-model-invocation` only *disables*; **default is `false`** | `skills#frontmatter-reference` |
| Combined `description` + `when_to_use` truncate at 1,536 chars | `skills#frontmatter-reference`; cap raised to 1,536 in 2.1.105 |
| `when_to_use` is *"Appended to `description` in the skill listing"* | `skills#frontmatter-reference` |
| `when_to_use` passes `claude plugin validate --strict` | observed 2026-09-20 |
| `paths` makes a skill load **only** for matching files | `skills#frontmatter-reference` |
| `${CLAUDE_SKILL_DIR}` available since 2.1.69 | changelog 2.1.69 |
| Skill `allowed-tools` applied to tools the skill invokes since 2.0.74 | changelog 2.0.74 |
| `${CLAUDE_PLUGIN_ROOT}` substituted in plugin `allowed-tools` since 2.1.0 | changelog 2.1.0 |
| A `name` frontmatter field lost the plugin prefix in autocomplete until 2.1.216 | changelog 2.1.216 |
| No release in 401 versions reports a relevant skill failing to auto-invoke | changelog, full scan |
| Anthropic deliberately disables auto-invocation on expensive skills | changelog 2.1.215 (`/verify`, `/code-review`) |
| `bin/` is forbidden here — claude.ai org sync rejects plugins that have one | `plugin-marketplaces` |

## Surfaces

**Used.** `.claude-plugin/plugin.json` (name, displayName, version, description,
author, homepage, repository, license, keywords, `metadata.marketplace`);
`skills/claude-code-docs/` with `SKILL.md`, `references/`, `scripts/`;
README, CHANGELOG, LICENSE.

**Rejected.** `commands/` (the skill is the interface) · `agents/` (a skill-only
plugin ships exactly one skill) · `hooks/hooks.json` (out of the fixed scope;
recorded as debt — see Non-goals) · `.mcp.json`, `.lsp.json`, `monitors/`,
`workflows/`, `outputStyles` (nothing to serve) · `userConfig` (no configurable
value; hosts and TTLs are constants) · `dependencies`, `defaultEnabled`,
`channels` (no relationship to other plugins) · `bin/` (forbidden).

## Decisions

1. **Kind is `skill-only`**, per ADR-0001: one skill, nothing else. The README's
   `**Kind:**` line says so; nothing declares it in `plugin.json`.
2. **`when_to_use` carries the trigger phrases; `description` says what the
   skill does.** The field never appears in the changelog's 401 releases, so its
   introduction cannot be dated. What can be verified is that it costs nothing:
   `claude plugin validate --strict` passes clean on a plugin whose skill
   declares it [observed, 2026-09-20]. The docs define it as *"Appended to
   `description` in the skill listing"*, sharing the same 1,536-char cap, so the
   two fields are one budget — as shipped, `description` measures 491 chars and
   `when_to_use` 591, for 1,082 of the 1,536 available.
   The maintainer chose the dedicated field over folding the phrases into
   `description`, because a field stating *when* belongs apart from the field
   stating *what*. The earlier objection likened it to the `skills[]` array
   rejected in [ADR-0006](../../decisions/adr-0006-changelog-scope-skill-declaration-and-release-tooling.md) §2;
   that analogy does not hold, since `skills[]` had no effect at all while
   `when_to_use` has the same effect as `description`.
3. **`disable-model-invocation` is not declared.** The default is already
   `false`, so declaring it changes nothing and states a mechanism that does not
   exist — the same reasoning that rejected a `skills[]` array in
   [ADR-0006](../../decisions/adr-0006-changelog-scope-skill-declaration-and-release-tooling.md) §2.
4. **`paths` is rejected**: it restricts activation to matching files, and most
   Claude Code questions touch no file at all.
5. **The plugin and its skill carry different names**, breaking this repo's
   skill-only convention of naming both alike (`block-no-verify`,
   `verify-completion`). The maintainer found that a plugin name containing
   "Claude" is rejected, while a skill name is not — so the plugin is
   `agent-self-knowledge` and the skill stays `claude-code-docs`, invoked as
   `/agent-self-knowledge:claude-code-docs`. The restriction is undocumented
   upstream; see DEBT-0021. The `name:` frontmatter field is kept and set to the
   directory name, which is also what 2.1.216 fixed for plugin prefixes.
6. **`allowed-tools` is kept verbatim**, including the
   `Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/ccdocs.py *)` grant.
7. **`ccdocs.py` ships unchanged**, including `raw` — see Accepted risk.
8. **Instructions vs script**: retrieval is deterministic and fragile, so it
   stays a script; judgment (which page, how to cite, when to report a bounded
   negative) stays instructions in `SKILL.md`.
9. **Catalog metadata**: `category: development`, tags covering docs retrieval,
   citations, and the areas the description names.

## Requirements

| Requirement | Minimum | Check | Why |
| --- | --- | --- | --- |
| Claude Code | 2.1.222 | `claude --version` | Below it `metadata` is unrecognized and `--strict` errors (repo-wide baseline) |
| Python | 3.7 | `python3 -V` | `vermin` on `ccdocs.py` reports 3.7; stdlib only, no `uv`, no packages |
| `python3` on `PATH` | — | `command -v python3` | The `allowed-tools` rule invokes it by name |
| Network egress | — | — | `code.claude.com`, `raw.githubusercontent.com`, `registry.npmjs.org` |
| Writable cache | — | — | `${XDG_CACHE_HOME:-~/.cache}/ccdocs`, outside the plugin cache |

**Platforms.** macOS, Linux and WSL are supported. Windows without Git Bash is
**not**: the grant is a `Bash` rule. Cowork, cloud and `-p` sessions are
untested and declared as such rather than claimed.

## Non-goals

- Does not patch, restrict or remove `raw` (see Accepted risk).
- Does not guarantee automatic invocation. Text raises the probability; only a
  hook would make it deterministic, and hooks are outside the fixed scope —
  recorded as debt.
- Does not cover anything but Claude Code. False claims about other platforms
  are untouched by this plugin.
- Does not add Python lint or test gates; blocked by DEBT-0016.
- Makes no comparative efficiency claim without a baseline arm.

## Failure modes

| Failure | Behaviour | Posture |
| --- | --- | --- |
| Docs host returns 4xx/5xx | `sys.exit` with the code, the URL and a `find` hint | **Fail closed** — verified: a 404 aborts; it never yields an empty corpus that would fake a "0 matches" negative |
| No network / TLS / proxy error | `sys.exit` with the underlying error | Fail closed |
| `python3` absent | The Bash call fails; the skill cannot retrieve | Fail closed, visible |
| Cache unwritable | Fetch still returns; only caching is lost | Fail open — correctness does not depend on the cache |
| Page moved or renamed | Error names the URL and points at `find` | Fail closed |
| Three searches return nothing | Reports a bounded fact with date and version, **not** "it does not exist" | By design; `SKILL.md` prescribes it |

## Accepted risk: unvalidated URL fetching in `raw`

`cmd_raw` passes its argument to `fetch()` with no scheme or host validation,
and the `allowed-tools` grant covers the whole script, so
`raw file:///…` and `raw https://any-host/…` run without a permission prompt.
Both were reproduced. On a public marketplace this is inherited by every
installer.

**The maintainer, Nery Samuel Murillo Tejada, decided on 2026-09-20 to publish
as is**, after being shown the vector and a four-line host-allowlist fix, and
after evidence that the fix touches nothing the clean-session test exercised
(that run used `find`, `grep`, `outline`, `page`, `changelog` and `version` —
`raw` was never called).

**Closing condition:** an allowlist in `fetch()` restricted to the hosts the
skill already declares in `allowed-tools`, or removal of `raw`. Tracked in
`docs/maintenance/pending-debt.md`.

## Verification plan

1. **Tests** — `plugins/agent-self-knowledge/test-*.sh` under both `bash` and
   `/bin/bash`: the script's exit status and message on an unreachable host, on
   a moved page, and with an unwritable cache; `selfcheck` validating every slug
   and quoted section name in `SKILL.md`.
2. **Evals** — `claude plugin eval --ablation with-without`, `runsPerCase: 3`
   (repo standard), at least three cases:
   - *positive trigger*: a settings-key question with no skill named;
   - *negative trigger*: an unrelated question that must **not** load it;
   - *negative claim*: a feature that does not exist, graded on a bounded
     "not found as of \<date\>" rather than a flat denial.
3. **Live checks** — `claude -p --plugin-dir`, `claude plugin validate --strict`,
   `npm run check`.
4. **Open, not yet run** — `/skill-doctor` for context cost (the maintainer must
   run it; Claude cannot), and a baseline arm for the unmeasured efficiency
   claim.
5. **Reviews** — `/code-review high`, `/simplify`, `/security-review`,
   `/claude-api prompt-audit` on `SKILL.md`, then `/plugin-release-review`.

## References

- [ADR-0001](../../decisions/adr-0001-marketplace-distribution-model.md) — why a standalone skill ships as a plugin
- [ADR-0003](../../decisions/adr-0003-plugin-versioning-and-tagging.md) — semver, exempt list, tagging
- [ADR-0005](../../decisions/adr-0005-apache-2-0-license.md) — Apache-2.0
- [ADR-0006](../../decisions/adr-0006-changelog-scope-skill-declaration-and-release-tooling.md) — per-plugin changelog; no declarative field without an effect
- https://code.claude.com/docs/en/skills — frontmatter reference, invocation control
- https://code.claude.com/docs/en/plugins-reference — manifest and path behavior
- https://code.claude.com/docs/en/plugin-marketplaces — catalog entries, `bin/` restriction
- https://raw.githubusercontent.com/anthropics/claude-code/main/CHANGELOG.md — 401 releases scanned

## Amendment — 2026-09-20 (build)

Built under the maintainer's fixed scope. Deviations from the plan above, all
recorded rather than silent:

- **Plugin renamed** from `claude-code-live-docs` to `agent-self-knowledge`; the
  skill is `claude-code-docs`. Reason and evidence gap in DEBT-0021.
- **`when_to_use` and the rewritten `description` landed after the first
  build.** The build instruction covered only the verbatim-quoting rule and the
  report block, so the plugin was first assembled with the skill's original
  684-char `description` and no `when_to_use`. The maintainer then rejected that
  description style across the whole catalog and ruled that `when_to_use` be
  declared, so all seven skills in this repository now carry both fields,
  rewritten from each skill's own files rather than from the previous wording.
- **Four rewritten descriptions were invalid YAML, and no existing gate caught
  it.** Dropping the quotation marks left plain scalars containing `": "`, which
  a YAML parser rejects; `block-no-verify`, `ruff-hooks`, `shell-hooks` and
  `verify-completion` all failed to parse while `claude plugin validate
  --strict` and `npm run check` passed [observed, 2026-09-20, Claude Code
  2.1.278]. Fixed by removing every `": "` from the values, and gated by
  `scripts/lib/skill-frontmatter.test.mjs`, which parses every plugin
  `SKILL.md` frontmatter with the repository's `yaml` dependency and enforces
  the 1,536-char listing budget. See DEBT-0022.
- **The `test-*.sh` suite in the Verification plan was not built.** `ccdocs.py`
  is Python and the repository has no Python test gate (DEBT-0016), so the
  script's failure modes are covered by `selfcheck` and by the clean-session
  run, not by an automated suite. The README claims no such suite.
- **Compatibility is `partial`, not `supported`**: retrieval was exercised in a
  real session, but the consumer smoke test from the remote marketplace has not
  been run.
- **Debt records**: DEBT-0019 (`raw` without URL validation, risk accepted) and
  DEBT-0021 (undocumented plugin-name restriction) opened and still pending;
  DEBT-0020 (description style inherited from `plugin-dev`) opened and closed by
  the rewrite; DEBT-0022 opened for the frontmatter gate gap.
