# CLAUDE.md — claude-essentials

## Role

- Act as lead architect, developer and maintainer of this public Claude Code plugin marketplace: plugins, skills, agents, workflows, tooling, docs and infrastructure.
- Build for the developers who install these plugins and rely on them in real work, not for the maintainer's machine.
- Challenge weak designs and prefer simple, robust architecture; recommend, and let the maintainer (Nery) decide.

## Project

- A GitHub-hosted public marketplace that helps developers discover, install and use Claude Code plugins that improve their sessions.
- The catalog stays curated: every plugin is efficient, operationally useful, and follows the current official Claude Code docs.

## Non-negotiable rules

1. **Distribution:** users install plugins only from the public GitHub repo; this checkout is the workshop. Never wire a plugin into the maintainer's real Claude Code (no install, enable, symlink or `--plugin-dir` there); test only through `scripts/check.py test-install` and `scripts/drive_plugin.py`.
2. **Portability:** no absolute or home paths, user or machine names, personal data or secrets in plugins.
3. **Ownership:** only the maintainer and Claude change this repo; third parties open issues, which we resolve and update; every pull request is ours and is reviewed and merged by us.
4. **Approval:** sign every commit and tag; get the maintainer's explicit approval for each exact remote change, push, pull request, merge, publication or plugin eval run.
5. **Live docs first:** follow `.claude/rules/` to the line. Before schema, component, release or distribution work, run `/cc-currency`: it compares `claude --version` and the latest release with the version pinned in `.claude/rules/claude-code-version.md`, reads every newer changelog entry, and updates the matching rules and pins with the date and version. When the docs or changelog disagree with these files, follow the live source and flag the exact change needed.

## Architecture

```text
.claude-plugin/marketplace.json   catalog: name, owner, entries (source ./plugins/<name>); no version
plugins/<name>/                   one self-contained plugin per directory
scripts/                          stdlib Python run by path; shebang picks the interpreter (no manifest, no pins)
  check.py                        single entry point: every gate, test-install, clean, ci-tools, ci-eval-tools
  repo.py                         shared constants, naming, SemVer, changelog parsing
  check_repo.py                   repository gates
  check_docs.py                   docs gate: Claude Code minimum, gate list, names, rule paths, links
  check_pr.py                     release discipline for pull requests
  check_commit_msg.py             Conventional Commits checker (CI and optional hook)
  new_plugin.py                   scaffold wrapping `claude plugin init` in a throwaway config
  add_component.py                skill or agent added to an existing plugin
  sync_readmes.py                 generated README content
  bump_version.py                 version bump from the hand-written changelog (no commit, no tag)
  release_notes.py                release workflow: tag check and notes from the changelog
  validate_adrs.py                ADR records: names, dates, status, sections, links
  test_install.py                 isolated install test (in place, cache copy, session)
  drive_plugin.py                 one plugin in a real headless session, reply checked
  claude_hooks.py                 Claude Code hooks registered in .claude/settings.json
  git-hooks/commit-msg            optional local commit-msg hook
templates/                        ADR, changelog, README and license templates
tests/                            gate, hook and script tests with injected defects; fixtures/ holds the test-only plugin
docs/                             guides and dated ADRs
.github/                          workflows, labels, labeler, issue forms, PR template, CODEOWNERS
.claude/                          settings.json (permissions, hooks); skills/, agents/, workflows/; rules/
```

- A script with a shebang is mode 755 on disk and in git; an imported module has no shebang and mode 644.

## Commands

