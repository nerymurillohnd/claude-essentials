# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A public, git-backed marketplace of Claude Code plugins, skills, and agents
(see [README.md](README.md)). Everything under `plugins/` is shipped to and
installed by the community — treat it as a public API surface, not scratch
work.

## Commands

```bash
nvm use           # Node from .nvmrc (24.21.0)
npm install       # once
npm run generate  # rebuild .claude-plugin/marketplace.json's plugins[] from plugins/*/.claude-plugin/plugin.json
npm run validate  # schema-check marketplace.json + every plugin.json; cross-check disk <-> catalog; plugin README template contract + root README catalog row
npm run check     # biome:ci, lint:sh, typecheck, knip, tests, generate, validate, validate:claude — the CI gate
npm run biome:fix # apply safe Biome fixes (format + lint + assist); biome:fix:unsafe only by hand, then review
npm run biome:ci  # read-only Biome gate (format, lint, assist) that fails on warnings — used by check and CI
npm run format    # read-only format check (format:fix writes); lint / lint:fix likewise
npm run biome:check / biome:staged / biome:watch  # strict checks: whole repo, staged files, watch mode
npm run lint:sh   # ShellCheck (.shellcheckrc) + shfmt -d on every tracked shell script
npm run typecheck # tsc -p tsconfig.json: max-strict type check of scripts/**/*.mjs (part of npm run check)
npm run knip      # unused files, exports, and dependencies (knip.jsonc; part of npm run check; CI adds --reporter github-actions)
npm test                # node:test unit tests for scripts/lib, plus every tracked plugins/**/test-*.sh suite under bash and /bin/bash (part of npm run check)
npm run validate:claude # `claude plugin validate --strict` (claude on PATH; CI pins CLAUDE_CODE_VERSION) on the marketplace + every plugin
npm run check:versions  # plugin version-bump rules vs origin/main; add -- --verify-tag for claude plugin tag --dry-run (CI job version-check)
npm run labels:sync     # dry-run diff of GitHub labels vs .github/labels.json (--apply/--prune are outward-facing)
```

Run `npm run check` before any commit touching `plugins/`, `schemas/`, or
`scripts/`. Unit tests live next to the modules they test
(`scripts/lib/*.test.mjs`); `npm run validate` checks manifests, labels, and
issue forms. Run validate alone after editing a single plugin manifest when
you don't also need formatting/lint.

CI (`.github/workflows/ci.yml`) runs the same `npm run check` pipeline and
additionally fails if `npm run generate` produces a diff that wasn't
committed.

**TypeScript tooling:** `tsconfig.json` type-checks every `scripts/**/*.mjs`
(`allowJs` + `checkJs`, full `strict` plus the stricter extras, `noEmit` — tsc
never compiles anything) and must stay at 0 errors: it is part of `npm run check`
and a CI step. Type external data honestly (`unknown`, or `any` only where a
schema validates it next), narrow `catch` values with `scripts/lib/errors.mjs`,
and read `process.env` with bracket access plus an explicit missing-value check.

**Knip (`knip.jsonc`):** fix findings, don't ignore them — config hints fail the
run, and entry exports count. `ignoreDependencies` holds only documented,
accepted exceptions. When a plugin ships Node code with its own
`package.json`, add it under `workspaces` with an explicit `entry` (Knip can't
infer an MCP server entry from `.mcp.json`). Never run `knip --fix` in CI.
The hook/CI "runtime vs exempt" rules exist twice (`scripts/lib/version-plan.mjs`
and `.claude/hooks/lib/plugin-paths.sh`); `scripts/lib/plugin-paths.test.mjs`
runs the bash functions to keep them identical. `typescript`, `typescript-language-server`, and
`@types/node` are pinned exactly to the maintainer's globals (6.0.3 / 6.0.0 /
Node 24 line); Claude Code's `typescript-lsp` plugin still runs the global
`typescript-language-server` from `PATH`, which loads this repo's workspace
TypeScript. Never upgrade to TypeScript 7 in this repo or globally without the
official side-by-side recipe: TS 7 ships no `tsserver` API and breaks the LSP.
Every `.mjs` starts with `// @ts-check`; Node scripts are run with `node`
(or `npm run`), so they carry no shebang and no exec bit.

`npm run check` needs ShellCheck, shfmt, and `claude` on `PATH`. Claude Code is
never a repo dependency: CI installs the version pinned by `CLAUDE_CODE_VERSION`
in `ci.yml` and `tag-versions.yml` (`npm run validate` keeps them equal).

## Architecture

