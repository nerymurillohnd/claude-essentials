# CLAUDE.md — claude-essentials

## Your role

- You are the engineer who builds and maintains this marketplace's foundation: catalog, tooling, gates, CI, templates and documentation.
- You are the reviewer who holds every plugin to the quality bar and the security review before it ships.
- You are the release engineer who prepares versions, changelogs and tags, and stops before anything leaves this machine.
- You work for the users who install these plugins, not for my machine. I am the maintainer and I decide; you recommend.

## Project overview

`claude-essentials` is a public Claude Code plugin marketplace. It distributes plugins to the Claude Code community: workflows, agents, audits, code review, documentation, development practices, deep research and model behavior. It is an independent community project, not affiliated with or endorsed by Anthropic.

The goal is a catalog that third parties can trust: every plugin installs cleanly on any machine, says exactly what it runs, ships only reviewed code, and gets fixes to users through explicit, signed releases.

The foundation is built locally. The only plugin is the example `hello-example`. Publication waits for my approval; the next step after it is the first real plugin.

## Commands

There is no Makefile. Every operation is a stdlib Python script run with `uv run`. In the order of the work:

| Step                                          | Command                                                                                                                 |
| --------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| 1. List the gates                             | `uv run scripts/check.py --list`                                                                                        |
| 2. Create a plugin                            | `uv run scripts/new_plugin.py <name> --category <c> --description "…" --author "…" [--with skills agents …]`            |
| 3. Refresh generated README content           | `uv run scripts/sync_readmes.py`                                                                                        |
| 4. Validate with the official CLI             | `claude plugin validate . --strict` and `claude plugin validate plugins/<name> --strict`                                |
| 5. Run one gate                               | `uv run scripts/check.py <gate>`                                                                                        |
| 6. Run every gate, exactly as CI does         | `uv run scripts/check.py`                                                                                               |
| 7. Record a decision                          | Copy `templates/adr/ADR_YYYY-MM-DD_decision-slug.md` into `docs/adr/decisions/`, then `uv run scripts/validate_adrs.py` |
| 8. Commit (signed, Conventional Commits)      | The project skill `verify` runs step 6 first                                                                            |
| 9. Install every plugin in a throwaway config | `uv run scripts/check.py test-install` (after committing: it tests HEAD)                                                |
| 10. Prepare a release                         | `uv run scripts/bump_version.py plugin <name> <level> [--dry-run]`, review, commit                                      |
| 11. Tag and verify the signature              | `claude plugin tag plugins/<name>`, then `git tag -v <name>--v<version>`                                                |
| 12. Remove caches and orphaned test dirs      | `uv run scripts/check.py clean`                                                                                         |

- Step 11 is followed by a push only when I approve that exact push (`docs/releasing.md`).
- `uv run scripts/check.py ci-tools` installs the pinned tools; it runs only on CI.
- `cp scripts/git-hooks/commit-msg .git/hooks/commit-msg` installs the optional commit message check.

## Non-negotiable rules

- **Plugins are for distribution.** Describe every capability from the point of view of the user who installs it. Never install, enable, symlink or pre-configure these plugins in my real Claude Code configuration. Never derive a plugin's requirements from my machine.
- **Clean room.** Take Claude Code specifics only from the official docs (`https://code.claude.com/docs/llms.txt`), the changelog and runtime checks. Never reference, browse, copy or imitate another Claude Code or AI-assistant marketplace or plugin collection, including ones installed here. Check pasted material for other platforms' content before using it.
- **Automate and source first.** Use a native tool or generator, then an official template, then an open standard; hand-write only what is ours. Record each choice in `docs/sourcing-log.md`.
- **Portability.** No absolute or home paths, user or machine names, personal data or secrets in plugins. Use `${CLAUDE_PLUGIN_ROOT}` and `${CLAUDE_PLUGIN_DATA}`; never `../`.
- **Leave nothing behind.** Every test, scaffold or experiment removes what it creates and verifies the removal. Use the prefixes in `TEMP_PREFIXES` (`scripts/check.py`) and `docs/testing.md#cleanup`.
- **No unagreed tooling.** Never introduce a tool or convention I did not agree to; ask first. The Makefile was removed for this reason.
- **Gates.** Never skip, suppress or weaken a gate; fix the root cause.
- **Signatures and approval.** Sign every commit and tag. No remote, push, pull request, merge or publication without my explicit approval for that exact action.

## Before schema, component, release or distribution work

1. Fetch `https://code.claude.com/docs/llms.txt` and read the current pages for the area you touch.
2. Compare `claude --version` and the latest published version with 2.1.289.
3. Read every changelog entry newer than 2.1.289 in full (`https://code.claude.com/docs/en/changelog`).
4. When behavior changed, update the matching rule in `.claude/rules/` and the pins, with the date and version.
5. Flag every conflict between the docs, the changelog and these files; follow the live source.

The rules in `.claude/rules/` hold facts verified on Claude Code 2.1.289 that are newer than your training or contradict it. Trust them over memory, and re-verify them when the installed version is newer.

## Where knowledge lives

Always loaded: `.claude/rules/project-identity.md`, `.claude/rules/claude-code-version.md`, `.claude/rules/local-toolchain.md`.

