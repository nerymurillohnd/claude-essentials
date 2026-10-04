# CLAUDE.md — claude-essentials

Project memory for Claude Code sessions in this repository. Read it first. The **Verified facts** come from the official Claude Code docs, the changelog and runtime checks on Claude Code **2.1.289** (2026-10-03); re-verify any fact before relying on it when the installed version is newer.

## Purpose

`claude-essentials` is a public Claude Code plugin marketplace that distributes plugins to the Claude Code community: workflows, agents, audits, code review, documentation, development practices, deep research and model behavior. It is an independent community project, **not affiliated with or endorsed by Anthropic**.

## Non-negotiable rules

- **Built for third parties.** Every capability is described and evaluated from the point of view of **the user who installs the plugin**. The maintainer is not a special user: to use a plugin locally they add the published marketplace and install it like anyone else. Never install, enable, symlink or pre-configure these plugins in the maintainer's real Claude Code configuration; tests use throwaway configurations only.
- **Clean room.** Claude Code specifics (schemas, structure, components, validation, distribution) come only from the official docs (`https://code.claude.com/docs/llms.txt`) and changelog, plus runtime checks. Never reference, browse, copy or imitate any other Claude Code or AI-assistant marketplace or plugin collection, including ones installed on this machine. Check pasted material for content from other platforms before using it. ([ADR clean-room-policy](docs/adr/decisions/ADR_2026-10-03_clean-room-policy.md))
- **Automate and source first.** Use a native tool or generator, then an official template, then an open standard; hand-write only what is ours, and record the decision in `docs/sourcing-log.md`. ([ADR sourcing-policy](docs/adr/decisions/ADR_2026-10-03_sourcing-policy.md))
- **Portability.** No absolute or home paths, user or machine names, personal data or secrets in plugins; `${CLAUDE_PLUGIN_ROOT}` and `${CLAUDE_PLUGIN_DATA}` only; no `../`.
- **Leave nothing behind.** Every test, scaffold or experiment removes what it creates (directories, configurations, clones, caches, processes) and verifies the removal; no orphaned or ghost directories, here or in the system temporary directory. Use the prefixes in `TEMP_PREFIXES` (`scripts/check.py`) and `uv run scripts/check.py clean`. See [docs/testing.md#cleanup](docs/testing.md#cleanup).
- **Entry point.** `uv run scripts/check.py` runs every gate, exactly as CI does. There is no Makefile: the maintainer agreed on stdlib Python scripts run with uv, and never approved make. Do not introduce tools or conventions the maintainer did not agree to; ask first.
- **Quality gates.** Never skip, suppress or weaken a gate to get green; fix the root cause. Every commit and tag is signed. No remote, push, pull request, merge or publication without the maintainer's explicit approval for that exact action.

## Mandatory routine before schema, component, release or distribution work

1. Fetch `https://code.claude.com/docs/llms.txt` and read the current pages for the area you touch.
2. Compare `claude --version` and the latest published version with **2.1.289**, the version these facts were verified on. Read every changelog entry newer than 2.1.289 in full (`https://code.claude.com/docs/en/changelog`).
3. Update **Verified facts** and the pins (`repo.MIN_CLAUDE_CODE`, used by `scripts/check.py` and new plugins, and `CLAUDE_CODE_VERSION` in `.github/workflows/release.yml`) when behavior changed, with the date and version. Flag every conflict between docs, changelog and this file; follow the live source.

## Document map: read before acting

| Before you                                                | Read                                                                                                                                                                                             |
| --------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Create or change a plugin                                 | [docs/authoring.md](docs/authoring.md), [docs/naming.md](docs/naming.md) (auto-loaded summary: `.claude/rules/plugins/`)                                                                         |
| Accept or review a plugin                                 | [docs/quality-bar.md](docs/quality-bar.md)                                                                                                                                                       |
| Touch hooks, MCP or LSP servers, `bin/`, monitors or mods | [docs/security-review.md](docs/security-review.md), [ADR security-posture](docs/adr/decisions/ADR_2026-10-03_security-posture.md)                                                                |
| Edit a README or a README template                        | [docs/readme-guide.md](docs/readme-guide.md)                                                                                                                                                     |
| Bump a version, write changelog notes, tag or release     | [docs/releasing.md](docs/releasing.md)                                                                                                                                                           |
| Change gates, tests or CI                                 | [docs/testing.md](docs/testing.md), [ADR validation-stack](docs/adr/decisions/ADR_2026-10-03_validation-stack.md), [ADR testing-approach](docs/adr/decisions/ADR_2026-10-03_testing-approach.md) |
| Add a file, tool, template or dependency                  | [docs/sourcing-log.md](docs/sourcing-log.md), [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)                                                                                                   |
| Change a rule or make a structural decision               | [docs/adr/README.md](docs/adr/README.md) and a new ADR from [templates/adr/ADR_YYYY-MM-DD_decision-slug.md](templates/adr/ADR_YYYY-MM-DD_decision-slug.md)                                       |
| Publish the repository                                    | [docs/publishing-checklist.md](docs/publishing-checklist.md), only after explicit approval                                                                                                       |
| Answer contributors                                       | [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md), [SUPPORT.md](SUPPORT.md), [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)                                                               |

## Architecture

```text
.claude-plugin/marketplace.json   catalog: name, owner, version, entries (source ./plugins/<name>)
plugins/<name>/                   one self-contained plugin per directory
scripts/                          stdlib Python run with `uv run` (no dependency manifest)
  check.py                        single entry point: every gate, test-install, clean, ci-tools
  repo.py                         shared constants, naming, SemVer, changelog parsing
  check_repo.py                   repository gates
  sync_readmes.py                 generated README content (--check in scripts/check.py)
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
.claude/                          project skill `verify`; rules/ (always-loaded facts, path-scoped rules per area)
```

## Commands

| Task                                                   | Command                                                                                                                 |
| ------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------- |
| Every gate (same as CI)                                | `uv run scripts/check.py`                                                                                               |
| Install every plugin in a throwaway config             | `uv run scripts/check.py test-install` (commit first: the cache-copy scenario tests HEAD)                               |
| New plugin                                             | `uv run scripts/new_plugin.py <name> --category <c> --description "…" --author "…" [--with skills agents …]`            |
| Refresh generated README content                       | `uv run scripts/sync_readmes.py`                                                                                        |
| Prepare a version bump                                 | `uv run scripts/bump_version.py plugin <name> <level> [--dry-run]`, then commit and tag by hand (docs/releasing.md)     |
| Official validation                                    | `claude plugin validate . --strict` and `claude plugin validate plugins/<name> --strict`                                |
| One gate, or list the gates                            | `uv run scripts/check.py <gate>` / `uv run scripts/check.py --list`                                                     |
| Record a decision                                      | Copy `templates/adr/ADR_YYYY-MM-DD_decision-slug.md` into `docs/adr/decisions/`, then `uv run scripts/validate_adrs.py` |
| Remove repository caches and orphaned test directories | `uv run scripts/check.py clean`                                                                                         |

## Definition of done

- `uv run scripts/check.py` passes with raw output shown; `uv run scripts/check.py test-install` passes for plugin changes, with the real configuration unchanged.
- Negative cases fail for the intended reason (gate tests in `tests/`).
- Changelog notes, labels and the sourcing log are updated where the change requires them; generated READMEs are current.
- A changed decision gets a **new** dated ADR that links the old one, and the old one is marked `superseded`; accepted ADRs are never rewritten (docs/adr/README.md).
- Commits are signed and follow Conventional Commits; nothing is pushed or published without explicit approval.
- Remaining limitations, skipped checks and risks are reported explicitly, and **Current state** below is updated.

## Decisions

Recorded as dated ADRs in [docs/adr/decisions/](docs/adr/decisions/) (`ADR_YYYY-MM-DD_<slug>.md`, procedure in [docs/adr/README.md](docs/adr/README.md)). Summary: owner `nerymurillohnd`, MIT, in-repo plugins only, SemVer in `plugin.json` only with official `<name>--v<version>` tags, editorial changelogs with a stdlib bump script (no commit or tag), manual signed commits and `claude plugin tag`, CI publication, no single release command until real releases justify one, `uvx git-cliff@2.14.2` only for occasional reviewed drafts, zero repository dependencies, strict review for code that runs on users' machines (mods only when nothing else can do the job), isolated install tests, labels as code, generated README content, Claude Code 2.1.289 pinned, hand-written Claude Code JSON Schemas not adopted.

## Verified facts (not from training knowledge)

Verified against Claude Code **2.1.289** docs and changelog window 2.1.284–2.1.289, plus runtime checks in an isolated config.

### Marketplace file

- Location: `.claude-plugin/marketplace.json` at the marketplace root. Relative plugin sources resolve from the root (the directory containing `.claude-plugin/`), must start with `./`, and may not contain `..`.
- Required: `name`, `owner.name`, `plugins[]`. Optional and useful: `description` (validate warns if missing), `version` / `metadata.version`, `metadata.pluginRoot` (bare names, ≥ 2.1.239), `renames` (append-only map old→new or `null`, ≥ 2.1.193), `forceRemoveDeletedPlugins`.
- Plugin entry: `name` + `source` required; also accepts `category` and `tags` natively (free-form), `displayName`, `description`, `defaultEnabled`, `strict` (default `true`), `metadata` (free-form, ignored by Claude Code).
- There is **no marketplace-level `displayName`**: runtime-verified 2026-10-03, a top-level or `metadata.displayName` is reported as `Unknown field` and fails `--strict`. `displayName` exists only on plugin entries and in `plugin.json`. Users see the marketplace by its `name`.
- Unknown keys are ignored at load time but reported as warnings by `claude plugin validate` (so `--strict` fails them).
- Reserved marketplace names: official/community/directory names, impersonating names (for example `official-claude-plugins`, `claude-plugins-v2`, any non-ASCII), other spellings of reserved names (≥ 2.1.280), `inline`, `builtin`, `skills-dir`, `synced`, `claude-plugin-test`, `npm`, `pip`, `uv`, `cargo`, `github`, `gh`, and the `claudeai-` prefix.
- `claude-essentials` passes `claude plugin validate --strict` and the `claude plugin marketplace add` name check (runtime-verified 2026-10-03).

### Plugin manifest

- `.claude-plugin/plugin.json`; only `name` is required. Only the manifest goes inside `.claude-plugin/`; every component lives at the plugin root.
- **Plugin names must not start with `claude-`, `anthropic-`, `anthropics-` or `cc-plugin-`**, must not be `claude`, `anthropic`, `anthropics`, `claude-code` or `claude-mods`, and must not put `official` next to `claude`/`anthropic` (validate error). Having `claude`/`anthropic` as a whole word anywhere else is a warning (fails `--strict`).
- `version` is **not checked against SemVer** by Claude Code; enforce SemVer ourselves.
- **Version source of truth:** `plugin.json` `version` wins over the marketplace entry `version`. Runtime-verified 2026-10-03: an entry with the **same** version passes `validate --strict` and `claude plugin tag`; only a **mismatching** entry version is a validate warning (relative-path entries only; fails `--strict`) and makes `claude plugin tag` refuse. The docs advise not setting it in both places. Project rule: set `version` in `plugin.json` only, never in the marketplace entry (no sync step, no drift).
- Users only receive a new copy when the computed version changes. If `version` is set and not bumped, users never get the new commits.
- Component paths must start with `./`, resolve inside the plugin root and exist. `commands`, `agents`, `outputStyles`, `workflows` replace their default folder; `skills` adds to it; `hooks`, `mcpServers`, `lspServers` merge.
- Standard layout: `skills/<name>/SKILL.md`, `commands/` (legacy; prefer skills), `agents/*.md`, `hooks/hooks.json` (with top-level `"hooks"` wrapper), `.mcp.json`, `.lsp.json`, `output-styles/`, `workflows/`, `themes/`, `monitors/monitors.json`, `bin/` (on the Bash tool PATH; claude.ai and Cowork refuse plugins with a top-level `bin/`), `settings.json` (only `agent` and `subagentStatusLine`).
- A `CLAUDE.md` at a plugin root is **not loaded** and validate warns about it. Put instructions in a skill.
- Variables: `${CLAUDE_PLUGIN_ROOT}` (installed version directory; changes on every update; never write state there), `${CLAUDE_PLUGIN_DATA}` (persistent, deleted on last uninstall unless `--keep-data`), `${CLAUDE_PROJECT_DIR}`. They are **not** in the environment of Bash tool commands; in skill/agent/command content write the `${...}` reference in the Markdown body so it is substituted inline.
- Shell-form hooks: wrap the variable in double quotes (`"${CLAUDE_PLUGIN_ROOT}"/scripts/x.sh`); validate warns when unquoted. Prefer exec form with `args`.
- `${user_config.KEY}` is rejected in shell-form hook commands, monitor commands and MCP `headersHelper`; use exec form or `CLAUDE_PLUGIN_OPTION_<KEY>`.
- Installed plugins are copied to `~/.claude/plugins/cache/<marketplace>/<plugin>/<version>/`; files outside the plugin directory are not copied. Symlinks inside the plugin are preserved; symlinks to elsewhere in the same marketplace are dereferenced; symlinks outside the marketplace are skipped.

### Official CLI tooling (prefer over hand-rolled scripts)

- `claude plugin validate <path> [--strict] [--json]`: the authoritative validator. Exit 0 pass, 1 fail, 2 validator error. From a marketplace directory it does **not** open the plugins' skill/agent/command/hook/MCP files, so **validate each plugin directory separately as well**. Since 2.1.281 it also checks MCP entries; since 2.1.283 it checks `outputStyles`, `lspServers`, `monitors`, `themes` paths.
- `claude plugin tag [path] [--dry-run] [--push] [-m]`: creates the annotated tag **`<name>--v<version>`** (official format; runtime-verified output `hello--v0.1.0` via `git tag -a <tag> -m "<name> <version>"`, pushed as `refs/tags/<tag>`) after checking that `plugin.json` and the marketplace entry agree. Refuses dirty trees and existing tags. Every workflow, script and doc that consumes plugin tags must match exactly `<name>--v<semver>` (double hyphen, lowercase `v`), never `v*` or `<name>-v*`. With `tag.gpgsign=true` the annotated tag is signed (runtime-verified 2026-10-03 in a full release of a throwaway clone: `git tag -v` reports a good ED25519 signature); verify it with `git tag -v` after tagging (docs/releasing.md). Release dates are UTC.
- `claude plugin init <name> --with skills agents hooks mcp lsp output-style channel`: scaffolds **only** under `<config dir>/skills/<name>/` (no destination flag). It honors `CLAUDE_CONFIG_DIR`, so run it with an isolated temporary `HOME` and `CLAUDE_CONFIG_DIR` and move the output into `plugins/<name>/`. Its output includes a root `SKILL.md` plus `"skills": ["./"]`, a pattern for skills-directory plugins that must be adapted for marketplace plugins.
- `claude plugin eval` exists (≥ 2.1.269) for behavioral eval suites; may report "early access" depending on account.
- `--plugin-dir <path>` loads a plugin for one session without installing it. Pointing it at a marketplace root does not load plugins from `marketplace.json`.

### Schema URLs

- The `$schema` value emitted by `claude plugin init` (`https://anthropic.com/claude-code/plugin.schema.json`) and the analogous `marketplace.schema.json` return **HTTP 404** (checked 2026-10-03). There is no published official JSON Schema; do not hand-write one that imitates Claude Code. `claude plugin validate` is the schema authority.

### Distribution and updates

- Users add the marketplace with `/plugin marketplace add nerymurillohnd/claude-essentials` (or `claude plugin marketplace add …`) and install with `claude plugin install <plugin>@claude-essentials`, or in one step `/plugin install <plugin> --marketplace nerymurillohnd/claude-essentials` (≥ 2.1.275).
- Teams pre-configure it with `extraKnownMarketplaces` (honored in a repository's `.claude/settings.json` only after the workspace trust dialog) plus `enabledPlugins` keyed `plugin@claude-essentials`.
- **Background auto-update is OFF by default for third-party marketplaces, including this one, and `marketplace.json` has no field to turn it on.** Users stay on their installed version until they run `claude plugin update <plugin>@claude-essentials` or `/plugin marketplace update claude-essentials`, or turn on **Enable auto-update** under `/plugin` → Marketplaces, or set `"autoUpdate": true` on the `extraKnownMarketplaces` entry. Security fixes therefore do **not** reach users automatically: the README install instructions must include the auto-update step, and security advisories must tell users to update explicitly.
- Never rename a published plugin; use `displayName` for labels. If unavoidable, add a `renames` entry. Removing a plugin should also add `renames: { "<name>": null }`.

### Isolated install testing (runtime-verified)

- `HOME=<tmp> CLAUDE_CONFIG_DIR=<tmp>/.claude claude plugin marketplace add <repo-path>` followed by `claude plugin install <plugin>@claude-essentials` works fully isolated. Checksums of the real `~/.claude/settings.json`, `plugins/known_marketplaces.json`, `plugins/installed_plugins.json`, `plugins/cache` and `skills` listings were identical before and after.
- A marketplace added from a local directory loads relative-path plugins **in place** (version ignored). That alone never proves what users receive. Runtime nuance (2.1.289): Claude Code still writes a copy to `plugins/cache/...` and `claude plugin list --json` reports that copy as `installPath`, while the text output of `claude plugin list` shows `Read from: <source dir>`. Do not infer the load location from `installPath`.
- **Cache-copy path (what real users get), runtime-verified 2026-10-03:** clone HEAD to a bare repo, write a temporary marketplace whose entries use `{"source": "git-subdir", "url": "file://<bare>.git", "path": "plugins/<name>"}`, add that marketplace directory and install. The plugin lands in `<config>/plugins/cache/claude-essentials/<name>/<version>/`, exactly as from the published repository. It tests committed HEAD only, so commit before running it. `scripts/test_install.py` runs both modes plus a `--plugin-dir` session load.
- Approaches verified **not** to work, do not retry: `claude plugin marketplace add file://<bare>.git` ("Invalid marketplace source format"); `extraKnownMarketplaces` in the isolated `settings.json` (registers only at interactive session start, so CLI commands report the marketplace as not found); a git remote served over dumb HTTP (`python -m http.server` + `git update-server-info`) fails with "dumb http transport does not support shallow capabilities".
- **READMEs never drift from the plugins:** the root README catalog and each plugin README's metadata and component tables are generated blocks rewritten from `marketplace.json`, `plugin.json` and the plugin's files; a gate in `uv run scripts/check.py` fails when a generated block is stale. Edit the source files, never the generated blocks.

### Changelog findings 2.1.280–2.1.289 (read in full 2026-10-03)

- **Minimum version for our tooling: 2.1.289.** Validator fixes landed in this window: plugin skipped when the folder also holds a marketplace manifest (2.1.289), names Claude Code cannot install now fail (2.1.283), `outputStyles`/`themes`/`monitors`/`lspServers` path checks (2.1.283), MCP checks plus an unquoted `${CLAUDE_PLUGIN_ROOT}` warning (2.1.281). Pin CI to 2.1.289 or newer.
- **Mods (2.1.287, docs `plugins/mods/*`):** plugins can now ship mods, JS/TS functions that run inside Claude Code with the user's full permissions, unsandboxed. They see every prompt and tool call, can rewrite them, can approve tool calls (even ones a user hook blocked), make network requests and spend the user's usage. Many mod fixes followed in 2.1.288–2.1.289, so the feature is young. Administrators can stop user-installed mods through managed settings. `claude plugin validate` prints `hooks:` and `calls:` lines that list what a mod does; `claude plugin test` runs a mod's `.test.ts` tests. The note shown to the user above the prompt comes from the built-in `cc-plugin-you-should-know` mod.
- **`claude plugin init --with hooks` scaffolds a settings hook that runs `bun "${CLAUDE_PLUGIN_ROOT}/hooks-handlers/on-session-start.ts"`**, which assumes `bun` exists on third-party machines. Never ship that unchanged; hooks must use interpreters the plugin documents as requirements.
- **Project skill named `verify` (2.1.286, docs `skills#run-your-checks-before-each-commit`):** when a project skill named `verify` (or `simplify`) exists and Claude may invoke it, Claude is told to run it right before every commit, except docs-only or tests-only commits. Use it to run `uv run scripts/check.py`. Plugin skills don't count.
- **AGENTS.md (≥ 2.1.277):** Claude Code reads `AGENTS.md` only when no `CLAUDE.md` exists in the working directory or above it, or when `CLAUDE.md` imports it. With our `CLAUDE.md`, a separate `AGENTS.md` is ignored by Claude Code unless imported.
- **Path-scoped `.claude/rules/` with `paths:` frontmatter** now load on Write/Edit as well as Read (2.1.288), which makes them reliable for `plugins/**` authoring rules.
- **`/doctor prompt-audit [path]` (2.1.283)** audits CLAUDE.md, skills, agents, commands and output styles for prompting patterns written for older models, stale paths and stale commands. It is interactive; use it as a review step for plugin content.
- **`allowed-tools` pre-approval is not guaranteed:** under managed `allowManagedPermissionRulesOnly`, skills from third-party marketplaces lose their `allowed-tools` pre-approval (2.1.284). Plugins must not depend on it.
- **Auto mode is the default permission mode** for interactive sessions with no configured mode (2.1.284). Security review must assume plugin instructions run under auto mode.
- **Hooks:** PreToolUse and PermissionRequest hooks that fail to match now block the call (2.1.288); synchronous hooks that start background processes used to hang (fixed 2.1.285). Plugin hooks must be robust, fast and must not spawn daemons.
- **Reserved namespaces:** skill folders, command files and workflow commands in the `anthropic-skills` or `claude-ai` namespace no longer load (2.1.282). The `claude-ai` name reservation was reverted in 2.1.283, but avoid both names.
- **Names that imitate reserved marketplace names** are refused at add time, and one already added stops loading (2.1.280).
- **Load-check without an API key:** `claude --plugin-dir <dir> plugin list --json` reports session-only plugins with `errors` and `notes` fields. A folder of plugins loads each child that has a manifest (≥ 2.1.265; a folder that also holds `marketplace.json` works ≥ 2.1.281).
- **Users can sparse-clone the marketplace:** `claude plugin marketplace add --sparse .claude-plugin plugins …` (sparse fixes on git < 2.39 landed in 2.1.284).

### Tooling versions checked 2026-10-03 (re-check before pinning)

git-cliff 2.14.2 (Apache-2.0), commitlint 21.2.3 (MIT), markdownlint-cli2 0.23.3 / action v24.2.0 (MIT), prettier 3.9.9 (MIT), actionlint 1.7.12 (MIT), zizmor 1.30.1 (MIT), lychee-action v2.9.0 (Apache-2.0), actions/labeler v7.0.0, actions/checkout v7.0.1, actions/setup-node v7.0.0, astral-sh/setup-uv v10.2.0, MADR 4.0.0, Contributor Covenant 3.0, Keep a Changelog 1.1.0, Conventional Commits 1.0.0, SemVer 2.0.0. release-please v17.11.2 supports `tag-separator` (could produce `<name>--v<version>`) but was rejected because its commits and tags are not signed with the maintainer's key.

### Local toolchain facts (runtime-verified 2026-10-03, uv 0.12.22)

- Processes started through zsh load `~/.zshenv`, interactive or not (the Bash tool is a non-interactive login zsh), so `python3` is `~/.local/bin/python3`, the uv-managed CPython 3.14.7, and `bash` is Homebrew bash 5.3. Without zsh (`env -i`, launchd, cron, apps started from the Dock, CI, third-party machines) `python3` is Xcode's 3.9.6 and `bash` is `/bin/bash` 3.2.57.
- The repository scripts use Python 3.12 syntax; under Xcode's 3.9.6 they fail with `SyntaxError`. That is why everything is run with `uv run` and PEP 723 `requires-python`. `#!/usr/bin/env python3 -` does not run the script at all: `-` makes Python read the program from stdin.
- `pip3` resolves only to Xcode's `/usr/bin/pip3`; never use pip.
- `uv run` of a PEP 723 script keeps an environment in `~/.cache/uv/environments-v2/` by design. That cache belongs to uv: the uv docs say it is never safe to modify the cache directly; clean it only with `uv cache prune` or `uv cache clean`. Cached uv environments are not orphaned test files.
- Plugin shell scripts may run under macOS `/bin/bash` 3.2 on users' machines.

## Claims to re-verify before relying on them

- A candidate `.lsp.json` schema (verified on 2.1.281 by its author) states that one invalid LSP server drops every server in the same file, contradicting the docs, and that a `$schema` key in `.lsp.json` invalidates the file. Not verified here; test in an isolated config before relying on either.

## Current state / next steps

- Foundation complete locally (2026-10-03): catalog, example plugin `hello-example`, gates (`uv run scripts/check.py`, 9 gates, 50 tests), scaffold, `bump_version.py` and `release_notes.py`, CI, labels, templates, community files, docs and dated ADRs in `docs/adr/decisions/`. Local repository with signed commits; **no remote**.
- Next: maintainer approval to publish (docs/publishing-checklist.md), then the first real plugin, then removal of `hello-example`.
- Awaiting the maintainer: refining the user-level Python rule (python3 allowed only in processes started through zsh), a `uv cache prune` to repair cache entries removed by hand on 2026-10-03, a bash 3.2 compatibility rule for plugin shell scripts, removal of old session scratch files, and the LICENSE copyright holder.
- Deferred decisions: scheduled Claude Code release watcher, Dependabot for action pins, link checking, git-cliff or release-please, a single release command (only after real releases).