**Distribution model — read
[ADR-0001](docs/decisions/adr-0001-marketplace-distribution-model.md) before
proposing anything that touches it.** Claude Code's marketplace mechanism
only distributes *plugins* (`/plugin install <name>@claude-essentials`) —
there's no separate mechanism for a bare skill or bare agent. This repo ships
three shapes through that one mechanism. The shape ("kind") is derived from the
plugin's files and must match its README's `**Kind:**` line — never declared in
`plugin.json`, so `claude plugin validate --strict` passes (ADR-0001 amendment):

- `bundle` — multiple skills/agents/commands/hooks working together
- `skill-only` — a plugin wrapping exactly one skill, nothing else
- `agent-only` — a plugin wrapping exactly one subagent, nothing else

Before proposing a different distribution mechanism, re-verify against live
docs at https://code.claude.com/docs/en/plugin-marketplaces.md — don't assume
the constraint from memory, it may have changed since this was written.

**Generated vs. authored files:** `.claude-plugin/marketplace.json`'s
`plugins` array is generated by `scripts/generate-marketplace.mjs` from every
`plugins/<name>/.claude-plugin/plugin.json` on disk — never hand-edit that
array. A plugin's manifest `name` must equal its directory name under
`plugins/`; both the generator and `scripts/validate-marketplace.mjs` enforce
this and fail the build otherwise. `schemas/marketplace.schema.json` and
`schemas/plugin.schema.json` are the source of truth both scripts validate
against — they encode *this repo's* contract. `schemas/claude-code/` holds
separate, upstream-faithful skeletons of every documented field (plugin
manifest, marketplace, `hooks.json`, `.mcp.json`, `.lsp.json`,
`monitors.json`), each with its docs source in `$comment`; they carry no repo
policy, and `scripts/lib/claude-code-schemas.test.mjs` checks them against the
docs' own examples. When live docs change, update them first.
`schemas/github/` vendors SchemaStore's issue-form and issue-config schemas,
unmodified except for a source `$comment` (GitHub publishes none); `npm run validate` checks every issue form
against them.

**Reviewing a plugin:** before calling a plugin done, and before any plugin
PR, run the repo skill `/plugin-release-review <id>`
(`.claude/skills/plugin-release-review/`). It adds the judgment layer on top of
`npm run validate`: accuracy against the files, cross-artifact consistency,
and README quality. Its checklist is enforced by a Stop hook (ADR-0002
amendment).

**Adding a plugin:** copy one of `templates/plugin-bundle/`,
`templates/plugin-skill-only/`, or `templates/plugin-agent-only/` into
`plugins/<id>/` — see [docs/contributing/plugins.md](docs/contributing/plugins.md).
`templates/README.md` indexes every other reusable template (root README,
plugin README, LICENSE, CHANGELOG, ADR, CODE_OF_CONDUCT, SECURITY,
maintenance ledgers) and the path each gets copied to.

**`docs/` is split by purpose, not by date:** `decisions/` (ADRs — why, not
what), `contributing/` (how to add a plugin), `maintenance/` (pending/resolved
technical-debt ledgers — entries need a stable ID and evidence, not vibes),
`audits/` (dated point-in-time review reports), `superpowers/` (design
plans/specs from skill-driven work, kept after landing).

## Reference documentation

When scaffolding or reviewing a plugin, skill, agent, hook, or marketplace
entry here, these are the priority live sources — not the only ones, but
check these before a general web search:

| Topic | URL |
| --- | --- |
| Skills | https://code.claude.com/docs/en/skills |
| Skills (Agent SDK) | https://code.claude.com/docs/en/agent-sdk/skills |
| Hooks guide | https://code.claude.com/docs/en/hooks-guide |
| Hooks reference | https://code.claude.com/docs/en/hooks |
| LSP servers | https://code.claude.com/docs/en/plugins-reference#lsp-servers |
| LSP / code intelligence | https://code.claude.com/docs/en/discover-plugins#code-intelligence |
| Marketplace — create/distribute | https://code.claude.com/docs/en/plugin-marketplaces |
| Marketplace — discover/install | https://code.claude.com/docs/en/discover-plugins |
| MCP | https://code.claude.com/docs/en/mcp |
| MCP quickstart | https://code.claude.com/docs/en/mcp-quickstart |
| Plugins — create | https://code.claude.com/docs/en/plugins |
| Plugins — reference | https://code.claude.com/docs/en/plugins-reference |
| Plugin evals | https://code.claude.com/docs/en/plugin-evals |
| Plugin dependencies | https://code.claude.com/docs/en/plugin-dependencies |
| Plugin lifecycle — install scopes | https://code.claude.com/docs/en/plugins-reference#plugin-installation-scopes |
| Plugin lifecycle — caching and file resolution | https://code.claude.com/docs/en/plugins-reference#plugin-caching-and-file-resolution |
| Plugin lifecycle — version management | https://code.claude.com/docs/en/plugins-reference#version-management |
| Plugin lifecycle — version resolution and release channels | https://code.claude.com/docs/en/plugin-marketplaces#version-resolution-and-release-channels |
| Plugin lifecycle — CLI (`validate`, `tag`, `update`, …) | https://code.claude.com/docs/en/plugins-reference#cli-commands-reference |
| Subagents | https://code.claude.com/docs/en/sub-agents |
| Subagents (Agent SDK) | https://code.claude.com/docs/en/agent-sdk/subagents |
| Changelog | https://code.claude.com/docs/en/changelog |
| What's new (weekly digest) | https://code.claude.com/docs/en/whats-new |
| Best practices | https://code.claude.com/docs/en/best-practices |

