# Releasing

How plugin versions, changelogs, tags, releases and labels work, and which changes go through a pull request. Decisions: [ADR per-plugin-versioning](adr/decisions/ADR_2026-10-03_per-plugin-versioning.md), [ADR release-automation](adr/decisions/ADR_2026-10-03_release-automation.md) (superseded by [ADR release-orchestration](adr/decisions/ADR_2026-10-04_release-orchestration.md)), [ADR labels-and-pr-automation](adr/decisions/ADR_2026-10-03_labels-and-pr-automation.md).

**Contents:** [Versions](#versions) · [When a change needs a release](#when-a-change-needs-a-release) · [Pull request or direct push](#pull-request-or-direct-push) · [Commit messages](#commit-messages) · [Changelogs](#changelogs) · [Release a plugin](#release-a-plugin) · [Deprecate or remove a plugin](#deprecate-or-remove-a-plugin) · [Labels](#labels)

## Versions

Only plugins are versioned. Each plugin has its own [SemVer](https://semver.org/spec/v2.0.0.html) version `MAJOR.MINOR.PATCH` in `plugins/<name>/.claude-plugin/plugin.json`, and only there: never in its catalog entry, never with a `v` prefix, a pre-release or build suffix. New plugins start at `0.1.0`.

Claude Code reads `plugin.json` first and caches each plugin by name and version, so users receive a new copy only when that version changes ([versions and updates](https://code.claude.com/docs/en/plugins/loading#versions-and-updates)).

The catalog (`.claude-plugin/marketplace.json`) has no `version`, neither top-level nor `metadata.version`. Claude Code does not use it to deliver anything: users receive the latest catalog from the default branch whenever their copy refreshes (`/plugin marketplace update`, `claude plugin update` or auto-update, which is off by default; users who added a `#<ref>` stay on that ref). The catalog's history is the dated root `CHANGELOG.md`.

| Bump  | When                                  | Examples                                                                                                     |
| ----- | ------------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| MAJOR | Users must change something           | Renamed or removed skill, agent or command; changed hook behavior; a new required setting; removed component |
| MINOR | New, backward-compatible capability   | New skill, agent or option with a default; a component marked deprecated                                     |
| PATCH | Fixes and documentation of the plugin | Bug fix, clearer instructions, README changes, typo fixes                                                    |

A MAJOR release needs a `### Migration` section stating what broke, who is affected and the exact steps to adapt.

## When a change needs a release

A change merged into `plugins/<name>/` without a new version would give users of the same version different files: those who installed earlier keep their cached copy, and those who install later get the new commit. So every change inside a plugin ships with its own release, in the same pull request.

| Change                                                                                     | Release                                                        |
| ------------------------------------------------------------------------------------------ | -------------------------------------------------------------- |
| Any file inside `plugins/<name>/`: skills, agents, hooks, MCP, README, CHANGELOG, manifest | Yes, in the same pull request, at the level of the table above |
| A new plugin                                                                               | No: it starts at `0.1.0`; the scaffold adds the catalog note   |
| A catalog entry (description, category, tags) or `renames` in `marketplace.json`           | No: add a dated note to the root `CHANGELOG.md`                |
| Scripts, tests, CI, `docs/`, `.github/`, root README, rules, ADRs                          | No                                                             |

A pull request may release several plugins, each with its own bump; it carries exactly one `semver:` label naming the highest bump among the plugins it releases.

## Pull request or direct push

| Change                                         | Path                                                                                                 |
| ---------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| Anything under `plugins/**`                    | Pull request: `scripts/check_pr.py` checks the release and only runs on pull requests                |
| `.claude-plugin/marketplace.json`              | Pull request: it is what users see when they refresh the catalog                                     |
| `.github/workflows/**`, `CODEOWNERS`           | Pull request: code owner approval and the workflow audits                                            |
| Docs, scripts, tests, rules, ADRs, root README | Direct push to `main`, signed, after `scripts/check.py` passes and the maintainer approves that push |

After a direct push, confirm that the Validate workflow passes on `main`.

## Commit messages

[Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/), checked by `scripts/check_commit_msg.py` in CI and in the optional `commit-msg` hook:

```text
<type>(<scope>)!: <subject>

<body>

BREAKING CHANGE: <what breaks>
```

- Types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`.
- Scope: the plugin name for plugin changes; `marketplace`, `scripts`, `ci` or `docs` otherwise.
- `!` or a `BREAKING CHANGE:` footer marks a breaking change. A `!` in the pull request title requires the `semver:major` label; only the title is checked against the label.

## Changelogs

Both changelogs use the change types of [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/): `Added`, `Changed`, `Deprecated`, `Removed`, `Fixed`, `Security` and `Migration`. Notes are written for users: what changed for them, not how the code changed.

- **Plugin** (`plugins/<name>/CHANGELOG.md`): versioned sections `## [<version>] - <date>`, newest first. Write the notes under `## [Unreleased]`; `scripts/bump_version.py` moves them into the release section, so `[Unreleased]` is empty on `main`.
- **Catalog** (root `CHANGELOG.md`): dated sections `## YYYY-MM-DD` (UTC), newest first: plugins added, deprecated, removed or renamed, and changes to the catalog entries or to how the catalog is distributed.

## Release a plugin

Users receive a plugin from `main`: Claude Code clones the marketplace's default branch and caches each plugin by its `version`, so the merge of a pull request with a bump is the release, and users get it on their next `claude plugin update` or auto-update ([host a marketplace](https://code.claude.com/docs/en/plugins/host-marketplace#release-a-new-version)). The tag and the GitHub Release come after it as the signed record and for dependency version ranges ([dependencies](https://code.claude.com/docs/en/plugins/dependencies#create-a-release-tag)); Claude Code reads tags only to resolve a dependent plugin's version constraint on this plugin, never to install a plugin itself. Keep `main` releasable at all times.

The release is prepared in the pull request that changes the plugin, and tagged after the merge ([ADR release-orchestration](adr/decisions/ADR_2026-10-04_release-orchestration.md)). The steps below also work by hand.

0. **Branch.** Work on a short-lived `<plugin>/<topic>` branch from an up-to-date `main` (`git switch -c <plugin>/<topic>`); GitHub deletes it on merge, and `git fetch --prune` removes the local remote-tracking reference. Non-plugin pull requests use the commit scope as prefix: `marketplace/`, `scripts/`, `ci/` or `docs/` ([ADR branch-naming](adr/decisions/ADR_2026-10-04_branch-naming.md)).

Requirements: signing configured for commits and tags, a current Claude Code.

1. **Notes.** Describe every user-relevant change under `## [Unreleased]` in `plugins/<name>/CHANGELOG.md`. To draft notes from history, optionally run git-cliff without installing anything, and then rewrite the draft for users:

   ```bash
   uvx git-cliff@2.14.2 --include-path "plugins/<name>/**" --tag-pattern "^<name>--v" --unreleased
   ```

   The draft only lists commits; it never decides the bump and is never written to the changelog automatically.

2. **Bump, in the same branch.** Preview, then prepare the files:

   ```bash
   scripts/bump_version.py plugin <name> <major|minor|patch> --dry-run
   scripts/bump_version.py plugin <name> <major|minor|patch>
   ```

   The script refuses an empty `[Unreleased]`, a MAJOR without Migration, and a changelog that disagrees with `plugin.json`. It moves the notes into `## [<version>] - <date>` (UTC), bumps `plugin.json`, regenerates the README content that shows the version, and runs `claude plugin validate --strict` and `scripts/check_repo.py`. It does not commit, tag or push.

3. **Commit and open the pull request** with the matching `semver:` label:

   ```bash
   git add plugins/<name> README.md
   git commit -m "fix(<name>): <subject>"
   ```

   `scripts/check_pr.py` fails the pull request when the plugin changed without a single-step bump, when the release section or label does not match the bump, when `## [Unreleased]` is not empty, when a MAJOR has no Migration, when the title is not a Conventional Commit or its scope is not the plugin name while exactly one plugin changed, or when `.claude-plugin/marketplace.json` changed without a note in the root `CHANGELOG.md`.

After the merge a maintainer tags the merged commit and publishes the GitHub Release as the signed record; the maintainer steps are in `.claude/rules/releasing.md`. A published tag is never deleted or moved: fix forward with a new release, a PATCH, or a MAJOR with a `### Migration` section if users must act.

## Deprecate or remove a plugin

To remove a component inside a plugin (a skill, agent, hook or command), deprecate it under `### Deprecated` in a plugin minor, keep it for at least one further minor release and 30 days, and remove it in the plugin's next major with a `### Migration` section.

To remove a whole plugin (exceptions: a confirmed vulnerability that cannot be fixed quickly removes it at once, as `SECURITY.md` promises, and the example plugin `hello-example` is removed at once by [ADR remove-example-plugin-without-deprecation](adr/decisions/ADR_2026-10-05_remove-example-plugin-without-deprecation.md); both skip steps 1 and 2):

1. Deprecate it in a plugin MINOR release: add `### Deprecated` with the replacement and the planned removal, and state it in the README Overview. Add a dated `### Deprecated` note to the root `CHANGELOG.md`.
2. Keep the plugin for at least one further minor release and 30 days.
3. Remove it in a pull request: delete the entry and the directory, add `"renames": { "<name>": null }` to `marketplace.json` (append-only), remove the `plugin:<name>` label and its labeler rules, regenerate the root README with `scripts/sync_readmes.py`, and add a dated `### Removed` note to the root `CHANGELOG.md`. Never rename a published plugin unless a `renames` entry maps the old name to the new one ([rename or remove a plugin](https://code.claude.com/docs/en/plugins/host-marketplace#rename-or-remove-a-plugin)).

## Labels

Labels are defined in `.github/labels.yml` and synced by the Labels workflow. Path labels (`plugin:`, `category:`, `type:docs`, `type:chore`, `security-review`) are applied by the labeler; issue forms apply `status:needs-triage` and a `type:`. A pull request that releases plugins carries exactly one `semver:` label naming the highest bump among the plugins it releases, and no other pull request carries one; `scripts/check_pr.py` enforces both. Release-note categories in `.github/release.yml` follow the same taxonomy.
