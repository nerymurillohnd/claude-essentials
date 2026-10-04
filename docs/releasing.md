# Releasing

How plugin and marketplace versions, changelogs, tags, releases and labels work. Decisions: [ADR 0006](adr/0006-per-plugin-versioning.md), [ADR 0007](adr/0007-release-automation.md), [ADR 0011](adr/0011-labels-and-pr-automation.md).

**Contents:** [Versions](#versions) · [Commit messages](#commit-messages) · [Changelogs](#changelogs) · [Release a plugin](#release-a-plugin) · [Release the marketplace](#release-the-marketplace) · [Deprecate or remove a plugin](#deprecate-or-remove-a-plugin) · [Labels](#labels)

## Versions

Each plugin has its own [SemVer](https://semver.org/spec/v2.0.0.html) version in `plugins/<name>/.claude-plugin/plugin.json`, and only there. Claude Code reads `plugin.json` first, and users receive a new copy only when that version changes ([versions and updates](https://code.claude.com/docs/en/plugins/loading#versions-and-updates)). The marketplace has its own version in `.claude-plugin/marketplace.json`.

| Bump  | When                                | Examples                                                                                                     |
| ----- | ----------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| MAJOR | Users must change something         | Renamed or removed skill, agent or command; changed hook behavior; a new required setting; removed component |
| MINOR | New, backward-compatible capability | New skill, agent or option with a default                                                                    |
| PATCH | Fixes and documentation             | Bug fix, clearer instructions, README changes                                                                |

A MAJOR release needs a `### Migration` section stating what broke, who is affected and the exact steps to adapt.

## Commit messages

[Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/), checked by `scripts/check_commit_msg.py` in CI and in the optional `commit-msg` hook:

```text
<type>(<scope>)!: <subject>

<body>

BREAKING CHANGE: <what breaks>
```

- Types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`.
- Scope: the plugin name for plugin changes; `marketplace`, `scripts`, `ci` or `docs` otherwise.
- `!` or a `BREAKING CHANGE:` footer marks a breaking change and requires the `semver:major` label.

## Changelogs

Each plugin has `CHANGELOG.md` in [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/) format; the marketplace has the root `CHANGELOG.md`. Contributors add notes under `## [Unreleased]` with the change types `Added`, `Changed`, `Deprecated`, `Removed`, `Fixed`, `Security` and `Migration`. Notes are written for users: what changed for them, not how the code changed.

## Release a plugin

Requirements: a clean working tree on `main`, signing configured for commits and tags, Claude Code 2.1.289 or later.

```bash
make release-dry-run PLUGIN=<name> LEVEL=minor     # preview the new changelog
uv run scripts/release.py plugin <name> minor      # bump, commit, tag
git push origin main <name>--v<version>            # only when approved
```

The script refuses an empty `[Unreleased]`, a MAJOR without Migration, and a changelog that disagrees with `plugin.json`. It moves the notes into `## [<version>] - <date>`, bumps `plugin.json`, runs `claude plugin validate --strict` and `scripts/check_repo.py`, commits `chore(<name>): release <version>`, and runs `claude plugin tag`, which checks manifest and catalog agree and creates the signed annotated tag `<name>--v<version>`. It then verifies the tag signature.

When protected branches require pull requests, run the release on a branch, open a pull request with the `semver:` label, merge it, and tag the merged commit with `claude plugin tag plugins/<name>`.

Pushing the tag runs `.github/workflows/release.yml`: it checks the tag against `plugin.json`, validates the plugin, and publishes a GitHub Release whose notes are that version's changelog section.

## Release the marketplace

```bash
uv run scripts/release.py marketplace minor
```

Same flow on the root `CHANGELOG.md` and `marketplace.json`, with the tag `marketplace--v<version>`. Release the marketplace when plugins are added, deprecated or removed, or when distribution changes.

## Deprecate or remove a plugin

1. Deprecate in a MINOR release: add `### Deprecated` with the replacement and the planned removal, and state it in the README Overview.
2. Keep the plugin for at least one further minor release and 30 days.
3. Remove it in a marketplace release: delete the entry and directory, add `"renames": { "<name>": null }` to `marketplace.json` (append-only), and note it in the root changelog. Never rename a published plugin unless a `renames` entry maps the old name to the new one ([rename or remove a plugin](https://code.claude.com/docs/en/plugins/host-marketplace#rename-or-remove-a-plugin)).

## Labels

Labels are defined in `.github/labels.yml` and synced by the Labels workflow. Path labels (`plugin:`, `category:`, `type:docs`, `type:chore`, `security-review`) are applied by the labeler; issue forms apply `status:needs-triage` and a `type:`. Maintainers apply one `semver:` label to every pull request that changes a plugin; `scripts/check_pr.py` enforces it. Release-note categories in `.github/release.yml` follow the same taxonomy.