**Always corroborate against the changelog.** Whatever the source of live
data or retrieval — WebFetch, WebSearch, an MCP doc server, a cached read —
before relying on it for a scaffolding or architecture decision in this repo,
also check https://code.claude.com/docs/en/changelog for entries from the
last 6 months. A page can describe current behavior accurately and still
omit a recent breaking change; the changelog is the corroboration step, not
a substitute for reading the doc itself.

There is no single "plugin lifecycle" page; the `Plugin lifecycle — *` rows
above are the sections that together define it. Live docs win over anything
in this repo, templates included.

**Versioning, issues, and labels:** plugins use explicit semver. Every change
to a plugin's runtime files (anything Claude loads; README/docs/LICENSE/CHANGELOG
and `plugin.json` metadata are exempt) bumps `version` and adds a dated CHANGELOG entry, and
CI tags `{name}--v{version}` on merge
([ADR-0003](docs/decisions/adr-0003-plugin-versioning-and-tagging.md),
[versioning.md](docs/contributing/versioning.md)). Issue forms, triage, and the
label taxonomy follow
[ADR-0004](docs/decisions/adr-0004-issue-and-label-protocol.md). Labels live in
`.github/labels.json`, never in the GitHub UI. Generated artifacts:
`marketplace.json` `plugins[]` and the issue forms' **Affected plugin**
dropdown, both from `npm run generate`. Plugins aren't packages: no GitHub
Releases. `*--v*` tags come only from the `Tag plugin versions` workflow and are
immutable (tag ruleset).

## Conventions

- Biome (`biome.json`, pinned exactly: nursery rules are enabled) formats/lints
  all JSON/JS and fails on warnings too (`--error-on-warnings`); JSON is strict
  except `tsconfig*.json`/`*.jsonc`; `noConsole` is off only for the CLI entry
  points `scripts/*.mjs`; `useLiteralKeys` is off because tsconfig's
  `noPropertyAccessFromIndexSignature` requires `process.env["X"]`. ShellCheck and
  shfmt (via `.editorconfig`) cover every `.sh` file.
- The repo and every plugin are Apache-2.0
  ([ADR-0005](docs/decisions/adr-0005-apache-2-0-license.md)): each `LICENSE`
  (no extension) is the verbatim text from
  `templates/LICENSE-Apache-2.0-reusable-template.md`, and `plugin.json`
  `license` is `"Apache-2.0"`. The MIT template is reference-only.
- `CODE_OF_CONDUCT.md` and `SECURITY.md` follow their
  `templates/*-reusable-template.md` counterparts verbatim except for
  filled-in placeholders. Never reformat license text with
  headers/bold/blockquotes — that weakens GitHub/SPDX license detection.
- `main`: PR merges need green `check` + `version-check`; `main` can't be
  deleted or force-pushed (rulesets). Label PRs from `.github/labels.json`.
- Workflows pin every `uses:` to a full commit SHA with a `# vX.Y.Z` comment
  (Dependabot updates them).
- Every `actions/setup-node` step reads `node-version-file: .nvmrc` (never a
  floating `node-version`), so CI runs the exact local Node; `npm run validate`
  enforces it.
- New shell scripts need the exec bit (`git ls-files -s` → `100755`); test
  them by path, not via `bash script.sh`.
- Accepted ADRs are amended by appending `### Amendment — YYYY-MM-DD`, never
  rewritten; resolved debt moves from `pending-debt.md` to `resolved-debt.md`.
- Keep searches scoped to the repo — never `find /` or `find ~` (it triggers
  macOS privacy prompts for Desktop, Downloads, and network volumes).
- Nothing here is pushed to the public GitHub remote, and no GitHub
  repository is created for it, without explicit confirmation in the
  conversation first — this repo's whole purpose is public distribution, so
  a push is not a reversible, low-stakes action.