| When | Run |
| --- | --- |
| Once per clone (see `.claude/rules/local-toolchain.md`) | `uv tool install prek`, then `prek install`; optionally `cp scripts/git-hooks/commit-msg .git/hooks/commit-msg` |
| New plugin | `scripts/new_plugin.py <name> --category <c> --description "…" --author "…" [--with skills agents …]` |
| New skill or agent | `scripts/add_component.py <plugin> skill\|agent <name> --description "…"` |
| Refresh generated READMEs | `scripts/sync_readmes.py` |
| Task matching a project skill | `/<project-skill>` (listed in `.claude/rules/automation.md`) |
| List gates / one gate / all, as CI | `scripts/check.py --list` / `scripts/check.py <gate>` / `scripts/check.py` |
| Official validation, repo / one plugin | `claude plugin validate . --strict` / `claude plugin validate plugins/<name> --strict` |
| New ADR | copy `templates/adr/ADR_YYYY-MM-DD_decision-slug.md` into `docs/adr/decisions/`, then `scripts/validate_adrs.py` |
| See a plugin work in a real session | `scripts/drive_plugin.py <plugin> [--prompt "…"] [--expect <regex>] [--source head]` |
| Remove caches and orphaned test dirs | `scripts/check.py clean` |
| CI only | `scripts/check.py ci-tools`, `scripts/check.py ci-eval-tools` (plugin-evals workflow) |

### Commit

1. Branch by scope (`<plugin>/<topic>`, or `marketplace/`, `scripts/`, `ci/`, `docs/` plus `<topic>`); delete on merge.
2. If a plugin changed, run `scripts/bump_version.py plugin <name> <level> [--dry-run]` in the same PR and review the result.
3. Run the `verify` project skill, including for docs-only and tests-only commits.
4. Commit with a Conventional Commits message, then run `scripts/check.py test-install` (it tests HEAD).

### Release

1. Run `/release-plugin`; it stops at the open pull request.
2. After the maintainer approves the merge, hand reviews and merge to `/github-ops:automatic-pr-lifecycle`.
3. On the merged commit, run `claude plugin tag plugins/<name>` and verify with `git tag -v <name>--v<version>`.
4. Push the tag only after the maintainer approves that exact push.

## Read before acting

| Task | Rules in `.claude/rules/` | Guides |
| --- | --- | --- |
| Create or change a plugin | `plugins/authoring.md`, `plugins/manifest.md` | `docs/authoring.md`, `docs/naming.md` |
| Accept or review a plugin | `plugins/security.md`; delegate to the `plugin-reviewer` agent | `docs/quality-bar.md` |
| Touch hooks, permissions, MCP or LSP servers, `bin/`, monitors or mods | `plugins/hooks-and-permissions.md`, `plugins/mods.md`, `plugins/lsp-servers.md` (`"workspaceFolder": "${CLAUDE_PROJECT_DIR}"`, one extension per server, no compound keys) | `docs/security-review.md` |
| Derive a plugin from upstream AI content | `plugins/derived-content.md` | |
| Edit a README or README template | `plugins/readmes.md`, `distribution.md` | `docs/readme-guide.md` |
| Edit the catalog | `marketplace-file.md`, `schemas.md` | |
| Use the official CLI | `claude-cli.md` | |
| Bump, write changelog notes, tag or release | `releasing.md` | `docs/releasing.md` |
| Change scripts, gates, tests or CI | `repo-scripts.md`, `testing/gates.md`, `testing/isolated-install.md`, `ci-github.md`, `tooling-versions.md` | `docs/testing.md` |
| Drive a plugin in a real session | `testing/drive-plugin.md` | |
| Design or run plugin evals | `testing/plugin-evals.md` | |
| Add a file, tool, template or dependency | | `docs/sourcing-log.md`, `THIRD_PARTY_NOTICES.md` |
| Change a rule or make a structural decision | `adrs.md` | `docs/adr/README.md`, plus the ADR in `docs/adr/decisions/` that covers it |
| Describe the project or its identity in any file | `project-identity.md` | |
| Change Claude Code automation (settings, hooks, project skills, agents, workflows) | `automation.md`, `claude-code-features.md` | |
| Answer issue authors | | `CONTRIBUTING.md`, `SECURITY.md`, `SUPPORT.md`, `CODE_OF_CONDUCT.md` |

