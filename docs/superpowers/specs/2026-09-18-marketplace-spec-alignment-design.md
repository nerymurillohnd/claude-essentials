# Marketplace spec alignment and local authoring automation — design

- **Date**: 2026-09-18
- **Status**: proposed (awaiting maintainer approval)
- **Input**: the maintainer's marketplace specification (§1–§17), compared
  against the repository at `b1da810`, Claude Code CLI 2.1.277, and live docs.

## 1. Scope decisions (maintainer, 2026-09-18)

| Decision | Outcome |
| --- | --- |
| Repository identity | Nery's personal, public, community marketplace — not a company repository. Nery consumes it like any user: remote marketplace add + per-plugin install. Private or company-specific plugins belong in a separate private marketplace. |
| License | **Apache-2.0** for the repository and every plugin — done, [ADR-0005](../../decisions/adr-0005-apache-2-0-license.md). MIT template kept as reference only. |
| Evals | Structural gate now (suite must exist and cover trigger / non-trigger); `claude plugin eval` runs manually with a hard budget. CI eval runs (spec phase 4) become a tracked debt item. |
| Local automation | Proposal below; maintainer asked for a risk-first, automation-first design. |

## 2. Spec claims that are wrong, unverified, or superseded

Live docs win (repo rule). These spec statements are **not** carried into
repo docs as written:

| Spec § | Claim | Finding | Handling |
| --- | --- | --- | --- |
| 2.8, 13 | Pin each plugin `source` with `ref`/`sha` | Correct **for entries whose code lives in another repository**: `ref`/`sha` exist only on `github`, `url`, `git-subdir` sources, and SHA pinning is the norm there (2026-09-18 tally: `claude-plugins-community` 2274 of 2282 entries; `claude-plugins-official` 258 of 310). Not applicable to in-repo plugins: relative-path sources resolve from the marketplace checkout and can't be pinned — the official catalog's 52 in-repo plugins aren't. | In-repo plugins: explicit semver + immutable `{name}--v{version}` tags (ADR-0003), unchanged. Third-party entries, if ever listed: SHA-pinned sources (open decision, §8). When a plugin from here is submitted to `claude-community`, Anthropic's pipeline pins our repo by SHA and bumps it on push; our explicit `version` still gates delivery. |
| 5 | `"$schema": "./schemas/..."` | Resolved relative to `.claude-plugin/marketplace.json`, so it must be `../schemas/...` (the current value). | Keep current. |
| 6 | "14 sections" | The list has 15. | Use the 15-section list. |
| 7 | `commands/` is legacy | **Verified**: plugins.md says to use `skills/` for new plugins. | Templates and rules say so. |
| 7 | Plugin `settings.json` supports only `agent`, `subagentStatusLine` | **Verified** (plugins.md); unknown keys are silently ignored; root `settings.json` beats `plugin.json` `settings`. | Encoded in `schemas/claude-code/plugin-manifest.schema.json`. |
| 4.4 | Same-marketplace symlinks are dereferenced | Not found in current docs. | Not relied on; duplication or `dependencies` only. |
| 7 | npm/bun lockfiles auto-installed, yarn/pnpm skipped | Not found in current docs. | Not relied on. |
| 7 | Top-level `bin/` is on Bash `PATH`; rejected for claude.ai org-settings distribution | **Verified** (plugins.md). | No top-level `bin/`; use `scripts/` via `${CLAUDE_PLUGIN_ROOT}`. |
| — | (not in spec) A single-skill plugin may put `SKILL.md` at the plugin root | **Verified** (plugins.md). | Gap: `pluginKind()` only recognizes `skills/<name>/SKILL.md`. Either support it or forbid it explicitly in the contract. |
| 7, 8 | Per-component Cowork support matrix | Docs confirm plugins run in Code and Cowork, not Chat; no per-component matrix found. | Plugin READMEs declare *tested* surfaces with a date; untested = "Not tested", never "Yes". |
| 7, `${…}` | `${CLAUDE_PLUGIN_ROOT}`, `${CLAUDE_PLUGIN_DATA}` | The pasted spec had them expanded into a local cache path by skill-argument substitution. | Artifacts use the literal variables. |

Verified and adopted: `defaultEnabled`, `userConfig.sensitive`, root
`version`/`description`, `metadata.pluginRoot` (≥2.1.239), `renames`
(`null` = removed), reserved names (incl. `npm`/`pip`/`uv`/`cargo`/`github`/`gh`
since 2.1.275), `claude plugin eval` flags (checked against `claude plugin help eval` on 2.1.277),
`experimental.evals` (plain relative names, e.g. `quality/evals`, not `./`), `tool_used` graders with `min`/`max`/`arm`, `.mcp.json` transport key `type` (not `transport`), consumer-test isolation via `CLAUDE_CONFIG_DIR`.

