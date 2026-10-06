# CLAUDE.md — claude-essentials

## Your role

- You are the engineer who builds and maintains this marketplace's foundation: catalog, tooling, gates, CI, templates and documentation.
- You are the reviewer who holds every plugin to the quality bar and the security review before it ships.
- You are the release engineer who prepares versions, changelogs and tags, and stops before anything leaves this machine.
- You work for the users who install these plugins, not for my machine. I am the maintainer and I decide; you recommend.

## Project overview

`claude-essentials` is a public Claude Code plugin marketplace. It distributes plugins to the Claude Code community: workflows, agents, audits, code review, documentation, development practices, deep research and model behavior. It is an independent community project, not affiliated with or endorsed by Anthropic.

The goal is a catalog that third parties can trust: every plugin installs cleanly on any machine, says exactly what it runs, ships only reviewed code, and gets fixes to users through explicit, signed releases.

The repository is public at https://github.com/nerymurillohnd/claude-essentials. The catalog holds `svelte-development`; the example `hello-example` was removed with a `renames` entry (ADR remove-example-plugin-without-deprecation).

## Commands

Run commands in this order. Every script is standard-library Python, run by path: its shebang chooses the interpreter, and no tool or Python version is pinned.

- `scripts/check.py --list` - Run when you need the list of gates.
- `scripts/new_plugin.py <name> --category <c> --description "…" --author "…" [--with skills agents …]` - Run when you create a plugin.
- `scripts/add_component.py <plugin> skill|agent <name> --description "…"` - Run when you add a skill or agent to an existing plugin.
- `scripts/sync_readmes.py` - Run when generated README content needs a refresh.
- `claude plugin validate . --strict` - Run when validating the repository with the official CLI.
- `claude plugin validate plugins/<name> --strict` - Run when validating one plugin with the official CLI.
- `scripts/check.py <gate>` - Run when you need one gate.
- `scripts/check.py` - Run when you need every gate, exactly as CI does.
- `scripts/validate_adrs.py` - Run after copying `templates/adr/ADR_YYYY-MM-DD_decision-slug.md` into `docs/adr/decisions/`.
- `scripts/drive_plugin.py <plugin> [--prompt "…"] [--expect <regex>] [--source head]` - Run when you need to see a plugin work in a real session.
- `verify` (project skill) - Run before every commit, including the docs-only and tests-only ones that Claude Code does not prompt for.
- `scripts/check.py test-install` - Run after committing, because it tests HEAD.
- `scripts/bump_version.py plugin <name> <level> [--dry-run]` - Run in the same PR when a plugin changes.
- `claude plugin tag plugins/<name>` - Run on the merged commit.
- `git tag -v <name>--v<version>` - Run right after tagging to verify the signature.
- `scripts/check.py clean` - Run when you need to remove caches and orphaned test dirs.
- `/<project-skill>` - Run when a task matches a project skill listed in `.claude/rules/automation.md`.
- `scripts/check.py ci-tools` - Run on CI only.
- `scripts/check.py ci-eval-tools` - Run on CI only, by the plugin-evals workflow.
- `prek install` - Run once per clone to install the ruff and basedpyright pre-commit hooks (`uv tool install prek` first).
- `cp scripts/git-hooks/commit-msg .git/hooks/commit-msg` - Run once to install the optional commit message check.

### Commits and Tags

- Sign every commit.
- Use Conventional Commits.
- Review the `bump_version.py` result before committing.
- Push after tagging only when I approve that exact push.
- Read `docs/releasing.md` before releasing.
- Work on short-lived branches named by commit scope, deleted on merge: `<plugin>/<topic>`, or `marketplace/`, `scripts/`, `ci/`, `docs/` plus `<topic>`.
- Release with `/release-plugin`; it stops at the open pull request, and `/github-ops:automatic-pr-lifecycle` handles reviews and the merge.

### Executable Scripts

- A script with a shebang is mode 755 on disk and in git; an imported module has no shebang and mode 644. See `.claude/rules/repo-scripts.md`.

## Non-negotiable rules