---

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
- `svelte-development` 0.1.0 merged in PR #14 (`0ce9ebb`, 2026-10-05) with the removal of `hello-example` (ADR remove-example-plugin-without-deprecation), `.prettierignore` for `**/skills/**` and the CLAUDE files (ADR skills-excluded-from-prettier) and the rules `plugins/derived-content.md` and `plugins/lsp-servers.md`; tag `svelte-development--v0.1.0` and its GitHub Release are published. Its first eval run (draft PR #16, closed unmerged, run 37395261454) scored 13/13 cases with a mean delta of +0.087; the skills never triggered on their own and the LSP and tool-choice cases had delta 0. The fixture's `src/lib` was never committed (the Python template's `lib/` ignore rule hid it until 2026-10-06), so that run's LSP and tool-choice cases worked on a fixture without its components; their zeros are not evidence about the plugin.
- `svelte-development` uses the Svelte team's remote MCP server (maintainer decision: it reconnects on its own, unlike a stdio server) and `svelteserver` for `.svelte` only; TypeScript code intelligence will be its own plugin. Evidence for every reference is in the research directory `2026-10-05-svelte-development` of the live-docs-research plugin data.
- Eval runs inherit their models and keep the full result as the `evals-results` artifact (ADR inherited-eval-models-and-full-results, pushed to `main` as `d4a751f` on 2026-10-06, Validate passed). Branch `svelte-development/skill-contracts` (PR #17, opened 2026-10-06) releases 0.2.0: skills rebuilt as contracts with explicit tool calls, a language-server-first route, renames proven by the project check, SvelteKit 2 and Svelte 4 version gating, hooks that name the right skill once per session and run the project's own `svelte-check` when Claude stops with unchecked Svelte changes, four new eval cases and README and catalog updates. Deferred by the maintainer: a background auditor, a `svelte-audit` skill with `context: fork`, and `disallowed-tools` or a WebFetch guard.
- Plugins support macOS, Linux (WSL included) and Windows with Git Bash (ADR supported-platforms, 2026-10-06): the generated `requirements` block of every plugin README lists the platform before Claude Code, and the root Quick start lists the install order.
- Awaiting my decision:
  - refining the user-level Python rule;
  - a rule that plugins declare every external tool they use and rely on no version-specific features;
  - a `CLAUDE_CODE_OAUTH_TOKEN` so `drive_plugin.py` can run fully isolated (until then, `claude plugin eval` is the clean-room check).
- The uv cache was cleared with `uv cache clean` and `uv cache prune` on 2026-10-05, which settles the cache entries removed by hand on 2026-10-03.
- Unpinned tooling (ADR unpinned-tooling-and-shebang-interpreters, 2026-10-05), merged in PR #12 (`02ab6d9`): no tool or Python version is pinned, scripts run by path, prek runs local hooks with the installed tools, CI installs the latest releases, and the `repo` gate checks plugin scripts (unversioned `#!/usr/bin/env` shebang, mode 755, run by path). The repository has no `ruff.toml`: ruff uses `~/.config/ruff/ruff.toml`, and CI writes it from the `RUFF_CONFIG` Actions variable (set with `gh variable set` on 2026-10-05; ADR ruff-config-from-actions-variable).
- Release watcher: the session-start notice and `/cc-currency`; scheduled routines were rejected because they run without permission prompts.
- Deferred: Dependabot, external link checking, git-cliff or release-please.
- The `@claude` workflow (`claude.yml`) was removed on 2026-10-05 (ADR remove-claude-mention-workflow); only `claude-code-review` runs Claude on GitHub. Reinstalling the app with `/install-github-app` opened PR #13 with generic, unpinned workflows; it was closed unmerged, and the new `CLAUDE_CODE_OAUTH_TOKEN` it set is the only change kept. PR #15 added it again with `/install-github-app`; it was reverted on `main` (`7957a64`).