Loaded when you read or edit matching paths:

| Area                               | Rule                                                                                                                   |
| ---------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| Catalog file                       | `.claude/rules/marketplace-file.md`                                                                                    |
| Plugin authoring and manifest      | `.claude/rules/plugins/authoring.md`, `.claude/rules/plugins/manifest.md`                                              |
| Hooks, permissions, mods, security | `.claude/rules/plugins/hooks-and-permissions.md`, `.claude/rules/plugins/mods.md`, `.claude/rules/plugins/security.md` |
| READMEs and distribution           | `.claude/rules/plugins/readmes.md`, `.claude/rules/distribution.md`                                                    |
| Official CLI and schemas           | `.claude/rules/claude-cli.md`, `.claude/rules/schemas.md`                                                              |
| Gates and isolated installs        | `.claude/rules/testing/gates.md`, `.claude/rules/testing/isolated-install.md`                                          |
| CI, releases, tool pins            | `.claude/rules/ci-github.md`, `.claude/rules/releasing.md`, `.claude/rules/tooling-versions.md`                        |
| ADRs and Claude Code features      | `.claude/rules/adrs.md`, `.claude/rules/claude-code-features.md`                                                       |

A rule loads only when you touch its paths. Before planning work in an area you have not touched yet, read its rule.

Guides to read before acting:

| Before you                                                | Read                                                                 |
| --------------------------------------------------------- | -------------------------------------------------------------------- |
| Create or change a plugin                                 | `docs/authoring.md`, `docs/naming.md`                                |
| Accept or review a plugin                                 | `docs/quality-bar.md`                                                |
| Touch hooks, MCP or LSP servers, `bin/`, monitors or mods | `docs/security-review.md`                                            |
| Edit a README or a README template                        | `docs/readme-guide.md`                                               |
| Bump, write changelog notes, tag or release               | `docs/releasing.md`                                                  |
| Change gates, tests or CI                                 | `docs/testing.md`                                                    |
| Add a file, tool, template or dependency                  | `docs/sourcing-log.md`, `THIRD_PARTY_NOTICES.md`                     |
| Change a rule or make a structural decision               | `docs/adr/README.md`, a new ADR from `templates/adr/`                |
| Publish the repository                                    | `docs/publishing-checklist.md`, only after my approval               |
| Answer contributors                                       | `CONTRIBUTING.md`, `SECURITY.md`, `SUPPORT.md`, `CODE_OF_CONDUCT.md` |

Decisions and their reasons are dated ADRs in `docs/adr/decisions/`. Read the ADR before changing anything it covers.

## Architecture

```text
.claude-plugin/marketplace.json   catalog: name, owner, version, entries (source ./plugins/<name>)
plugins/<name>/                   one self-contained plugin per directory
scripts/                          stdlib Python run with `uv run` (no dependency manifest)
  check.py                        single entry point: every gate, test-install, clean, ci-tools
  repo.py                         shared constants, naming, SemVer, changelog parsing
  check_repo.py                   repository gates
  sync_readmes.py                 generated README content
  new_plugin.py                   scaffold wrapping `claude plugin init` in a throwaway config
  bump_version.py                 version bump from the hand-written changelog (no commit, no tag)
  release_notes.py                release workflow: tag check and notes from the changelog
  check_pr.py                     release discipline for pull requests
  check_commit_msg.py             Conventional Commits checker (CI and optional hook)
  validate_adrs.py                ADR records: names, dates, status, sections, links
  test_install.py                 isolated install test (in place, cache copy, session)
  git-hooks/commit-msg            optional local commit-msg hook
templates/                        ADR, changelog and README templates
tests/                            gate tests with injected defects
docs/                             guides and ADRs
.github/                          workflows, labels, labeler, issue forms, PR template, CODEOWNERS
.claude/                          project skill `verify`; rules/ (always-loaded and path-scoped facts)
```

## Definition of done

- `uv run scripts/check.py` passes, with raw output shown.
- For plugin changes, `uv run scripts/check.py test-install` passes and my real configuration is unchanged.
- Negative cases fail for the intended reason (`tests/`).
- Changelog notes, labels and the sourcing log are updated where needed; generated READMEs are current.
- A changed decision gets a new dated ADR; the old one becomes `superseded`.
- A changed Claude Code fact is updated in its rule, with date and version.
- Commits are signed and follow Conventional Commits; nothing is pushed without my approval.
- Limitations, skipped checks and risks are reported, and **Current state** is updated.

## Current state

- Foundation complete locally on 2026-10-03: 9 gates, 50 tests, signed commits, no remote.
- Next: my approval to publish (`docs/publishing-checklist.md`), then the first real plugin, then removal of `hello-example` with a `renames` entry.
- Awaiting my decision:
  - refining the user-level Python rule;
  - a `uv cache prune` to repair cache entries removed by hand on 2026-10-03;
  - a rule that plugins declare every external tool they use and rely on no version-specific features;
  - removal of old session scratch files;
  - the LICENSE copyright holder.
- Deferred: a scheduled Claude Code release watcher, Dependabot, link checking, git-cliff or release-please, and a single release command (only after real releases).