All documented fields now have upstream-faithful skeleton schemas in
`schemas/claude-code/` (plugin manifest, marketplace, hooks, MCP, LSP,
monitors), tested against the docs' own examples. SchemaStore's published
plugin/marketplace schemas lag the docs and are not used as the source.

## 3. Gap analysis (repo vs spec)

| Area | Current | Target | Phase |
| --- | --- | --- | --- |
| Scope statement | Implicit | Explicit in README, CLAUDE.md, ADR-0006 | 1 |
| License | MIT everywhere | Apache-2.0 everywhere (**done**); validator SPDX/hash check pending | 1 |
| `plugin.schema.json` | requires `name`, `description`, `version` | + `displayName`, `author{name,url}`, `license`, `repository`, `homepage`, `keywords` (≥3); declares `defaultEnabled`, `userConfig`, `experimental` | 1 |
| `marketplace.schema.json` | `renames` values must be strings | **Bug:** rejects `null`, the documented value for a removed plugin, which `versioning.md` tells contributors to use. Fix to `string \| null`; add root `version`, `allowCrossMarketplaceDependenciesOn` | 1 |
| Plugin README | Emoji template, no required sections | 15 fixed English headings, validated | 2 |
| Evals | None | `evals/` in every template; validator requires ≥1 positive and ≥1 negative case when skills exist | 2 |
| Root README catalog | Hand-written placeholder | Generated table (Plugin, Description, Claude Code, Cowork, Requirements) between markers | 2 |
| Requirements script | No convention | `scripts/check-requirements.sh` template; validator enforces exec bit + runs it with `--check-only` in CI | 2 |
| Secret / private-content scanning | `.gitignore` only | Pinned gitleaks in CI + `.gitleaks.toml`; repo content scanner for private paths and denylisted terms | 3 |
| `CODEOWNERS` | Missing | Added (see risk R6) | 3 |
| `SECURITY.md`, `CONTRIBUTING.md` | Partial vs §15 | Full §15 content | 3 |
| `.claude/rules/`, skills, agents | None | §5 below | 4 |
| `CLAUDE.md` | 150+ lines, some procedure | Facts only; procedures move to rules/skills | 5 |

## 4. Enforcement design (what is gated, where)

One rule, one enforcement point, one source of truth. The same Node modules
back CI, `npm run check`, hooks, and skills.

| Rule | Source of truth | Local (hook/skill) | CI |
| --- | --- | --- | --- |
| Manifest contract | `schemas/plugin.schema.json` | post-edit (via `npm run validate`) | `check` |
| README headings | `scripts/lib/readme-contract.mjs` (exported heading list) | `new-plugin`, `plugin-preflight` | `check` |
| Eval suite shape | `scripts/lib/evals.mjs` | `new-plugin`, `plugin-preflight` | `check` |
| License coherence | schema `license: "Apache-2.0"` + LICENSE text hash | — | `check` |
| No private content | `.github/public-content.json` (patterns) + `scripts/lib/public-content.mjs` | PostToolUse on `plugins/**`, `templates/**` | `check` |
| No secrets | `.gitleaks.toml` | `plugin-preflight` (if gitleaks installed) | new `secrets` job, pinned + checksummed |
| Version / changelog / tag | existing `version-plan.mjs` | existing hooks | `version-check` |
| Eval cost ceiling | PreToolUse Bash guard | blocks `claude plugin eval` without `--max-cost-usd` and `--no-publish` | n/a |

Self-consistency test: a unit test renders each template with dummy values and
asserts it passes every validator. Templates and validators cannot drift.

## 5. Local authoring automation (`.claude/`)

Design principles: deterministic logic lives in tested `scripts/` modules;
skills orchestrate and interpret; agents review; hooks enforce. Anything that
costs money or touches the remote is user-only.

### 5.1 Path-scoped rules (`.claude/rules/`, `paths:` frontmatter)

| File | `paths` | Content (facts, not procedures) |
| --- | --- | --- |
| `plugin-authoring.md` | `plugins/**`, `templates/plugin-*/**` | Publication contract; self-contained (no `../`); `${CLAUDE_PLUGIN_ROOT}`/`${CLAUDE_PLUGIN_DATA}`; portable-skill-first; `defaultEnabled: false` for costly capabilities; secrets only via `userConfig.sensitive`; no top-level `bin/` |
| `evals.md` | `**/evals/**` | Case layout, positive/negative requirement, mocks for every MCP tool, never real services, results gitignored |
| `workflows.md` | `.github/**` | SHA-pinned `uses:`; `CLAUDE_CODE_VERSION` kept equal across workflows; least-privilege `permissions:` |
| `tooling.md` | `scripts/**`, `schemas/**` | Tests beside modules; schemas are the source of truth; generator and validator change together |