- **Plugins are for distribution.** Describe every capability from the point of view of the user who installs it. Never install, enable, symlink or pre-configure these plugins in my real Claude Code configuration. Never derive a plugin's requirements or compatibility from my machine, its PATH or its binaries.
- **Clean room.** Take Claude Code specifics only from the official docs (`https://code.claude.com/docs/llms.txt`), the changelog and runtime checks. Never copy or imitate another Claude Code or AI-assistant marketplace or plugin collection. Consult one only when I ask, only what I name, and only to observe. One exception: a plugin may derive from a project's own official AI content when I name it (ADR derived-third-party-content, `.claude/rules/plugins/derived-content.md`). My earlier marketplace projects are forbidden sources, listed in the untracked `CLAUDE.local.md`. Check pasted material for other platforms' content before using it.
- **Automate and source first.** Use a native tool or generator, then an official template, then an open standard; hand-write only what is ours. Record each choice in `docs/sourcing-log.md`.
- **Portability.** No absolute or home paths, user or machine names, personal data or secrets in plugins. Use `${CLAUDE_PLUGIN_ROOT}` and `${CLAUDE_PLUGIN_DATA}`; never `../`.
- **Leave nothing behind.** Every test, scaffold or experiment removes what it creates and verifies the removal. Use the prefixes in `TEMP_PREFIXES` (`scripts/check.py`) and `docs/testing.md#cleanup`.
- **No unagreed tooling.** Never introduce a tool or convention I did not agree to; ask first.
- **Gates.** Never skip, suppress or weaken a gate; fix the root cause.
- **Who changes this repository.** Only the maintainer and Claude develop and maintain it. No third party opens a pull request or modifies anything here; the repository allows pull requests from collaborators only. Third parties write issues, and we attend, resolve and update them. No pull request goes to a second collaborator: every pull request is ours, so it is reviewed and merged directly by us.
- **Signatures and approval.** Sign every commit and tag. No remote, push, pull request, merge or publication without my explicit approval for that exact action.

## Before schema, component, release or distribution work

- Run `/cc-currency`: it compares `claude --version` and the latest published version with 2.1.289, reads every newer changelog entry in full and updates the matching rules and pins with the date and version.
- Flag every conflict between the docs, the changelog and these files; follow the live source.

The rules in `.claude/rules/` hold facts verified on Claude Code 2.1.289 that are newer than your training or contradict it. Trust them over memory, and re-verify them when the installed version is newer.

## Where Knowledge Lives

### Path-Scoped Rules

- A rule loads only when you read or edit its paths.
- Read the rule before planning work in an area you have not touched.

#### Catalog and Plugins

- Catalog file: `.claude/rules/marketplace-file.md`
- Plugin authoring and manifest: `.claude/rules/plugins/authoring.md`, `.claude/rules/plugins/manifest.md`
- Hooks, permissions, mods, security: `.claude/rules/plugins/hooks-and-permissions.md`, `.claude/rules/plugins/mods.md`, `.claude/rules/plugins/security.md`
- LSP and MCP servers (every LSP server sets `"workspaceFolder": "${CLAUDE_PROJECT_DIR}"`, one extension per server, no compound keys): `.claude/rules/plugins/lsp-servers.md`
- Plugins derived from upstream AI content: `.claude/rules/plugins/derived-content.md`
- READMEs and distribution: `.claude/rules/plugins/readmes.md`, `.claude/rules/distribution.md`

#### Repository and Tooling

