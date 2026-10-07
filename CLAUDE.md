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
5. **Live docs first:** follow `.claude/rules/` to the line. Before schema, component, release or distribution work, run `/cc-currency`: it compares `claude --version` and the latest release with the last reviewed release recorded in `.claude/rules/claude-code-version.md`, reads every newer changelog entry, and updates the matching rules with the date and version. The repository pins no Claude Code version. When the docs or changelog disagree with these files, follow the live source and flag the exact change needed.

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

- Open debt lives in `docs/maintenance/pending-debt.md` and closed debt in `docs/maintenance/resolved-debt.md`: read them before planning work, and record new debt there, not here.
- The catalog holds `svelte-development` 0.2.0, merged in PR #17 (`dd7227d`, 2026-10-06) and released as `svelte-development--v0.2.0` on 2026-10-07.
- Every plugin release keeps both its signed tag and its GitHub Release (maintainer decision, 2026-10-07).
- `svelte-development` maps only `.svelte` to `svelteserver`: `.ts` mapped to it returned empty results (2026-10-05), so TypeScript code intelligence will be its own plugin. The remote MCP server choice is recorded in `docs/sourcing-log.md`.
- Deferred by the maintainer for `svelte-development`: a background auditor, a `svelte-audit` skill with `context: fork`, and `disallowed-tools` or a WebFetch guard.
- Awaiting my decision outside the ledger: refining the user-level Python rule, which lives outside this repository. Ledger items that need my decision: DEBT-010, DEBT-011, DEBT-017 and DEBT-018.