### 5.2 Project skills (`.claude/skills/`)

| Skill | Invocation | What it does | Backing code |
| --- | --- | --- | --- |
| `new-plugin` | user-only (`disable-model-invocation: true`), `arguments: [name, kind]` | Validates name (kebab, ≤42, not reserved, not taken); copies template; interviews for description, keywords, and trigger/non-trigger phrasing; writes eval cases from those answers; runs `generate` + `validate`; dispatches `plugin-auditor` | `scripts/new-plugin.mjs` (tested) |
| `plugin-preflight` | user + model (read-only; triggers on "ready to open a PR / publish") | Dynamic context (`!` injection) of `check:versions --json`, changed plugins; runs `npm run check`, `--verify-tag`, `claude plugin details` per changed plugin, gitleaks, content scan; outputs a go/no-go table with the exact failing rule | existing scripts + `scripts/preflight.mjs` |
| `plugin-eval` | user-only, `arguments: [plugin, budget]` | Runs `claude plugin eval` with pinned `--model`/`--judge-model`, `--no-publish`, required `--max-cost-usd`, `--json`; summarizes Δ per case; writes a dated summary to `plugins/<name>/evals/BASELINE.md` (tracked) so Δ history survives | — |
| `consumer-smoke` | user-only, `arguments: [plugin]` | Post-merge: verifies the plugin as a consumer from the **remote** marketplace in a throwaway `CLAUDE_CONFIG_DIR` (documented env var), never `--plugin-dir` and never the maintainer's real config; records surface + date in the README Compatibility table | `scripts/consumer-smoke.mjs` |
| `docs-drift-audit` | user-only, `context: fork`, `agent: live-docs-verifier` | Re-verifies schemas, templates, and docs against live docs + 6-month changelog; writes `docs/audits/YYYY-MM-DD-docs-drift.md`; opens `DEBT-*` entries for each misalignment | — |

### 5.3 Subagents (`.claude/agents/`)

| Agent | Tools | Model / memory | Role |
| --- | --- | --- | --- |
| `plugin-auditor` | `Read, Grep, Glob, Bash`; `disallowedTools: Write, Edit` | `sonnet`, `memory: project` (tracked in `.claude/agent-memory/plugin-auditor/`, recurring findings become checklist items) | Audits one plugin: contract, §14 security, description trigger quality (specific vs generic), token cost, Cowork claims vs evidence, README honesty ("What it does not do", "Limitations"). Returns ranked findings with file:line. |
| `live-docs-verifier` | `Read, Grep, WebFetch, WebSearch` | `sonnet`, no memory (facts go to `docs/audits/`, not agent memory, to avoid stale recall) | Given claims, returns VERIFIED/WRONG/PARTIAL/NOT FOUND with quote + URL, always cross-checking the changelog. |

### 5.4 Hooks (additions to `.claude/settings.json`)

| Event / matcher | Script | Behavior |
| --- | --- | --- |
| PreToolUse `Bash` | `guard-eval-budget.sh` | Deny `claude plugin eval` lacking `--max-cost-usd` or `--no-publish` |
| PostToolUse `Edit\|Write\|Bash` | extend `post-edit.sh` | Run public-content scan on changed files under `plugins/**`, `templates/**`; block on hit |
| SessionStart | extend `session-start.sh` | Report: days since last `docs/audits/*docs-drift*`, plugins without `evals/BASELINE.md`, local CLI vs `CLAUDE_CODE_VERSION` |

### 5.5 Saved workflow (`.claude/workflows/plugin-review.js`)

Runs only when the maintainer invokes it by name. Parallel review of one
plugin: contract, security, trigger quality, docs drift; then an adversarial
verify pass per finding. Under 10 agents. Used before the first release of
each plugin and on third-party plugin PRs.

## 6. Risks and weaknesses