- Official CLI and schemas: `.claude/rules/claude-cli.md`, `.claude/rules/schemas.md`
- Repository scripts, gates, isolated installs: `.claude/rules/repo-scripts.md`, `.claude/rules/testing/gates.md`, `.claude/rules/testing/isolated-install.md`
- Plugin evals (design, scaffolds, flags, cost, evidence; never run without the maintainer's approval): `.claude/rules/testing/plugin-evals.md`
- CI, releases, tools and pinned Actions: `.claude/rules/ci-github.md`, `.claude/rules/releasing.md`, `.claude/rules/tooling-versions.md`
- ADRs and Claude Code features: `.claude/rules/adrs.md`, `.claude/rules/claude-code-features.md`
- Claude Code automation (settings, hooks, project skills, agent, workflows): `.claude/rules/automation.md`

### Guides to Read Before Acting

- Create or change a plugin: read `docs/authoring.md` and `docs/naming.md`.
- Accept or review a plugin: read `docs/quality-bar.md`.
- Touch hooks, MCP or LSP servers, `bin/`, monitors, or mods: read `docs/security-review.md`.
- Edit a README or README template: read `docs/readme-guide.md`.
- Bump, write changelog notes, tag, or release: read `docs/releasing.md`.
- Change gates, tests, or CI: read `docs/testing.md`.
- Add a file, tool, template, or dependency: read `docs/sourcing-log.md` and `THIRD_PARTY_NOTICES.md`.
- Change a rule or make a structural decision: read `docs/adr/README.md`.
  - Create a new ADR from `templates/adr/`.
- Answer issue authors: read `CONTRIBUTING.md`, `SECURITY.md`, `SUPPORT.md`, and `CODE_OF_CONDUCT.md`.

### Decisions

- Decisions live in dated ADRs in `docs/adr/decisions/`.
- Read the ADR before changing anything it covers.

## Architecture

```text
.claude-plugin/marketplace.json   catalog: name, owner, entries (source ./plugins/<name>); no version
plugins/<name>/                   one self-contained plugin per directory
scripts/                          stdlib Python run by path, shebang picks the interpreter (no manifest, no pins)
  check.py                        single entry point: every gate, test-install, clean, ci-tools, ci-eval-tools
  repo.py                         shared constants, naming, SemVer, changelog parsing
  check_repo.py                   repository gates
  sync_readmes.py                 generated README content
  new_plugin.py                   scaffold wrapping `claude plugin init` in a throwaway config
  bump_version.py                 version bump from the hand-written changelog (no commit, no tag)
  release_notes.py                release workflow: tag check and notes from the changelog
  check_pr.py                     release discipline for pull requests
  check_commit_msg.py             Conventional Commits checker (CI and optional hook)
  check_docs.py                   docs gate: Claude Code minimum, gate list, names, rule paths, links
  validate_adrs.py                ADR records: names, dates, status, sections, links
  test_install.py                 isolated install test (in place, cache copy, session)
  drive_plugin.py                 one plugin in a real headless session, reply checked
  add_component.py                skill or agent added to an existing plugin
  claude_hooks.py                 Claude Code hooks registered in .claude/settings.json
  git-hooks/commit-msg            optional local commit-msg hook
templates/                        ADR, changelog, README and license templates
tests/                            gate, hook and script tests with injected defects; fixtures/ holds the test-only plugin
docs/                             guides and ADRs
.github/                          workflows, labels, labeler, issue forms, PR template, CODEOWNERS
.claude/                          settings.json (permissions, hooks); skills/, agents/, workflows/; rules/
```

## Definition of done

- `scripts/check.py` passes, with raw output shown.
- For plugin changes, `scripts/check.py test-install` passes and my real configuration is unchanged.
- Negative cases fail for the intended reason (`tests/`).
- Changelog notes, labels and the sourcing log are updated where needed; generated READMEs are current.
- A changed decision gets a new dated ADR; the old one becomes `superseded`, or keeps `accepted` with a dated pointer note when the new one replaces only part of it (`.claude/rules/adrs.md`).
- A changed Claude Code fact is updated in its rule, with date and version.
- Commits are signed and follow Conventional Commits; nothing is pushed without my approval.
- Limitations, skipped checks and risks are reported, and **Current state** is updated.

## Current state

- Published on 2026-10-04: every gate that existed at publication passed locally and in CI, `main` is protected by rulesets (signed commits, linear history, squash-only merges), labels are synced, and the marketplace installs like a user's install.
- The full release flow ran end to end on pull request #2: `check_pr`, labeler, squash merge, signed tag `hello-example--v0.1.1` and its GitHub Release.
- Open item: confirm in the browser that `/issues/new/choose` lists the two issue forms and the three contact links (the API reported the contact links; the forms are only visible signed in).
- Claude Code automation added on 2026-10-04: see `.claude/rules/automation.md`.
- The Claude GitHub workflows arrived with the squash merge of PR #4 (`7314c58`). The automation commits `44fc258` to `60f7a5a` were already on `origin/main` before it; how they were pushed is not recorded here. They came after the handoff `2026-10-04-0852`.
- The `docs` gate and the `.claude` validation in `validate` came with those commits; CI passed them on PR #4 (`Gates and isolated install test`, run 37197025456), and `scripts/check.py` passed all 10 gates locally on 2026-10-04.
- `51e96f6` (2026-10-04) gave the bug report dropdowns a neutral first option; CI passed on `main`, and the forms still need the browser check.
- Branch naming settled on 2026-10-04 in ADR branch-naming: the prefix is the commit scope, and `marketplace`, `scripts`, `ci` and `docs` are reserved plugin names. CI passed on its commit `7c49526` (`Validate`, run 37201134748, checked with `gh run list` on 2026-10-04).
- The gate tests run on a fixture plugin outside the catalog (`tests/fixtures/plugins/sample-plugin/`), so removing `hello-example` cannot break them (PR #6, 2026-10-04).
- The automatic Claude review ran on PR #6 and posted nothing: the action loads the repository's `.claude/settings.json`, whose `permissions.ask` list denied `gh pr comment`. PR #7 (`f5884f8`) passes `--setting-sources user`; the first pull request after it shows whether the review now posts (details in `.claude/rules/ci-github.md`).
- The only GitHub collaborator is the maintainer, and Claude works through that account, so required reviews on `main` stay off (`.claude/rules/ci-github.md`).
- `svelte-development` 0.1.0 merged in PR #14 (`0ce9ebb`, 2026-10-05) with the removal of `hello-example` (ADR remove-example-plugin-without-deprecation), `.prettierignore` for `**/skills/**` and the CLAUDE files (ADR skills-excluded-from-prettier) and the rules `plugins/derived-content.md` and `plugins/lsp-servers.md`; tag `svelte-development--v0.1.0` and its GitHub Release are published. Its first eval run (draft PR #16, closed unmerged, run 37395261454) scored 13/13 cases with a mean delta of +0.087; the skills never triggered on their own and the LSP and tool-choice cases had delta 0.
- `svelte-development` uses the Svelte team's remote MCP server (maintainer decision: it reconnects on its own, unlike a stdio server) and `svelteserver` for `.svelte` only; TypeScript code intelligence will be its own plugin. Evidence for every reference is in the research directory `2026-10-05-svelte-development` of the live-docs-research plugin data.
- Eval runs inherit their models and keep the full result as the `evals-results` artifact (ADR inherited-eval-models-and-full-results, pushed to `main` as `d4a751f` on 2026-10-06, Validate passed). Branch `svelte-development/skill-contracts` (2026-10-06, not yet pushed) prepares 0.2.0: skills rebuilt as contracts with explicit tool calls, a language-server-first route, renames proven by the project check, SvelteKit 2 and Svelte 4 version gating, a PostToolUse reminder hook, four new eval cases and README and catalog updates. Deferred by the maintainer: a background auditor, a `svelte-audit` skill with `context: fork`, and `disallowed-tools` or a WebFetch guard.
- Awaiting my decision:
  - refining the user-level Python rule;
  - a rule that plugins declare every external tool they use and rely on no version-specific features;
  - a `CLAUDE_CODE_OAUTH_TOKEN` so `drive_plugin.py` can run fully isolated (until then, `claude plugin eval` is the clean-room check).
- The uv cache was cleared with `uv cache clean` and `uv cache prune` on 2026-10-05, which settles the cache entries removed by hand on 2026-10-03.
- Unpinned tooling (ADR unpinned-tooling-and-shebang-interpreters, 2026-10-05), merged in PR #12 (`02ab6d9`): no tool or Python version is pinned, scripts run by path, prek runs local hooks with the installed tools, CI installs the latest releases, and the `repo` gate checks plugin scripts (unversioned `#!/usr/bin/env` shebang, mode 755, run by path). The repository has no `ruff.toml`: ruff uses `~/.config/ruff/ruff.toml`, and CI writes it from the `RUFF_CONFIG` Actions variable (set with `gh variable set` on 2026-10-05; ADR ruff-config-from-actions-variable).
- Release watcher: the session-start notice and `/cc-currency`; scheduled routines were rejected because they run without permission prompts.
- Deferred: Dependabot, external link checking, git-cliff or release-please.
- The `@claude` workflow (`claude.yml`) was removed on 2026-10-05 (ADR remove-claude-mention-workflow); only `claude-code-review` runs Claude on GitHub. Reinstalling the app with `/install-github-app` opened PR #13 with generic, unpinned workflows; it was closed unmerged, and the new `CLAUDE_CODE_OAUTH_TOKEN` it set is the only change kept. PR #15 added it again with `/install-github-app`; it was reverted on `main` (`7957a64`).