| ID | Risk | Mitigation |
| --- | --- | --- |
| R1 | Heading-based README validation is brittle | One exported heading list; template self-test; error message prints the missing heading |
| R2 | Structural eval gate proves shape, not quality | `plugin-auditor` reviews prompts; `BASELINE.md` makes Δ visible in PRs; spec rule "Δ ≤ 0 needs written justification" enforced by review |
| R3 | Eval cost and early-access availability | User-only skill, budget guard hook, CI phase 4 deferred as DEBT |
| R4 | Cowork claims can't be tested in CI | "Yes" requires a dated consumer-smoke record; default "Not tested" |
| R5 | `claude plugin details` has no `--json` on 2.1.277 | Report-only in preflight, never a gate |
| R6 | CODEOWNERS + "require code-owner review" blocks a solo maintainer's own PRs | Add CODEOWNERS for auto-review requests on third-party PRs; do **not** enable required code-owner review until a second maintainer exists |
| R7 | Public-content denylist itself leaks private terms | Patterns are generic (absolute home paths, `.env`, key formats); any org-specific terms stay in a gitignored local pattern file |
| R8 | Relicense misses a file | Validator checks every `LICENSE*` against the canonical Apache text; grep gate for "MIT" badges |
| R9 | Enabling GitHub secret scanning / push protection is an outward-facing settings change | Done only after explicit maintainer confirmation, via `gh api` |
| R10 | CI pins 2.1.276 while local is 2.1.277 | Bump `CLAUDE_CODE_VERSION` in phase 1 after changelog review |

## 7. Delivery plan (one PR per phase)

0. **Done on `chore/relicense-apache-2.0`**: ADR-0005 (Apache-2.0), relicense, Apache/MIT templates, upstream skeleton schemas + tests.
1. **Foundation**: ADR-0006 (scope + publication standard), repo contract schemas layered on `schemas/claude-code/`, `renames: null` fix, license check in validator, CLI pin bump.
2. **Templates and validators**: 15-heading README, evals skeletons, check-requirements template, generated root catalog, validator modules + tests.
3. **Security**: gitleaks job, content scanner, CODEOWNERS, SECURITY.md/CONTRIBUTING.md to §15, `.gitignore` for `**/evals/results/`.
4. **Local automation**: rules, skills, agents, hooks, saved workflow.
5. **Consolidation**: slim CLAUDE.md, docs index, DEBT entries (CI evals, per-component Cowork matrix, unverified spec claims).

## 8. Open decision: third-party plugins in the catalog

The maintainer's goal ("top-tier plugins in one place instead of downloading
from several") can mean two things:

1. **Author-hosted only** (current tooling): every plugin lives in `plugins/`,
   relative sources, semver + tags. Nothing to change.
2. **Also curate plugins hosted elsewhere**: entries need `url`/`git-subdir`
   sources pinned by 40-char `sha` (the ecosystem norm above). Current tooling
   contradicts that: the generator only emits on-disk plugins, the repo
   marketplace schema only accepts string sources, and the validator requires
   disk <-> catalog parity. It would need an authored `external-plugins.json`
   merged by the generator, a review gate per SHA bump (each bump ships new
   third-party code under this marketplace's name), and a scheduled workflow
   that proposes bumps as PRs.

## 9. README contract (consolidated 2026-09-18)

Spec §15 and the previous templates were merged into
`templates/plugin-README-reusable-template.md` (master) and
`templates/root-README-recommended-template.md` (master). Their shape
instances (`templates/plugin-*/README.md`, root `README.md`) are aligned.

| Spec §15 plugin section | Consolidated heading | Kept from the previous template |
| --- | --- | --- |
| Qué hace | 🎯 What it does | Use-case table (scenario → help → result) |
| Qué no hace | 🚫 What it does not do | "Not a fit when" |
| Instalación | ⚡ Installation | Success signal; installation effects; update/disable/remove (now with Cowork) |
| Skills disponibles | 🧠 Skills | — (new: namespaced `/plugin:skill` invocation) |
| Agentes disponibles | 🤖 Agents | — (new) |
| Hooks y efectos secundarios | 🪝 Hooks and side effects | — (new) |
| MCP, permisos y red | 🔌 MCP, permissions, and network | — (new: least privilege, Cowork line) |
| Requisitos | 📋 Requirements | Requirements table, now with check commands |
| Verificación | ✅ Verification | Consumer smoke test, maintainer checks; new eval Δ table |
| Compatibilidad | 🧭 Compatibility | "Last verified"; new per-surface status vocabulary |
| Ejemplos | 💡 Examples | — (new) |
| Seguridad | 🔐 Security | Runtime-effects table, human-approval boundary |
| Limitaciones | 🚧 Limitations | Limitation / symptom / recovery table |
| Changelog | 📝 Changelog | — |
| Licencia | 📄 License | — |
| (not in spec) | 🧩 Other components (optional), ❓ FAQ (optional) | Kept |

Fixed a defect found during the merge: the skill-only shape told users to run
`/{{skill-name}}`, but plugin skills are always namespaced
(`/plugin-id:skill-name`).

Phase 2 validator input: the required heading list above, in order, is the
contract `scripts/lib/readme-contract.mjs` will enforce.
